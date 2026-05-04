# @letagentpay/ai

LetAgentPay tools for [Vercel AI SDK](https://ai-sdk.dev/) — spending governance for AI agents.

## Installation

```bash
npm install @letagentpay/ai ai zod
```

## Quick Start

```typescript
import { generateText } from "ai";
import { anthropic } from "@ai-sdk/anthropic";
import { createLetAgentPayTools } from "@letagentpay/ai";

const tools = createLetAgentPayTools({ token: "agt_..." });

const { text } = await generateText({
  model: anthropic("claude-sonnet-4-20250514"),
  prompt: "Buy the cheapest weather API plan",
  tools,
});
```

## Tools

| Tool | Description |
| --- | --- |
| `requestPurchase` | Request approval to spend money (call BEFORE any purchase) |
| `checkBudget` | Check current budget, spent, held, and remaining |
| `listCategories` | List account's custom spending categories |
| `myRequests` | List recent purchase requests (optionally filtered by status) |
| `confirmPurchase` | Confirm or report failure after completing a purchase |

## Configuration

```typescript
// Token from parameter
const tools = createLetAgentPayTools({ token: "agt_..." });

// Token from LETAGENTPAY_TOKEN env var
const tools = createLetAgentPayTools();

// Self-hosted instance
const tools = createLetAgentPayTools({
  token: "agt_...",
  baseUrl: "https://your-instance.com/api/v1/agent-api",
});
```

## Using Individual Tools

```typescript
import { createRequestPurchaseTool, createCheckBudgetTool } from "@letagentpay/ai";
import { LetAgentPay } from "letagentpay";

const client = new LetAgentPay({ token: "agt_..." });

const tools = {
  purchase: createRequestPurchaseTool(client),
  budget: createCheckBudgetTool(client),
};
```

## How It Works

1. Agent decides it needs to make a purchase
2. It calls `requestPurchase` with amount, category, merchant, and description
3. LetAgentPay checks the request against spending policies (budget limits, category restrictions, daily/weekly/monthly caps, schedule)
4. Tool returns the decision: **auto_approved**, **pending** (needs human review), or **rejected**
5. Agent proceeds only if approved, adapts if rejected

## Streaming

Works with `streamText` the same way:

```typescript
import { streamText } from "ai";

const result = streamText({
  model: anthropic("claude-sonnet-4-20250514"),
  prompt: "Find and buy a domain name under $15",
  tools,
  maxSteps: 5,
});

for await (const part of result.textStream) {
  process.stdout.write(part);
}
```

## Resources

- [LetAgentPay Documentation](https://letagentpay.com/docs)
- [Agent API Reference](https://letagentpay.com/docs/agent-api)
- [Vercel AI SDK Docs](https://ai-sdk.dev/)
