# OpenAI Agents SDK Integration

Use LetAgentPay with the OpenAI Agents SDK to add spending controls to your AI agents.

## Installation

```bash
pip install letagentpay openai-agents
```

## Quick Start

```python
from agents import Agent, Runner, function_tool
from letagentpay import LetAgentPay

client = LetAgentPay()  # reads LETAGENTPAY_TOKEN from env

@function_tool
def request_purchase(
    amount: float,
    category: str,
    merchant_name: str,
    description: str,
) -> str:
    """Request approval to spend money on a purchase.

    Use this BEFORE making any purchase. Returns approval status.
    """
    result = client.request_purchase(
        amount=amount,
        category=category,
        merchant_name=merchant_name,
        description=description,
    )
    if result.status == "auto_approved":
        return f"Approved. Remaining budget: ${result.budget_remaining}"
    elif result.status == "pending":
        return "Pending human review. Do not proceed yet."
    else:
        return f"Rejected: {result.status}"

agent = Agent(
    name="Shopping Assistant",
    instructions="ALWAYS use request_purchase before making any purchase.",
    tools=[request_purchase],
)
```

## Running the Agent

```python
import asyncio

async def main():
    result = await Runner.run(agent, "Buy groceries at Whole Foods for $25")
    print(result.final_output)

asyncio.run(main())
```

## Adding Budget Checking

```python
@function_tool
def check_budget() -> str:
    """Check current budget status."""
    budget = client.check_budget()
    return (
        f"Budget: ${budget.budget}, Spent: ${budget.spent}, "
        f"Held: ${budget.held}, Remaining: ${budget.remaining}"
    )

agent = Agent(
    name="Shopping Assistant",
    instructions="ALWAYS use request_purchase before buying. Check budget when asked.",
    tools=[request_purchase, check_budget],
)
```

## How It Works

1. The agent decides it needs to make a purchase
2. It calls `request_purchase` with amount, category, merchant, and description
3. LetAgentPay checks the request against your spending policies (budget, category restrictions, daily/weekly/monthly limits, schedule)
4. The function returns the decision: **auto_approved**, **pending**, or **rejected**
5. The agent proceeds only if approved

## Categories

Valid categories: `groceries`, `restaurants`, `food_delivery`, `taxi`, `transport`, `subscriptions`, `entertainment`, `education`, `health`, `electronics`, `clothing`, `gas`, `household`, `flights`, `accommodation`, `other`.

## Full Example

See [`examples/openai_agents.py`](../../../examples/openai_agents.py) for a complete working example with error handling, budget checking, and multiple tasks.

## Resources

- [Python SDK Documentation](../python_sdk.md)
- [Agent API Reference](../agent_api_reference.md)
- [Budget Rules](../budget_rules.md)
