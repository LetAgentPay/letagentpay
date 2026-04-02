# MCP Server (letagentpay-mcp)

MCP server for connecting AI agents to LetAgentPay via the Model Context Protocol. Allows agents (Claude Desktop, OpenClaw, and other MCP-compatible clients) to request purchase approvals, check budgets, and confirm results -- without writing any code.

## Installation

npm package `letagentpay-mcp`. No global installation required -- runs via `npx`.

## Configuration

Add the following to your MCP client configuration file:

```json
{
  "mcpServers": {
    "letagentpay": {
      "command": "npx",
      "args": ["letagentpay-mcp"],
      "env": {
        "LETAGENTPAY_TOKEN": "agt_xxx"
      }
    }
  }
}
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LETAGENTPAY_TOKEN` | Yes | Agent bearer token (prefix `agt_`) |

The token can be obtained on the agent connection page: `/dashboard/agent/{id}/connect`.

## Tools

### request_purchase

Sends a purchase request. Goes through policy checking -- can be automatically approved, put on hold, or rejected.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `amount` | number | Yes | Purchase amount |
| `currency` | string | No | Currency (defaults to the agent's currency) |
| `category` | string | Yes | Expense category |
| `description` | string | No | Purchase description |
| `merchant` | string | No | Merchant/service name |
| `agent_comment` | string | No | Agent comment (shown to the owner) |

**Returns:** Request ID, status (`approved`, `pending`, `rejected`), rejection reason.

### check_budget

Checks the agent's current budget -- how much has been spent and how much remains.

**Parameters:** none.

**Returns:** budget, spent, remaining.

### list_categories

Returns the list of available expense categories for the agent.

**Parameters:** none.

**Returns:** array of categories with IDs and names.

### my_requests

Gets the status of a specific purchase request by ID.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | string | Yes | The purchase request ID |

**Returns:** request details (id, status, amount, category, timestamps).

### confirm_purchase

Confirms the purchase result after approval. The agent reports whether the purchase was completed successfully.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | string | Yes | Purchase request ID |
| `success` | boolean | Yes | Was the purchase completed successfully? |
| `actual_amount` | number | No | Actual amount (if different from requested) |
| `receipt_url` | string | No | Receipt/confirmation URL |

**Returns:** updated request status (`completed` or `failed`).

## Connection Examples

### Claude Desktop

Configuration file: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows).

```json
{
  "mcpServers": {
    "letagentpay": {
      "command": "npx",
      "args": ["letagentpay-mcp"],
      "env": {
        "LETAGENTPAY_TOKEN": "agt_xxx"
      }
    }
  }
}
```

After saving the config, restart Claude Desktop. The agent will gain access to the tools `request_purchase`, `check_budget`, `list_categories`, `my_requests`, `confirm_purchase`.

### OpenClaw

Add the MCP server in OpenClaw settings in a similar way -- through the MCP servers config.

## How It Works

1. The AI agent wants to make a purchase
2. It calls the `request_purchase` tool with the amount, category, and description
3. LetAgentPay checks the request against the agent's policy (limits, categories, schedule)
4. If automatically approved -- the agent receives `approved` and executes the purchase
5. If manual approval is required -- the agent receives `pending`, the owner gets a push/email notification
6. After the purchase, the agent calls `confirm_purchase` with the result

## File Structure

```
mcp-server/
├── package.json
├── src/
│   └── index.ts        # Entry point, tool registration
└── README.md
```

## Related Documents

- [Agent API Reference](agent_api_reference.md) -- full API description
- [Python SDK](python_sdk.md) -- alternative connection method
- [Customer Journey Map](customer_journey_map.md) -- Stage 5 (agent connection)
