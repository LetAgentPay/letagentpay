export function GET() {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://letagentpay.com";

  const content = `# LetAgentPay — Full API Reference

> AI agent spending management platform — policy middleware between AI agents and payments.

LetAgentPay lets humans define spending policies (budgets, category limits, schedules) for their AI agents. Agents send purchase requests via API; the platform validates them against policies and returns approve/reject decisions in real time.

## Quick Start

1. Sign up at ${siteUrl}/auth/signin
2. Create an agent in the dashboard → get a Bearer token (\`agt_...\`)
3. Send purchase requests from your agent code

## Authentication

All Agent API endpoints use Bearer token authentication:

\`\`\`
Authorization: Bearer agt_your_token_here
\`\`\`

Tokens are generated when you create an agent in the dashboard.

## Base URL

\`\`\`
${siteUrl}/api/v1/agent-api
\`\`\`

## API Endpoints

### POST /requests — Create Purchase Request

Submit a purchase request for policy evaluation.

**Request:**
\`\`\`json
{
  "amount": 49.99,
  "currency": "USD",
  "category": "groceries",
  "merchant_name": "Whole Foods",
  "description": "Weekly groceries",
  "agent_comment": "Needed for meal prep this week"
}
\`\`\`

**Response (201):**
\`\`\`json
{
  "request_id": "uuid",
  "status": "auto_approved | pending | rejected",
  "currency": "USD",
  "policy_check": {
    "passed": true,
    "checks": [
      {"rule": "status", "result": "pass", "detail": "Agent is active"},
      {"rule": "category", "result": "pass", "detail": "groceries in allowed list"},
      {"rule": "budget", "result": "pass", "detail": "9950.01 remaining >= 49.99"}
    ]
  },
  "auto_approved": true,
  "budget_remaining": 9950.01,
  "expires_at": null
}
\`\`\`

**Categories:** accommodation, clothing, education, electronics, entertainment, flights, food_delivery, gas, groceries, health, household, other, restaurants, subscriptions, taxi, transport

> Unknown categories are automatically mapped to the closest match. The original category text is preserved in the \`original_category\` field of the response.

### GET /requests/{request_id} — Check Request Status

Poll for status updates on a pending request.

**Response:**
\`\`\`json
{
  "request_id": "uuid",
  "status": "pending | approved | auto_approved | rejected | expired | completed | failed",
  "amount": 49.99,
  "category": "groceries",
  "created_at": "2026-03-18T12:00:00",
  "reviewed_at": "2026-03-18T12:05:00"
}
\`\`\`

### POST /requests/{request_id}/confirm — Confirm Purchase

After a request is approved, confirm the actual purchase result.

**Request:**
\`\`\`json
{
  "success": true,
  "actual_amount": 47.50,
  "receipt_url": "https://example.com/receipt/123"
}
\`\`\`

### GET /budget — Get Agent Budget

**Response:**
\`\`\`json
{
  "budget": 10000.00,
  "spent": 49.99,
  "held": 25.00,
  "remaining": 9925.01,
  "currency": "USD"
}
\`\`\`

\`held\` — funds reserved by pending requests awaiting human approval. These are subtracted from \`remaining\` to prevent over-commitment.

### GET /policy — Get Agent Policy

Returns the JSON policy configured for this agent.

### GET /categories — List Valid Categories

Returns all valid category strings.

## Request Lifecycle

1. Agent sends \`POST /requests\` with amount, category, description
2. Policy engine runs 8+ checks: status, category, per-request limit, schedule, daily/weekly/monthly limits, budget, account-level budget rules
3. If all checks pass AND auto-approve criteria met → \`auto_approved\` (immediate)
4. If all checks pass but no auto-approve → \`pending\` (human reviews in dashboard)
5. If any check fails → \`rejected\` (with detailed policy_check explaining why)
6. For pending requests: funds are held (reserved) immediately. Human approves/rejects within configurable timeout (default 30 min, or expires). On expiry/reject, held funds are released
7. After approval: agent calls \`POST /requests/{id}/confirm\` with actual result

## Python SDK

\`\`\`bash
pip install letagentpay
\`\`\`

\`\`\`python
from letagentpay import LetAgentPay

client = LetAgentPay(token="agt_your_token")

# Submit a purchase request
result = client.purchase(
    amount=49.99,
    category="groceries",
    merchant_name="Whole Foods",
    description="Weekly groceries",
)

if result.status == "auto_approved":
    # Proceed with purchase
    client.confirm(result.request_id, success=True, actual_amount=47.50)
elif result.status == "pending":
    # Wait for human approval
    final = client.wait_for_decision(result.request_id, timeout=300)
    if final.status == "approved":
        client.confirm(result.request_id, success=True)
elif result.status == "rejected":
    print(f"Rejected: {result.policy_check}")
\`\`\`

### Decorator Pattern

\`\`\`python
from letagentpay import LetAgentPay, guard

client = LetAgentPay(token="agt_your_token")

@guard(client, category="groceries")
def buy_groceries(items: list[str]) -> dict:
    \"\"\"This function will only execute if the purchase is approved.\"\"\"
    total = calculate_total(items)
    return {"items": items, "total": total}
\`\`\`

## MCP Server

For Claude Desktop, add to \`claude_desktop_config.json\`:

\`\`\`json
{
  "mcpServers": {
    "letagentpay": {
      "command": "npx",
      "args": ["-y", "@anthropic/letagentpay-mcp"],
      "env": {
        "LETAGENTPAY_TOKEN": "agt_your_token"
      }
    }
  }
}
\`\`\`

For Cursor, add to \`.cursor/mcp.json\`:

\`\`\`json
{
  "mcpServers": {
    "letagentpay": {
      "command": "npx",
      "args": ["-y", "@anthropic/letagentpay-mcp"],
      "env": {
        "LETAGENTPAY_TOKEN": "agt_your_token"
      }
    }
  }
}
\`\`\`

Available MCP tools: \`purchase_request\`, \`check_request_status\`, \`confirm_purchase\`, \`get_budget\`, \`get_policy\`, \`list_categories\`.

## REST API (curl)

\`\`\`bash
# Create purchase request
curl -X POST ${siteUrl}/api/v1/agent-api/requests \\
  -H "Authorization: Bearer agt_your_token" \\
  -H "Content-Type: application/json" \\
  -d '{"amount": 49.99, "category": "groceries", "merchant_name": "Whole Foods"}'

# List requests (with optional status filter)
curl ${siteUrl}/api/v1/agent-api/requests?status=pending&limit=20 \\
  -H "Authorization: Bearer agt_your_token"

# Check single request status
curl ${siteUrl}/api/v1/agent-api/requests/{request_id} \\
  -H "Authorization: Bearer agt_your_token"

# Confirm purchase
curl -X POST ${siteUrl}/api/v1/agent-api/requests/{request_id}/confirm \\
  -H "Authorization: Bearer agt_your_token" \\
  -H "Content-Type: application/json" \\
  -d '{"success": true, "actual_amount": 47.50}'

# Get budget
curl ${siteUrl}/api/v1/agent-api/budget \\
  -H "Authorization: Bearer agt_your_token"
\`\`\`

## Framework Integrations

LetAgentPay integrates with popular AI agent frameworks via thin wrappers around the Python SDK:

- **LangChain** — custom BaseTool, works with any LangChain agent (see examples/langchain_tool.py)
- **OpenAI Agents SDK** — @function_tool decorator (see examples/openai_agents.py)
- **CrewAI** — CrewAI @tool decorator, supports multi-agent crews with separate budgets (see examples/crewai_agent.py)
- **Claude MCP** — zero-code integration via MCP server (see above)

Each integration follows the same pattern: wrap \`client.request_purchase()\` as a native tool for the framework.

## Error Handling

| Status | Meaning |
|--------|---------|
| 400 | Invalid input (wrong category, currency mismatch) |
| 401 | Missing or invalid bearer token |
| 403 | Agent paused, all agents paused by account owner, or account blocked |
| 404 | Request not found |
| 422 | Validation error (missing fields, invalid types) |

## Account-Level Budget Rules

In addition to per-agent policies, account owners can set account-wide budget rules that apply across all agents:

- **Daily/Weekly/Monthly limits** — cap total spending across all agents
- **Temporal rules** — "total $100 during this 10-hour flight"
- **Day-of-week rules** — different limits for weekdays vs weekends
- **Priority system** — higher priority rules override lower ones

Even if an agent's own policy allows a purchase, it can still be rejected by account-level budget rules.

## Notifications

When a purchase request goes to \`pending\`, the account owner is notified via all configured channels:

- **Email** — notification with one-click Approve / Reject action links
- **Telegram** — bot message with inline Approve / Reject buttons
- **Browser Push** — native push notification for real-time alerts

Channels are configured in the dashboard under **Settings → Notifications**. Telegram is connected via a deep-link from the settings page.
`;

  return new Response(content, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
