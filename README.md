# LetAgentPay

[![Release](https://img.shields.io/github/v/release/letagentpay/letagentpay?style=flat-square&label=release&color=blue)](https://github.com/letagentpay/letagentpay/releases)
[![Changelog](https://img.shields.io/badge/changelog-keep%20a%20changelog-orange?style=flat-square)](docs/CHANGELOG.md)
[![License: BSL 1.1](https://img.shields.io/badge/license-BSL%201.1-yellow?style=flat-square)](LICENSE)
[![x402](https://img.shields.io/badge/x402-supported-7c3aed?style=flat-square)](docs/x402.md)
[![MCP](https://img.shields.io/badge/MCP-server-f97316?style=flat-square)](docs/mcp_server.md)
[![PyPI](https://img.shields.io/pypi/v/letagentpay?style=flat-square&logo=pypi&logoColor=white&label=python%20sdk)](https://pypi.org/project/letagentpay/)
[![npm](https://img.shields.io/npm/v/letagentpay?style=flat-square&logo=npm&label=js%20sdk)](https://www.npmjs.com/package/letagentpay)

> **The spend-control layer for AI agents.** Budgets, plain-English policies, and human override on top of any payment rail.

**Agents can't read your card statement at 3 a.m.**
**Agents can't notice they're about to loop and burn $1,000 on the same API.**
**Agents can't say "no" to themselves.**

So we built the layer that does. LetAgentPay sits between your agent and any payment (Stripe, x402, prepaid wallets, gift cards) with three guarantees:

- **Hard ceiling.** The agent cannot exceed the daily / weekly / monthly budget you set. Period.
- **Plain-English policies.** Write rules like *"no purchases after midnight"* or *"auto-approve groceries under $50"* — AI converts them to enforced JSON config.
- **Real-time human override.** Pending requests appear on a live dashboard with one-click approve / reject (SSE updates, mobile push, email).

<p align="center">
  <img src="docs/assets/demo.gif" alt="LetAgentPay demo — agent sends purchase requests, policy engine approves/rejects in real time" width="720">
</p>

## How it compares

LetAgentPay is the **policy layer**, not another payment rail. It's the only project in the agent-payments space focused on rail-agnostic spend control with human-in-the-loop:

|                                            | [Stripe Agent Toolkit](https://github.com/stripe/agent-toolkit) | [Coinbase CDP](https://github.com/coinbase/cdp-sdk) | [BlockRunAI ClawRouter](https://github.com/BlockRunAI/ClawRouter) | [WLFI AgentPay SDK](https://github.com/worldliberty/agentpay-sdk) | **LetAgentPay** |
| ------------------------------------------ | --------------------- | ------------- | --------------------- | ----------------- | --------------- |
| **Primary focus**                          | Stripe API for agents | Crypto wallet SDK | LLM router with USDC pay | Self-custodial crypto wallet | **Spend-control policy layer** |
| **Payment rails**                          | Stripe only           | Crypto only   | LLM API only          | Crypto only       | **Any rail**    |
| Daily / weekly / monthly cap               | ❌                    | ❌            | ❌                    | ✅                | ✅              |
| Category rules                             | ❌                    | ❌            | ❌                    | partial           | ✅              |
| Schedule (e.g. business hours only)        | ❌                    | ❌            | ❌                    | ❌                | ✅              |
| Plain-English policy → JSON config         | ❌                    | ❌            | ❌                    | ❌                | ✅              |
| Real-time human approval (SSE + push)      | ❌                    | ❌            | ❌                    | ❌                | ✅              |
| Audit trail of every attempt               | partial               | partial       | partial               | partial           | ✅              |
| x402 micropayments                         | ❌                    | partial       | ✅                    | partial           | ✅              |
| Works on top of an existing rail           | n/a                   | n/a           | n/a                   | n/a               | ✅              |
| License                                    | MIT                   | MIT           | MIT                   | MIT               | BSL 1.1 → Apache 2.0 |

Use LetAgentPay on top of Stripe, x402, or any execution backend you already have.

## x402 — first-class support

[![x402](https://img.shields.io/badge/x402-HTTP_402_micropayments-7c3aed?style=for-the-badge)](https://x402.org)

Every x402 micropayment your agent signs runs through the same policy engine as a Stripe transaction:

- **Hard caps that apply on-chain too.** Daily / weekly / monthly limits apply to x402 the same way they apply to any other rail — one bucket, one source of truth.
- **Live exchange rates.** USDC ↔ USD conversion happens at authorization time (15-second TTL), so budgets stay in the user's currency.
- **Non-custodial by design.** LetAgentPay never touches private keys or funds. It signs an authorization; the agent signs the transaction.
- **tx-hash dedup.** One on-chain transaction cannot close two authorizations — replay protection out of the box.
- **Actual-amount reconciliation.** Budget is auto-corrected when settlement differs from authorization.

```
1. Agent → GET resource → HTTP 402 + payment requirements
2. Agent → POST /x402/authorize → LetAgentPay checks policy → authorized
3. Agent → signs tx with own wallet → pays → gets resource
4. Agent → POST /x402/report → tx_hash for audit
```

Full guide: [docs/x402.md](docs/x402.md) · Authorize endpoint: [Agent API reference — x402](docs/agent_api_reference.md#x402-payment-authorization)

## What's inside

- **8-check policy engine** — status, category, per-request limit, schedule, daily/weekly/monthly limits, budget
- **Auto-approve** — trusted categories and small amounts go through automatically
- **Fund holding** — pending requests reserve budget, preventing overspend on races
- **x402 facilitator-ready** — sign and authorize HTTP 402 micropayments inside the same policy
- **9 framework integrations** out of the box (Vercel AI SDK, Google ADK, Stripe, OpenAI Agents, LangChain, CrewAI, Claude MCP, OpenClaw, plus raw HTTP)

## Quick Start (Self-Hosted)

```bash
git clone https://github.com/letagentpay/letagentpay.git
cd letagentpay
cp .env.example .env        # edit JWT_SECRET and ADMIN_PASSWORD
docker compose up -d
```

Open http://localhost:3000 and log in with the password from `.env`.

That's it — running in under 2 minutes.

## Connect Your AI Agent

### Option A — MCP (no code)

Add to your Claude Desktop / MCP client config:

```json
{
  "mcpServers": {
    "letagentpay": {
      "command": "npx",
      "args": ["letagentpay-mcp"],
      "env": { "LETAGENTPAY_TOKEN": "agt_xxx" }
    }
  }
}
```

### Option B — Python SDK

```bash
pip install letagentpay
```

```python
from letagentpay import LetAgentPay

client = LetAgentPay(token="agt_xxx")
result = client.request_purchase(
    amount=15.0,
    category="subscriptions",
    description="OpenAI GPT-4 API call"
)

if result.status == "auto_approved":
    # proceed with purchase
    ...
elif result.status == "pending":
    # wait for human approval
    ...
```

### Option C — TypeScript SDK

```bash
npm install letagentpay
```

```typescript
import { LetAgentPay } from "letagentpay";

const client = new LetAgentPay({ token: "agt_xxx" });
const result = await client.requestPurchase({
  amount: 15.0,
  category: "subscriptions",
  description: "OpenAI GPT-4 API call",
});
```

### Option D — HTTP API

```bash
curl -X POST http://localhost:8000/api/v1/agent-api/requests \
  -H "Authorization: Bearer agt_xxx" \
  -H "Content-Type: application/json" \
  -d '{"amount": 15, "category": "subscriptions", "description": "OpenAI GPT-4"}'
```

See the full [Agent API Reference](docs/agent_api_reference.md).

## How It Works

```
AI Agent                      LetAgentPay                    Human
   │                              │                            │
   ├── POST /agent-api/requests ─►│                            │
   │                              ├── policy engine (8 checks) │
   │                              │                            │
   │   ┌─ auto_approved ──────────┤                            │
   │   │                          ├── pending ──► dashboard ──►│
   │   │                          │              (SSE live)    ├── approve/reject
   │   │                          │◄────────────────────────── │
   │◄──┴── response ──────────────┤                            │
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (async), Python 3.14 |
| Database | PostgreSQL 16, SQLAlchemy async |
| Cache / Pub-sub | Redis 7 |
| Frontend | Next.js 15, React 19, Tailwind CSS v4 |
| Auth | JWT (cookies) + Bearer tokens (agent API) |
| AI | Claude API (natural language → policy JSON) |

## Development

```bash
# Prerequisites: Python 3.14+, Node.js 22+, Docker

# Start PostgreSQL + Redis
docker compose up -d

# Install dependencies
make install-dev

# Run migrations
make migrate

# Start backend (8000) + frontend (3000)
make run
```

### Commands

```bash
make format           # black + ruff --fix
make lint             # ruff + mypy + next lint
make test             # all tests (backend + frontend)
make test-unit        # unit tests only
```

### Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py            # Settings (pydantic-settings)
│   ├── models.py            # SQLAlchemy models
│   ├── routers/             # API endpoints
│   └── services/
│       ├── policy_engine.py # 8-check request validation
│       ├── spending.py      # Redis spending counters
│       ├── ai_policy.py     # Claude: text → policy JSON
│       └── realtime.py      # Redis pub/sub → SSE
frontend/
├── src/
│   ├── app/                 # Pages (App Router)
│   ├── components/          # React components
│   └── lib/                 # API client, types, hooks
mcp-server/                  # MCP server (npx letagentpay-mcp)
sdk/                         # Python SDK (pip install letagentpay)
sdk-js/                      # TypeScript SDK (npm install letagentpay)
sdk-vercel-ai/               # Vercel AI SDK tools (npm install @letagentpay/ai)
openclaw-skill/              # OpenClaw skill
```

## Integrations

LetAgentPay works with popular AI agent frameworks and platforms out of the box:

| Platform | How | Docs |
|----------|-----|------|
| **Vercel AI SDK** | npm package (`@letagentpay/ai`) | [Guide](docs/integrations/vercel_ai.md) |
| **Google ADK** | Plain function tools | [Guide](docs/integrations/google_adk.md) |
| **Stripe** | Policy middleware before payments | [Guide](docs/integrations/stripe.md) |
| **OpenAI Agents SDK** | Function tool (`@function_tool`) | [Guide](docs/integrations/openai_agents.md) |
| **LangChain** | Custom tool (`BaseTool`) | [Guide](docs/integrations/langchain.md) |
| **CrewAI** | CrewAI tool (`@tool`) | [Guide](docs/integrations/crewai.md) |
| **Claude MCP** | MCP server (`npx letagentpay-mcp`) | [Guide](docs/mcp_server.md) |
| **OpenClaw** | Skill for Claude Code agents | [OpenClaw skill](openclaw-skill/) |

Each integration wraps `request_purchase()` in the framework's native tool format — the agent asks for permission before spending, and LetAgentPay enforces the policy.

See [docs/integrations/](docs/integrations/) for detailed guides.

## Documentation

- [Self-Hosting Guide](docs/self_host.md)
- [Agent API Reference](docs/agent_api_reference.md)
- [Architecture](docs/architecture.md)
- [MCP Server](docs/mcp_server.md)
- [Python SDK](docs/python_sdk.md)
- [TypeScript SDK](docs/typescript_sdk.md)
- [Budget Rules](docs/budget_rules.md)
- [x402 Integration](docs/x402.md)
- [Integrations](docs/integrations/) — Vercel AI SDK, Google ADK, Stripe, OpenAI Agents, LangChain, CrewAI, MCP, OpenClaw
- [Contributing](CONTRIBUTING.md)
- [Changelog](docs/CHANGELOG.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[Business Source License 1.1](LICENSE) — free to use and self-host. The source is open, with a time-delayed conversion to Apache 2.0.
