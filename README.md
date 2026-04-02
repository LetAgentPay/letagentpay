# LetAgentPay

**Policy middleware between AI agents and payments.** Set budgets, define spending policies in plain English, and approve or reject AI agent purchases in real time.

<p align="center">
  <img src="docs/assets/demo.gif" alt="LetAgentPay demo — agent sends purchase requests, policy engine approves/rejects in real time" width="720">
</p>

## The Problem

AI agents can spend money — calling APIs, buying services, paying for subscriptions. But there's no standard way to control *how much* they spend, *on what*, or *when*.

## The Solution

LetAgentPay sits between your AI agent and any payment action. You define the rules, the agent requests permission, and LetAgentPay enforces the policy:

- **Natural language policies** — write rules like "no purchases after midnight" or "auto-approve groceries under $50", and AI converts them to structured config
- **8-check policy engine** — status, category, per-request limit, schedule, daily/weekly/monthly limits, budget
- **Real-time dashboard** — approve or reject pending requests, see spending stats, SSE live updates
- **Auto-approve** — trusted categories and small amounts go through automatically
- **Fund holding** — pending requests reserve budget, preventing overspend

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

### Option C — HTTP API

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
```

## Framework Integrations

LetAgentPay works with popular AI agent frameworks out of the box:

| Framework | How | Example |
|-----------|-----|---------|
| **LangChain** | Custom tool (`BaseTool`) | [langchain_tool.py](examples/langchain_tool.py) |
| **OpenAI Agents SDK** | Function tool (`@function_tool`) | [openai_agents.py](examples/openai_agents.py) |
| **CrewAI** | CrewAI tool (`@tool`) | [crewai_agent.py](examples/crewai_agent.py) |
| **Claude MCP** | MCP server (`npx letagentpay-mcp`) | [MCP docs](docs/mcp_server.md) |

Each integration is a thin wrapper around the [Python SDK](docs/python_sdk.md) — your agent calls `request_purchase()` before spending, and LetAgentPay enforces the policy.

See [docs/integrations/](docs/integrations/) for detailed guides.

## Documentation

- [Self-Hosting Guide](docs/self_host.md)
- [Agent API Reference](docs/agent_api_reference.md)
- [Architecture](docs/architecture.md)
- [MCP Server](docs/mcp_server.md)
- [Python SDK](docs/python_sdk.md)
- [Budget Rules](docs/budget_rules.md)
- [Framework Integrations](docs/integrations/) — LangChain, OpenAI Agents, CrewAI
- [Contributing](CONTRIBUTING.md)
- [Changelog](docs/CHANGELOG.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[Business Source License 1.1](LICENSE) — free to use and self-host. The source is open, with a time-delayed conversion to Apache 2.0.
