# letagentpay-mcp

MCP server for [LetAgentPay](https://letagentpay.com) — AI agent spending policy middleware. Works with Claude Desktop, Claude Code, Cursor, OpenClaw, and any MCP-compatible client.

## Setup

Add to your MCP client config:

```json
{
  "mcpServers": {
    "letagentpay": {
      "command": "npx",
      "args": ["-y", "letagentpay-mcp"],
      "env": {
        "LETAGENTPAY_TOKEN": "agt_xxx"
      }
    }
  }
}
```

Get your agent token at [letagentpay.com](https://letagentpay.com) or from your self-hosted instance.

### Self-hosted

```json
{
  "mcpServers": {
    "letagentpay": {
      "command": "npx",
      "args": ["-y", "letagentpay-mcp"],
      "env": {
        "LETAGENTPAY_TOKEN": "agt_xxx",
        "LETAGENTPAY_API_URL": "http://localhost:8000/api/v1"
      }
    }
  }
}
```

## Tools

| Tool | Description |
|------|-------------|
| `request_purchase` | Submit a purchase request for policy evaluation |
| `check_budget` | View current budget, spent, held, and remaining |
| `list_categories` | List valid purchase categories |
| `my_requests` | Check status of a specific purchase request |
| `list_requests` | List purchase requests with optional status filter |
| `confirm_purchase` | Confirm purchase completion (or failure) |

Every purchase request goes through 8 deterministic policy checks: agent status, category, per-request limit, schedule, daily/weekly/monthly limits, and total budget.

## Environment Variables

| Variable | Required | Default |
|----------|----------|---------|
| `LETAGENTPAY_TOKEN` | Yes | — |
| `LETAGENTPAY_API_URL` | No | `https://api.letagentpay.com/api/v1` |

## SDKs

For programmatic integration without MCP:

- **Python**: `pip install letagentpay`
- **TypeScript**: `npm install letagentpay`

## Links

- [LetAgentPay](https://letagentpay.com)
- [GitHub](https://github.com/LetAgentPay/letagentpay)
- [OpenClaw Skill](https://github.com/LetAgentPay/letagentpay-openclaw)

## License

MIT
