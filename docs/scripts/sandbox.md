# Sandbox -- Test Environment

The `scripts/sandbox.py` script creates a test account with agents and simulates purchases. It allows you to test the entire customer journey without a real AI agent.

## Quick Start

```bash
# 1. Start the infrastructure
docker-compose up -d db redis
make run-back   # in one terminal
make run-front  # in another terminal

# 2. Run the sandbox
python3 scripts/sandbox.py
```

## What Gets Created

| Object | Details |
|--------|---------|
| Account | `sandbox@test.local`, USD, America/New_York |
| Shopping Assistant | Budget $5000. Groceries, food, household. Auto-approve < $50 |
| Tech Buyer | Budget $10000. Electronics, subscriptions, education. Auto-approve subscriptions < $30 |
| Travel Agent (optional) | Budget $3000. Taxi, transport, restaurants |

Each agent is configured with a policy that includes limits and auto-approve rules.

## Options

```bash
python3 scripts/sandbox.py                        # Standard run
python3 scripts/sandbox.py --seed-only            # Only create data (no requests)
python3 scripts/sandbox.py --print-jwt            # Print JWT for login without magic link
python3 scripts/sandbox.py --reset                # Delete old data and recreate
python3 scripts/sandbox.py --agents 3             # Create 3 agents (max 3)
python3 scripts/sandbox.py --requests 10          # 10 requests per agent
python3 scripts/sandbox.py --delay 0.5            # Faster (0.5s delay between requests)
```

## How to Log into the Dashboard

### Option 1: Magic link (recommended)
1. Open http://localhost:3000/auth/signin
2. Enter `sandbox@test.local`
3. In the backend logs, look for the line `[DEV] Magic link for sandbox@test.local: http://localhost:3000/auth/verify?token=...`
4. Open that link

### Option 2: JWT directly
```bash
python3 scripts/sandbox.py --print-jwt
```
Copy the JWT from the output and paste it into the DevTools Console:
```js
document.cookie = 'access_token=eyJ....; path=/'
```
Reload the page.

## What to Test

After running the sandbox, the dashboard will contain:

1. **Multiple agents** -- switch between them using tabs
2. **Pending requests** -- approve or reject them
3. **Auto-approved requests** -- with purchase confirmation (completed/failed)
4. **Rejected requests** -- rejected by policy (wrong category / limit exceeded)
5. **Agent comments** -- explanations of why a purchase is needed
6. **Spending analytics** -- totals for today/week/month
7. **Connect page** -- connection instructions with the token

## Re-running the Simulation

After seeding, you can send requests via `demo_agent.py`:

```bash
# Token from sandbox output
python3 scripts/demo_agent.py --token agt_xxxxx --mode continuous
```
