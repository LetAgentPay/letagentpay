# ClawRouter Integration

Use LetAgentPay with [ClawRouter](https://github.com/BlockRunAI/ClawRouter) to add spending policies in front of an agent's wallet-based LLM routing.

## Why combine them

ClawRouter answers *how* an agent pays for an LLM call — wallet signature for auth, USDC micropayments via x402, no API keys, no accounts. Elegant infrastructure.

It does not answer *should this agent pay this amount, in this category, right now*. With a funded wallet and a runaway loop, an agent can drain its balance across hundreds of routed calls in seconds.

LetAgentPay sits *in front* of the ClawRouter call: each routed LLM request goes through 8 deterministic policy checks first. The agent only sees a successful ClawRouter call if the policy says yes.

## Installation

```bash
npm install letagentpay
```

## Quick Start

The pattern is a thin wrapper around your existing ClawRouter usage: request approval → call ClawRouter → confirm actual cost.

```typescript
import { LetAgentPay } from "letagentpay";
import { ClawRouter } from "@blockrun/clawrouter";

const policy = new LetAgentPay({ token: process.env.LETAGENTPAY_TOKEN! });
const router = new ClawRouter(/* your ClawRouter config */);

async function policedChat(opts: {
  messages: { role: string; content: string }[];
  estimatedCostUsd: number;
  description?: string;
}) {
  // 1. Ask the policy engine BEFORE the spend
  const purchase = await policy.requestPurchase({
    amount: opts.estimatedCostUsd,
    category: "llm_inference",
    merchantName: "ClawRouter",
    description: opts.description ?? "Routed LLM call",
  });

  if (purchase.status === "rejected") {
    throw new Error(`Policy denied: ${purchase.policyCheck?.failedCheck}`);
  }
  if (purchase.status === "pending") {
    throw new Error(`Policy escalated to human review: ${purchase.requestId}`);
  }

  // 2. Call ClawRouter — auto_approved, proceed
  const result = await router.chat({ messages: opts.messages });

  // 3. Report actual cost back to LetAgentPay
  await policy.confirmPurchase(purchase.requestId, {
    success: true,
    actualAmount: result.costUsd, // exact USDC settled via x402
  });

  return result;
}
```

## What policies catch

A typical ClawRouter user wants to bound four things:

| Concern | LetAgentPay control |
| --- | --- |
| One runaway call draining the wallet | `per_request_limit` |
| A loop running all night | `daily_limit` + `schedule` |
| Agent spending outside intended scope | `allowed_categories` |
| Total wallet protection | `weekly_limit` / `monthly_limit` / account budget |

A small starter policy:

```json
{
  "version": "1.0",
  "daily_limit": 20.00,
  "per_request_limit": 1.00,
  "allowed_categories": ["llm_inference"],
  "schedule": {
    "timezone": "UTC",
    "default": { "allow": "00:00-23:59" }
  }
}
```

## Notes

- **Estimate vs actual.** ClawRouter picks the model after the call lands. Estimate conservatively (worst-case token count × highest-tier model), then `confirmPurchase` reports the real x402-settled amount. The held amount releases on confirm.
- **Failed routes.** If ClawRouter rejects the request (e.g., no model available for the prompt), call `confirmPurchase` with `success: false` to release the hold.
- **Categories.** `llm_inference` is a suggestion — categories are per-account in LetAgentPay and you can define any names that fit your domain.

## See also

- [ClawRouter README](https://github.com/BlockRunAI/ClawRouter) — wallet-based LLM router
- [ASPS spec §12.4](../agent_spending_policy_spec.md#124-x402-settlement-policy) — x402 settlement policy fields for chain/domain allowlists
- [Other integrations](./) — Vercel AI SDK, LangChain, CrewAI, OpenAI Agents, Google ADK, Stripe
