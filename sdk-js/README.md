# letagentpay

TypeScript SDK for [LetAgentPay](https://letagentpay.com) — AI agent spending policy middleware. Set budgets, define spending policies, and control AI agent purchases.

**Zero dependencies.** Uses the built-in `fetch` API (Node.js 18+, Bun, Deno).

## Installation

```bash
npm install letagentpay
```

## Quick Start

```typescript
import { LetAgentPay } from "letagentpay";

const client = new LetAgentPay({ token: "agt_xxx" });

// Create a purchase request
const result = await client.requestPurchase({
  amount: 15.0,
  category: "api_calls",
  description: "OpenAI GPT-4 call",
});
console.log(result.status); // "auto_approved" | "pending" | "rejected"

// Check budget
const budget = await client.checkBudget();
console.log(`Remaining: $${budget.remaining}`);
```

## API

### `requestPurchase(options)`

Create a purchase request. The policy engine runs 8 deterministic checks (budget, category, per-request limit, schedule, daily/weekly/monthly limits).

```typescript
const result = await client.requestPurchase({
  amount: 25.0,
  category: "software",
  merchantName: "GitHub",         // optional
  description: "Copilot license", // optional
  agentComment: "Monthly renewal", // optional, shown to reviewers
});

// result.status: "auto_approved" | "pending" | "rejected"
// result.requestId: "uuid"
// result.policyCheck: { passed: true, checks: [...] }
// result.budgetRemaining: 475.0 (only if auto_approved)
// result.expiresAt: "2026-..." (only if pending)
```

### `checkRequest(requestId)`

Check the status of a purchase request.

```typescript
const status = await client.checkRequest("request-uuid");
// status.status: "auto_approved" | "pending" | "approved" | "rejected" | "expired"
```

### `confirmPurchase(requestId, options)`

Confirm a purchase after approval. Use this to report the actual amount spent.

```typescript
await client.confirmPurchase("request-uuid", {
  success: true,
  actualAmount: 24.99,             // optional, if different from requested
  receiptUrl: "https://example.com/receipt", // optional
});
```

### `checkBudget()`

Get current budget breakdown.

```typescript
const budget = await client.checkBudget();
// budget.budget: 500.0
// budget.spent: 125.5
// budget.held: 25.0   (reserved for pending requests)
// budget.remaining: 349.5
// budget.currency: "USD"
```

### `getPolicy()`

Get the current spending policy.

```typescript
const policy = await client.getPolicy();
```

### `listCategories()`

List categories configured for the authenticated agent's account. Categories are per-account -- new accounts start with just `"other"`. Import defaults or create custom categories in the dashboard.

```typescript
const categories = await client.listCategories();
// ["groceries", "subscriptions", "other", ...]
```

### `myRequests(options?)`

List agent's purchase requests with optional filters.

```typescript
const list = await client.myRequests({ status: "pending", limit: 10 });
// list.requests: [{ requestId, status, amount, category, ... }]
// list.total: 42
```

## guard()

Wrap an async function so it checks spending policy before executing:

```typescript
import { guard } from "letagentpay";

const callOpenAI = guard(
  async (prompt: string, cost: number) => {
    // your OpenAI call here
    return "response";
  },
  { token: "agt_xxx", category: "api_calls" }
);

// Automatically sends a purchase request for $0.03 before executing
await callOpenAI("Analyze this document", 0.03);
```

With a fixed amount:

```typescript
const sendEmail = guard(
  async (to: string, body: string) => { /* ... */ },
  { token: "agt_xxx", category: "email", amount: 0.01 }
);
```

## x402 Crypto-Micropayments

Authorize on-chain USDC payments via the x402 protocol. Same policy engine, same token — different payment rail.

```typescript
const client = new LetAgentPay({ token: "agt_xxx" });

// Agent receives HTTP 402 — ask LAP for authorization
const auth = await client.x402.authorize({
  amountUsd: 0.05,
  payTo: "0xMerchant...",
  resourceUrl: "https://api.example.com/data",
});

if (auth.authorized) {
  // Sign tx with your own wallet, then report
  await client.x402.report({
    authorizationId: auth.authorizationId!,
    txHash: "0xabc123...",
  });
} else {
  console.log(`Declined: ${auth.reason}`);
}

// Check x402 budget and wallets
const budget = await client.x402.budget();

// Register wallet address (LAP never holds keys)
await client.x402.registerWallet({ walletAddress: "0x1234..." });
```

## Self-Hosted

Point the SDK to your own LetAgentPay instance:

```typescript
const client = new LetAgentPay({
  token: "agt_xxx",
  baseUrl: "http://localhost:8000/api/v1/agent-api",
});
```

## Environment Variables

```bash
export LETAGENTPAY_TOKEN=agt_xxx
export LETAGENTPAY_BASE_URL=https://api.letagentpay.com/api/v1/agent-api  # optional
```

```typescript
// Token is taken from LETAGENTPAY_TOKEN
const client = new LetAgentPay();
```

## Error Handling

```typescript
import { LetAgentPay, LetAgentPayError } from "letagentpay";

try {
  await client.requestPurchase({ amount: 100, category: "hardware" });
} catch (e) {
  if (e instanceof LetAgentPayError) {
    console.log(e.status); // 403
    console.log(e.detail); // "Daily limit exceeded"
  }
}
```

## Security Model

LetAgentPay uses **server-side cooperative enforcement**. When your agent calls `requestPurchase()`, the request is evaluated by the policy engine on the LetAgentPay server. The agent receives only the result (approved/denied/pending) and cannot:

- Modify its own policies (the `agt_` token grants access only to the Agent API)
- Override policy check results (they come from the server)
- Approve its own pending requests (only a human can do that via the dashboard)

This is a **cooperative model** — it protects against budget overruns, category violations, and scheduling mistakes by well-behaved agents. It does not sandbox a malicious agent that has direct access to payment APIs.

### Best Practices

- **Don't give your agent raw payment credentials** (Stripe keys, credit card numbers). LetAgentPay should be the only spending channel
- Use `pending` + manual approval for high-value purchases
- Set per-request limits as an additional barrier
- Review the audit trail in the dashboard regularly

## Documentation

- [LetAgentPay docs](https://letagentpay.com/developers)
- [Agent API Reference](https://letagentpay.com/developers)
- [Python SDK](https://github.com/LetAgentPay/letagentpay-python)
- [GitHub](https://github.com/LetAgentPay/letagentpay-js)

## License

MIT
