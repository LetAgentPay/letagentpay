# Vercel AI SDK Integration

Use LetAgentPay with the [Vercel AI SDK](https://ai-sdk.dev/) to add spending controls to your AI agents in TypeScript/JavaScript.

## Installation

```bash
npm install @letagentpay/ai ai zod
```

## Quick Start

```typescript
import { generateText } from "ai";
import { anthropic } from "@ai-sdk/anthropic";
import { createLetAgentPayTools } from "@letagentpay/ai";

const tools = createLetAgentPayTools(); // reads LETAGENTPAY_TOKEN from env

const { text } = await generateText({
  model: anthropic("claude-sonnet-4-20250514"),
  prompt: "Buy the cheapest weather API plan",
  tools,
});
```

## Available Tools

| Tool | Description |
| --- | --- |
| `requestPurchase` | Request approval to spend money (call BEFORE any purchase) |
| `checkBudget` | Check current budget, spent, held, and remaining |
| `listCategories` | List account's custom spending categories |
| `myRequests` | List recent purchase requests (optionally filter by status) |
| `confirmPurchase` | Confirm or report failure after completing a purchase |

## Using with streamText

```typescript
import { streamText } from "ai";
import { anthropic } from "@ai-sdk/anthropic";
import { createLetAgentPayTools } from "@letagentpay/ai";

const tools = createLetAgentPayTools({ token: "agt_..." });

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

## Using Individual Tools

If you only need specific tools, create them individually:

```typescript
import { createRequestPurchaseTool, createCheckBudgetTool } from "@letagentpay/ai";
import { LetAgentPay } from "letagentpay";

const client = new LetAgentPay({ token: "agt_..." });

const tools = {
  purchase: createRequestPurchaseTool(client),
  budget: createCheckBudgetTool(client),
};
```

## Self-Hosted

```typescript
const tools = createLetAgentPayTools({
  token: "agt_...",
  baseUrl: "https://your-instance.com/api/v1/agent-api",
});
```

## How It Works

1. The agent decides it needs to make a purchase
2. It calls `requestPurchase` with amount, category, merchant, and description
3. LetAgentPay checks the request against your spending policies (budget, category restrictions, daily/weekly/monthly limits, schedule)
4. The tool returns the decision: **auto_approved**, **pending**, or **rejected**
5. The agent proceeds only if approved

## Categories

Categories are per-account and fully customizable. New accounts start with just `"other"` — import the 16 default categories with one click from the dashboard, or create your own with optional aliases. Use the `listCategories` tool to get the valid list at runtime. Unknown categories are resolved to `"other"` and flagged for review in the dashboard.

## Resources

- [TypeScript SDK Documentation](../js_sdk.md)
- [Agent API Reference](../agent_api_reference.md)
- [Budget Rules](../budget_rules.md)
