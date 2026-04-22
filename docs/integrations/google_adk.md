# Google ADK Integration

Use LetAgentPay with the [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) to add spending controls to your AI agents.

## Installation

```bash
pip install letagentpay google-adk
```

## Quick Start

```python
from google.adk.agents import Agent
from letagentpay import LetAgentPay

client = LetAgentPay()  # reads LETAGENTPAY_TOKEN from env

def request_purchase(
    amount: float,
    category: str,
    merchant_name: str,
    description: str,
) -> dict:
    """Request approval to spend money on a purchase.

    Use this BEFORE making any purchase. Returns approval status.
    """
    result = client.request_purchase(
        amount=amount,
        category=category,
        merchant_name=merchant_name,
        description=description,
    )
    return {
        "status": result.status,
        "request_id": result.request_id,
        "budget_remaining": result.budget_remaining,
    }

agent = Agent(
    model="gemini-2.0-flash",
    name="shopping_assistant",
    instruction="ALWAYS use request_purchase before making any purchase.",
    tools=[request_purchase],
)
```

## Running the Agent

```python
import asyncio
from google.adk.runners import InMemoryRunner
from google.genai import types

async def main():
    runner = InMemoryRunner(agent=agent, app_name="demo")
    session = await runner.session_service.create_session(
        app_name="demo", user_id="user1",
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text="Buy groceries at Whole Foods for $25")],
    )

    async for event in runner.run_async(
        user_id="user1", session_id=session.id, new_message=message,
    ):
        if event.is_final_response():
            for part in event.content.parts:
                if part.text:
                    print(part.text)

asyncio.run(main())
```

## Adding Budget Checking

```python
def check_budget() -> dict:
    """Check current budget status."""
    budget = client.check_budget()
    return {
        "budget": budget.budget,
        "spent": budget.spent,
        "held": budget.held,
        "remaining": budget.remaining,
    }

agent = Agent(
    model="gemini-2.0-flash",
    name="shopping_assistant",
    instruction="ALWAYS use request_purchase before buying. Check budget when asked.",
    tools=[request_purchase, check_budget],
)
```

## Multi-Agent Setup

Google ADK supports sub-agents natively. Give each agent its own LetAgentPay token for separate budgets:

```python
import os

researcher_client = LetAgentPay(token=os.environ["RESEARCHER_TOKEN"])
buyer_client = LetAgentPay(token=os.environ["BUYER_TOKEN"])

def research_purchase(amount: float, category: str, merchant_name: str, description: str) -> dict:
    """Request purchase approval for research expenses."""
    result = researcher_client.request_purchase(
        amount=amount, category=category,
        merchant_name=merchant_name, description=description,
    )
    return {"status": result.status, "budget_remaining": result.budget_remaining}

def buy_item(amount: float, category: str, merchant_name: str, description: str) -> dict:
    """Request purchase approval for buying items."""
    result = buyer_client.request_purchase(
        amount=amount, category=category,
        merchant_name=merchant_name, description=description,
    )
    return {"status": result.status, "budget_remaining": result.budget_remaining}

researcher = Agent(
    model="gemini-2.0-flash",
    name="researcher",
    description="Researches products and APIs. Has its own budget for API calls.",
    instruction="Use research_purchase for any API or data costs.",
    tools=[research_purchase],
)

buyer = Agent(
    model="gemini-2.0-flash",
    name="buyer",
    description="Buys products after research is done.",
    instruction="Use buy_item for purchases. Only buy after getting research results.",
    tools=[buy_item],
)

coordinator = Agent(
    model="gemini-2.0-flash",
    name="coordinator",
    description="Coordinates research and purchasing tasks.",
    instruction="Delegate research to researcher, purchases to buyer.",
    sub_agents=[researcher, buyer],
)
```

## How It Works

1. The agent decides it needs to make a purchase
2. It calls `request_purchase` with amount, category, merchant, and description
3. LetAgentPay checks the request against your spending policies (budget, category restrictions, daily/weekly/monthly limits, schedule)
4. The function returns the decision: **auto_approved**, **pending**, or **rejected**
5. The agent proceeds only if approved

## Categories

Categories are per-account and fully customizable. New accounts start with just `"other"` — import the 16 default categories with one click from the dashboard, or create your own with optional aliases. Use the `list_categories` tool to get the valid list at runtime. Unknown categories are resolved to `"other"` and flagged for review in the dashboard.

## Full Example

See [`examples/google_adk_agent.py`](../../../examples/google_adk_agent.py) for a complete working example with error handling, budget checking, and multi-agent setup.

## Resources

- [Python SDK Documentation](../python_sdk.md)
- [Agent API Reference](../agent_api_reference.md)
- [Budget Rules](../budget_rules.md)
- [Google ADK Docs](https://google.github.io/adk-docs/)
