# Architecture

Architecture overview of LetAgentPay for contributors.

## What is LetAgentPay

Policy middleware between AI agents and money. Agents send purchase requests, and LetAgentPay validates them against configured policies (budgets, limits, categories, schedules) and decides: auto-approve, send for manual review, or reject.

LetAgentPay **does not process payments** — it only decides "can this be spent". Payment integration is on the agent's side.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (async), Python 3.14 |
| Database | PostgreSQL 16, SQLAlchemy async (asyncpg) |
| Migrations | Alembic |
| Cache / Pub-sub | Redis 7 |
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS |
| AI | Anthropic Claude API (natural language → JSON policy) |
| Auth | JWT in HTTP-only cookies (dashboard), Bearer tokens (Agent API) |

## Project Structure

```
letagentpay/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, middleware, lifespan
│   │   ├── config.py            # Pydantic settings (from env)
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── database.py          # Async session factory
│   │   ├── dependencies.py      # Auth dependencies (JWT, Bearer token)
│   │   ├── redis.py             # Redis connection pool
│   │   ├── utils.py             # Utilities (utcnow, etc.)
│   │   ├── routers/
│   │   │   ├── agent_api.py     # Agent API (purchase, confirm, budget)
│   │   │   ├── agents.py        # Agent CRUD (dashboard)
│   │   │   ├── auth.py          # Auth (magic link, password login)
│   │   │   ├── requests.py      # Purchase request management
│   │   │   ├── events.py        # SSE real-time events
│   │   │   ├── me.py            # Current user profile
│   │   │   ├── policy.py        # AI policy generation
│   │   │   ├── push.py          # Web Push subscriptions
│   │   │   └── budget_rules.py  # Account-level budget rules
│   │   └── services/
│   │       ├── policy_engine.py # 8-step policy validation
│   │       ├── spending.py      # Redis spending counters
│   │       ├── expiry.py        # Background: expire pending requests
│   │       └── rate_limit.py    # Sliding window rate limiter
│   ├── alembic/                 # Database migrations
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages (App Router)
│   │   ├── components/          # React components
│   │   └── lib/                 # API client, types, hooks
│   └── src/__tests__/           # Vitest tests
├── scripts/                     # Development/demo scripts
└── docs/                        # Documentation
```

## Key Models

```
Account (human user)
├── id, email, display_name, currency, timezone
├── is_admin, blocked
├── account_budget, account_spent, account_held
└── settings (request_expiry_minutes)

Agent (AI agent, belongs to Account)
├── id, name, description, token (agt_...)
├── status (active/paused), budget, spent, held
├── policy_json (rules), auto_approve_threshold
└── allowed_categories, schedule, daily/weekly/monthly limits

PurchaseRequest (from Agent)
├── id, amount, actual_amount, currency, category
├── description, status (pending/approved/rejected/confirmed/expired)
├── policy_result (JSON with check details)
└── timestamps (created_at, decided_at, confirmed_at)

BudgetRule (account-level spending rules)
├── rule_type (daily_limit/weekly_limit/monthly_limit/category_limit)
├── limit_amount, category
└── Applied across ALL agents in account
```

## Purchase Request Lifecycle

```
Agent                    LetAgentPay                     Human
  │                          │                             │
  ├─ POST /requests ─────────►│                             │
  │                          ├─ Policy Engine (9 checks)   │
  │                          │  1. Agent status            │
  │                          │  2. Velocity (req/min,/hr)  │
  │                          │  3. Category allowed        │
  │                          │  4. Per-request limit       │
  │                          │  5. Schedule check          │
  │                          │  6. Daily limit             │
  │                          │  7. Weekly limit            │
  │                          │  8. Monthly limit           │
  │                          │  9. Budget remaining        │
  │                          │                             │
  │  ◄── auto_approved ────  │  (if ≤ auto_approve &&      │
  │                          │   all checks pass)          │
  │                          │                             │
  │  ◄── pending ─────────── │ ── SSE notification ───────►│
  │                          │                             │
  │                          │  ◄── approve/reject ────────┤
  │  ◄── approved/rejected ──│                             │
  │                          │                             │
  ├─ POST /requests/:id/confirm ─► (actual_amount, success)│
  │                          ├─ Update spent counters      │
  │  ◄── confirmed ──────────│                             │
```

### Fund Holding

When a request is `pending`, the amount is **held** (reserved). This prevents multiple pending requests from collectively exceeding the budget:

- `pending` → held += amount
- `approved` → held -= amount, spent += amount
- `rejected/expired` → held -= amount (funds released)

## Policy Management

There are two ways to configure an agent's spending policy:

### AI Chat (natural language)
The default flow on the **Setup Policy** page. The user describes rules in plain English (e.g. "limit to $200/day, only groceries and transport"), Claude converts it to a structured JSON policy, and the user confirms.

- Backend: `POST /api/v1/agents/{id}/policy/ai` → AI preview, `POST .../ai/confirm` → save
- Iterative: the user can refine the policy through follow-up messages

### Manual Editor
The **Manual** tab on the same page. Provides a form with fields for all policy parameters (limits, categories, auto-approve) and a toggle to switch to a raw JSON editor for advanced users.

- Backend: `PUT /api/v1/agents/{id}/policy` → direct JSON update
- Both modes share the same policy schema (see [Agent Spending Policy Spec](agent_spending_policy_spec.md))

## Two Authentication Paths

### Dashboard (human users)
1. User enters email → receives magic link
2. Magic link → JWT in HTTP-only cookie (`access_token`)
3. Cookie sent automatically with API requests
4. **Self-hosted**: password login instead of magic link (`ADMIN_PASSWORD`)
5. **Sliding session**: JWT auto-refreshes on activity (when >50% of lifetime has passed)

### Agent API (AI agents)
1. Bearer token generated when creating an agent (`agt_...`)
2. Agent sends token in `Authorization: Bearer agt_...` header
3. Token is bound to a specific agent → access only to own data

## Spending Counters (Redis)

Spending counters are stored in Redis with time-bucketed keys:

```
spent:{agent_id}:{currency}:daily:{2026-03-22}     → 4500   (cents)
spent:{agent_id}:{currency}:weekly:{2026-W12}      → 23000
spent:{agent_id}:{currency}:monthly:{2026-03}      → 89000
```

Keys auto-expire (TTL = period + buffer). On approve/confirm, values are incremented atomically via `INCRBY` (stored as integer cents).

Account-level counters (`acct_spent:{account_id}:{currency}:…`) work similarly for budget rules.

## Real-time (SSE)

Redis pub/sub delivers events to the frontend via Server-Sent Events:

- `new_request` — new purchase request
- `request_updated` — status changed
- `budget_updated` — budget/spent updated

Channel: `agent:{agent_id}:events`.

## Notifications

When a purchase request goes to `pending`, the account owner is notified via all configured channels:

- **Web Push** — browser push notifications (requires VAPID keys)
- **Email** — message with Approve / Reject action links
- **Telegram** — message with inline Approve / Reject buttons

### Action tokens

Action tokens enable approve/reject directly from email links or Telegram buttons without logging in. Each token is one-time, stored in Redis, and expires together with the purchase request (TTL = `request_expiry_minutes`). Once used, the token is deleted.

### Notification dispatcher

The dispatcher (`services/notifications.py`) fans out to all channels enabled in `notification_channels` in parallel. If no channels are configured, legacy behavior applies: Web Push first, then email fallback.

### Database tables

- `notification_channels` — per-account channel configuration (type, credentials, enabled flag)
- `notification_log` — audit log of sent notifications (channel, status, error). Auto-cleaned after 30 days.

## Configuration

All settings via environment variables loaded through pydantic-settings (`app/config.py`). `.env` file in dev, environment variables in production.

Key env vars for development:

```
DATABASE_URL=postgresql+asyncpg://letagentpay:letagentpay@localhost:5434/letagentpay
REDIS_URL=redis://localhost:6380
JWT_SECRET=dev-secret
ANTHROPIC_API_KEY=sk-ant-...
```

PostgreSQL on port **5434**, Redis on **6380** (non-standard — to avoid conflicts with local instances).

## Repositories and Release

The project is distributed across multiple GitHub repositories:

| Repository | Content | CI Pipeline |
|-----------|---------|-------------|
| [LetAgentPay/letagentpay](https://github.com/LetAgentPay/letagentpay) | Core (open-source): backend, frontend, docs | Tests → GitHub Release → Deploy |
| [LetAgentPay/letagentpay-python](https://github.com/LetAgentPay/letagentpay-python) | Python SDK (`pip install letagentpay`) | Tests → GitHub Release → PyPI publish |

### Release process

The entire project uses unified versioning (`version.py`). The SDK has its own version in `sdk/pyproject.toml`.

```bash
make release patch|minor|major
```

This command:
1. Bumps version in `version.py`
2. Creates a `release: vX.Y.Z` commit and pushes to main
3. Syncs to all target repositories
4. CI on each repo automatically: runs tests → creates GitHub Release → deploys/publishes
