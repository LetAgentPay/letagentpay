# TypeScript SDK (letagentpay)

TypeScript SDK for integrating AI agents with LetAgentPay. Provides an API client and a `guard()` wrapper for automatic policy checking. Zero dependencies -- uses the built-in `fetch` API (Node.js 18+, Bun, Deno).

## Installation

```bash
npm install letagentpay
```

## Quick Start

### Client

```typescript
import { LetAgentPay } from "letagentpay";

const client = new LetAgentPay({ token: "agt_xxx" });

// Purchase request
const result = await client.requestPurchase({
  amount: 15.0,
  category: "subscriptions",
  description: "OpenAI GPT-4 call",
  agentComment: "Needed for document analysis",
});

if (result.status === "auto_approved") {
  // Execute the purchase
  await doPurchase();
  // Confirm the result
  await client.confirmPurchase(result.requestId, {
    success: true,
    actualAmount: 14.50,
    receiptUrl: "https://example.com/receipt/123",
  });
} else if (result.status === "pending") {
  console.log("Waiting for owner approval...");
} else {
  console.log("Rejected");
}
```

### Budget Check

```typescript
const budget = await client.checkBudget();
console.log(`Budget: ${budget.budget}, spent: ${budget.spent}, held: ${budget.held}, remaining: ${budget.remaining}`);
```

### List Categories

```typescript
const categories = await client.listCategories();
// ["groceries", "subscriptions", "transport", ...]
```

### My Requests

```typescript
const list = await client.myRequests({ status: "pending", limit: 5 });
for (const req of list.requests) {
  console.log(`${req.requestId}: ${req.amount} ${req.currency} — ${req.status}`);
}
console.log(`Total: ${list.total}`);
```

## guard()

Wraps an async function so it automatically checks spending policy before executing. If the request is rejected or pending, the function is not called.

```typescript
import { guard } from "letagentpay";

const callOpenAI = guard(
  async (prompt: string, cost: number) => {
    return openai.chat.completions.create({
      model: "gpt-4",
      messages: [{ role: "user", content: prompt }],
    }).choices[0].message.content;
  },
  { token: "agt_xxx", category: "api_calls" }
);

// When called, it automatically:
// 1. Sends request_purchase to LetAgentPay (amount extracted from numeric arg)
// 2. If approved — executes the function
// 3. If rejected/pending — throws LetAgentPayError
const result = await callOpenAI("Analyze this document", 0.03);
```

### With fixed amount

```typescript
const sendEmail = guard(
  async (to: string, body: string) => { /* send email */ },
  { token: "agt_xxx", category: "email", amount: 0.01 }
);
```

### guard() Options

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | string | Yes* | Agent bearer token (`agt_xxx`) |
| `client` | LetAgentPay | No | Existing client instance (alternative to token) |
| `category` | string | No | Expense category (default `"other"`) |
| `amount` | number | No | Fixed amount (if not specified, extracted from numeric function argument) |
| `description` | string | No | Purchase description |
| `agentComment` | string | No | Agent comment |

\* Required if `client` is not provided.

## Configuration

### Via Environment Variables

```bash
export LETAGENTPAY_TOKEN=agt_xxx
export LETAGENTPAY_BASE_URL=https://api.letagentpay.com/api/v1/agent-api  # optional
```

```typescript
// Token is taken from LETAGENTPAY_TOKEN
const client = new LetAgentPay();
```

### Via Config Object

```typescript
const client = new LetAgentPay({
  token: "agt_xxx",
  baseUrl: "https://api.letagentpay.com/api/v1/agent-api", // default
});
```

### Self-Hosted

```typescript
const client = new LetAgentPay({
  token: "agt_xxx",
  baseUrl: "http://localhost:8000/api/v1/agent-api",
});
```

## API Reference

### LetAgentPay

| Method | Returns | Description |
|--------|---------|-------------|
| `requestPurchase(options)` | `PurchaseResult` | Purchase request |
| `checkRequest(requestId)` | `RequestStatus` | Check request status |
| `confirmPurchase(requestId, options)` | `ConfirmResult` | Confirm purchase result |
| `checkBudget()` | `BudgetInfo` | Check budget |
| `getPolicy()` | `object` | Get current policy |
| `listCategories()` | `string[]` | List available categories |
| `myRequests(options?)` | `RequestList` | List agent requests |

### Response Types

**PurchaseResult:**
| Field | Type | Description |
|-------|------|-------------|
| `requestId` | string | Request ID |
| `status` | string | `auto_approved`, `pending`, `rejected` |
| `category` | string? | Category (normalized) |
| `policyCheck` | PolicyResult? | Policy check results |
| `autoApproved` | boolean | Whether auto-approved |
| `budgetRemaining` | number? | Remaining budget |
| `expiresAt` | string? | Expiration time (ISO 8601) |

**BudgetInfo:**
| Field | Type | Description |
|-------|------|-------------|
| `budget` | number | Total budget |
| `spent` | number | Amount spent |
| `held` | number | Amount held (pending) |
| `remaining` | number | Remaining balance |
| `currency` | string? | Currency |

**RequestList:**
| Field | Type | Description |
|-------|------|-------------|
| `requests` | PurchaseRequestInfo[] | List of requests |
| `total` | number | Total count |
| `limit` | number | Page limit |
| `offset` | number | Offset |

## Error Handling

```typescript
import { LetAgentPay, LetAgentPayError } from "letagentpay";

try {
  await client.requestPurchase({ amount: 100, category: "test" });
} catch (e) {
  if (e instanceof LetAgentPayError) {
    console.log(`API error: [${e.status}] ${e.detail}`);
  }
}
```

## Security Model

Policy enforcement happens on the LetAgentPay server. The agent token (`agt_`) only grants access to submit purchase requests and check status -- it cannot modify policies or approve its own requests.

This is a cooperative enforcement model: it protects against budget overruns, category violations, and scheduling mistakes. Don't give your agent raw payment credentials (Stripe keys, credit card numbers) -- LetAgentPay should be the only spending channel.

## File Structure

```
sdk-js/
├── package.json
├── tsup.config.ts
├── README.md
├── LICENSE
├── src/
│   ├── index.ts        # Exports: LetAgentPay, guard, types
│   ├── client.ts       # HTTP client
│   ├── guard.ts        # guard() wrapper
│   ├── types.ts        # TypeScript interfaces
│   └── errors.ts       # LetAgentPayError
└── tests/
    ├── client.test.ts
    └── guard.test.ts
```

## Related Documents

- [Agent API Reference](agent_api_reference.md) -- full API description
- [Python SDK](python_sdk.md) -- Python equivalent
- [MCP Server](mcp_server.md) -- alternative connection method (no code required)
