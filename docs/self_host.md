# Self-hosted deployment

Instructions for running LetAgentPay on your own server.

## Requirements

- Docker and Docker Compose (v2+)
- 1 GB RAM, 1 CPU (minimum)
- Optional: Anthropic API key (for AI policy generation)

## Quick start

```bash
git clone https://github.com/letagentpay/letagentpay
cd letagentpay

# Create configuration file
cp .env.example .env
```

Edit `.env` -- required variables:

```env
JWT_SECRET=<random string 32+ characters>
ADMIN_PASSWORD=<password for dashboard login>
```

Start:

```bash
docker compose up -d
```

Open `http://localhost:3000` and log in with the specified password.

> If deploying on a remote server (VPS), set `SITE_URL=http://<your-server-ip>:3000` in `.env` and open that address instead of localhost.

## Environment variables

### Required

| Variable | Description |
|---|---|
| `JWT_SECRET` | Secret key for signing JWT tokens. Generate with: `openssl rand -hex 32` |

### Authentication

| Variable | Description |
|---|---|
| `ADMIN_PASSWORD` | Password for web interface login (recommended for self-hosted) |

How login works depends on what's configured:

| ADMIN_PASSWORD | RESEND_API_KEY | Login method |
|---|---|---|
| set | — | Password form (simplest for self-hosted) |
| not set | set | Magic link sent to email |
| not set | not set | Magic link printed to backend console (for local dev) |

If `ADMIN_PASSWORD` is set, any email can log in using this password — no email is sent. This is the recommended approach for self-hosted deployments.

### Optional

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | -- | Anthropic API key for AI policy generation from natural language |
| `POSTGRES_PASSWORD` | `letagentpay` | PostgreSQL password |
| `SITE_URL` | `http://localhost:3000` | Public URL (for CORS and links) |
| `PORT` | `3000` | Frontend port |
| `COOKIE_SECURE` | `false` | Set to `true` if using HTTPS |
| `TELEGRAM_BOT_TOKEN` | -- | Telegram bot token from @BotFather (enables Telegram notifications) |
| `CDP_API_KEY_ID` | -- | Coinbase Developer Platform API key ID (enables x402 wallet creation) |
| `CDP_API_KEY_SECRET` | -- | CDP API key secret |
| `CDP_WALLET_SECRET` | -- | CDP wallet encryption key (EC P-256 in base64 DER format) |

### x402 crypto-micropayments (optional)

LetAgentPay can act as a policy middleware for x402 on-chain payments (USDC on Base). Agents ask the policy engine for authorization before paying, then report the transaction hash for audit.

x402 works without CDP credentials -- agents can register wallet addresses manually via `POST /x402/wallets`. CDP credentials are only needed for automatic wallet creation via `POST /x402/wallets/create`.

To set up CDP credentials: register at [portal.cdp.coinbase.com](https://portal.cdp.coinbase.com), create an API key, and generate a wallet secret (EC P-256 key).

To enable Telegram notifications: create a bot via [@BotFather](https://t.me/BotFather), copy the token, set it in `.env`, then connect the bot from **Settings > Notifications** in the dashboard.

## Architecture

```
                     +--------------+
                     |   Frontend   | :3000
                     |  (Next.js)   |
                     +------+-------+
                            |
                     +------+-------+
   AI Agents ------> |   Backend    | :8000
   (Bearer token)    |  (FastAPI)   |
                     +--+--------+--+
                        |        |
                 +------+---+ +--+------+
                 |PostgreSQL| |  Redis  |
                 |   :5432  | |  :6379  |
                 +----------+ +---------+
```

- **Frontend** -- web dashboard for managing agents and approving requests
- **Backend** -- API server, policy engine, authorization
- **PostgreSQL** -- storage for accounts, agents, requests, x402 authorizations
- **Redis** -- spending counters (daily/weekly/monthly), rate limiting, exchange rate cache

AI agents connect via the Agent API (`/api/v1/agent-api`) for fiat purchase requests, or the x402 API (`/api/v1/x402`) for crypto-micropayment authorization.

## Updating

```bash
cd letagentpay
git pull
docker compose up -d --build
```

Database migrations are applied automatically when the backend container starts.

## HTTPS

For production deployment, it is recommended to use a reverse proxy (nginx, Caddy, Traefik) in front of LetAgentPay.

Example with Caddy:

```
letagentpay.example.com {
    reverse_proxy localhost:3000
}
```

When using HTTPS, set the following in `.env`:

```env
SITE_URL=https://letagentpay.example.com
COOKIE_SECURE=true
```

## Backup

Data is stored in the Docker volume `pgdata`. To back up:

```bash
docker compose exec postgres \
  pg_dump -U letagentpay letagentpay > backup_$(date +%Y%m%d).sql
```

Restore:

```bash
cat backup_20260322.sql | docker compose exec -T postgres \
  psql -U letagentpay letagentpay
```

## Troubleshooting

### Backend does not start

Check logs: `docker compose logs backend`

Common causes:
- PostgreSQL is not ready yet -- backend automatically waits for healthcheck
- Invalid `JWT_SECRET` -- must be a non-empty string

### Frontend shows connection error

- Make sure the backend is running: `curl http://localhost:8000/health`
- Verify that `SITE_URL` in `.env` matches the URL in the browser

### AI policy generation does not work

- Make sure `ANTHROPIC_API_KEY` is set in `.env`
- The key should start with `sk-ant-`
- Policies can be created manually (JSON) without the Anthropic API
