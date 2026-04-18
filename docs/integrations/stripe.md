# Stripe Integration

Use LetAgentPay as a **policy middleware** before Stripe payments — the agent asks for permission first, then executes the payment.

## Architecture

```
Agent → LetAgentPay (policy check) → Stripe (payment execution)
```

LetAgentPay doesn't process payments. It answers one question: **should this agent be allowed to spend this money?** Stripe handles the actual payment.

## Why Governance Before Payment

Without a policy layer, an AI agent with Stripe access can:
- Exceed intended budgets by optimizing for task completion
- Purchase premium tiers when cheaper options exist
- Spend outside allowed categories
- Make purchases outside business hours

LetAgentPay adds deterministic policy checks (budget, category, schedule, limits) that run **before** any Stripe API call.

## Installation

**Python:**
```bash
pip install letagentpay stripe openai-agents
```

**TypeScript:**
```bash
npm install letagentpay stripe ai @ai-sdk/anthropic zod
```

## How It Works

### Step 1: Agent Requests Permission

```python
from letagentpay import LetAgentPay

lap = LetAgentPay()  # reads LETAGENTPAY_TOKEN from env

result = lap.request_purchase(
    amount=49.99,
    category="subscriptions",
    merchant_name="OpenAI",
    description="GPT-4 API credits",
)
```

Possible outcomes:
- **auto_approved** — proceed to Stripe payment
- **pending** — wait for human approval (agent should NOT pay)
- **rejected** — policy violation (agent should find alternative)

### Step 2: Execute Payment via Stripe (only if approved)

```python
import stripe

if result.status == "auto_approved":
    intent = stripe.PaymentIntent.create(
        amount=int(49.99 * 100),
        currency="usd",
        description="GPT-4 API credits",
        metadata={"letagentpay_request_id": result.request_id},
    )
```

### Step 3: Report Back to LetAgentPay

```python
    lap.confirm_purchase(
        result.request_id,
        success=True,
        actual_amount=49.99,
        receipt_url=f"https://dashboard.stripe.com/payments/{intent.id}",
    )
```

## Complete Agent Example (Python)

```python
from agents import Agent, Runner, function_tool
from letagentpay import LetAgentPay, LetAgentPayError
import stripe, json

lap = LetAgentPay()
stripe.api_key = "sk_test_..."

@function_tool
def request_purchase(amount: float, category: str, merchant_name: str, description: str) -> str:
    """Request approval BEFORE making any payment."""
    result = lap.request_purchase(
        amount=amount, category=category,
        merchant_name=merchant_name, description=description,
    )
    if result.status == "auto_approved":
        return json.dumps({
            "status": "auto_approved",
            "request_id": result.request_id,
            "message": "Approved. You may now call execute_payment.",
        })
    elif result.status == "pending":
        return json.dumps({"status": "pending", "message": "Awaiting human approval."})
    else:
        return json.dumps({"status": "rejected", "message": "Find a cheaper option."})

@function_tool
def execute_payment(request_id: str, amount: float, description: str) -> str:
    """Execute Stripe payment. ONLY call after request_purchase returns auto_approved."""
    # Verify approval
    status = lap.check_request(request_id)
    if status.status not in ("auto_approved", "approved"):
        return json.dumps({"error": f"Not approved: {status.status}"})
    # Pay via Stripe
    intent = stripe.PaymentIntent.create(
        amount=int(amount * 100), currency="usd", description=description,
        metadata={"letagentpay_request_id": request_id},
    )
    # Report to LetAgentPay
    lap.confirm_purchase(request_id, success=True, actual_amount=amount)
    return json.dumps({"status": "paid", "stripe_id": intent.id})

agent = Agent(
    name="Payment Agent",
    instructions=(
        "ALWAYS call request_purchase BEFORE execute_payment. "
        "Only pay if approved. If rejected, suggest alternatives."
    ),
    tools=[request_purchase, execute_payment],
)
```

## Complete Agent Example (TypeScript)

```typescript
import { generateText, tool } from "ai";
import { anthropic } from "@ai-sdk/anthropic";
import { z } from "zod";
import Stripe from "stripe";
import { LetAgentPay } from "letagentpay";

const lap = new LetAgentPay();
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

const requestPurchase = tool({
  description: "Request approval BEFORE making any payment.",
  parameters: z.object({
    amount: z.number().positive(),
    category: z.string(),
    merchantName: z.string(),
    description: z.string(),
  }),
  execute: async ({ amount, category, merchantName, description }) => {
    const result = await lap.requestPurchase({ amount, category, merchantName, description });
    return { status: result.status, requestId: result.requestId, budgetRemaining: result.budgetRemaining };
  },
});

const executePayment = tool({
  description: "Execute Stripe payment. ONLY after requestPurchase returns auto_approved.",
  parameters: z.object({
    requestId: z.string(),
    amount: z.number().positive(),
    description: z.string(),
  }),
  execute: async ({ requestId, amount, description }) => {
    const status = await lap.checkRequest(requestId);
    if (status.status !== "auto_approved" && status.status !== "approved") {
      return { error: `Not approved: ${status.status}` };
    }
    const intent = await stripe.paymentIntents.create({
      amount: Math.round(amount * 100), currency: "usd", description,
      metadata: { letagentpay_request_id: requestId },
    });
    await lap.confirmPurchase(requestId, { success: true, actualAmount: amount });
    return { status: "paid", stripePaymentId: intent.id };
  },
});

const { text } = await generateText({
  model: anthropic("claude-sonnet-4-20250514"),
  prompt: "Pay $25 for API credits",
  tools: { requestPurchase, executePayment },
  maxSteps: 5,
});
```

## Stripe Agent Toolkit Compatibility

If you already use [Stripe Agent Toolkit](https://github.com/stripe/agent-toolkit), LetAgentPay works alongside it. Add `request_purchase` as an additional tool — the agent checks policy with LetAgentPay before calling Stripe toolkit tools.

## Full Examples

- Python: [`examples/stripe_governance.py`](../../../examples/stripe_governance.py)
- TypeScript: [`examples/stripe_governance.ts`](../../../examples/stripe_governance.ts)

## Resources

- [Python SDK Documentation](../python_sdk.md)
- [TypeScript SDK Documentation](../js_sdk.md)
- [Agent API Reference](../agent_api_reference.md)
- [Budget Rules](../budget_rules.md)
- [Stripe Agent Toolkit](https://github.com/stripe/agent-toolkit)
