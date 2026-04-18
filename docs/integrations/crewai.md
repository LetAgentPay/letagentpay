# CrewAI Integration

Use LetAgentPay with CrewAI to add spending controls to your AI crews.

## Installation

```bash
pip install letagentpay crewai crewai-tools
```

## Quick Start

```python
from crewai import Agent, Crew, Task
from crewai.tools import tool
from letagentpay import LetAgentPay

client = LetAgentPay()  # reads LETAGENTPAY_TOKEN from env

@tool("Request Purchase")
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

@tool("Check Budget")
def check_budget() -> str:
    """Check current budget status."""
    budget = client.check_budget()
    return (
        f"Budget: ${budget.budget}, Spent: ${budget.spent}, "
        f"Held: ${budget.held}, Remaining: ${budget.remaining}"
    )
```

## Creating a Budget-Aware Agent

```python
shopping_agent = Agent(
    role="Shopping Assistant",
    goal="Complete purchase tasks while staying within budget",
    backstory=(
        "You always check spending policies before making purchases. "
        "You never proceed with rejected or pending purchases."
    ),
    tools=[request_purchase, check_budget],
)

task = Task(
    description=(
        "Buy groceries at Whole Foods (~$25) and "
        "order lunch from Uber Eats (~$15). "
        "Request approval for each purchase first."
    ),
    expected_output="Summary of purchases with their approval status.",
    agent=shopping_agent,
)

crew = Crew(agents=[shopping_agent], tasks=[task])
result = crew.kickoff()
```

## How It Works

1. A CrewAI agent is assigned a task that involves spending money
2. The agent calls `Request Purchase` with amount, category, merchant, and description
3. LetAgentPay checks the request against your spending policies (budget, category restrictions, daily/weekly/monthly limits, schedule)
4. The tool returns the decision: **auto_approved**, **pending**, or **rejected**
5. The agent proceeds only if approved

## Multi-Agent Crews

Each agent in a crew can have its own LetAgentPay token with separate budgets and policies:

```python
client_researcher = LetAgentPay(token="agt_researcher_token")
client_buyer = LetAgentPay(token="agt_buyer_token")

# Researcher has a small budget for API calls
@tool("Research Purchase")
def research_purchase(amount: float, category: str, merchant_name: str, description: str) -> str:
    result = client_researcher.request_purchase(amount=amount, category=category, merchant_name=merchant_name, description=description)
    return f"{result.status}: remaining ${result.budget_remaining}"

# Buyer has a larger budget for actual purchases
@tool("Buy Item")
def buy_item(amount: float, category: str, merchant_name: str, description: str) -> str:
    result = client_buyer.request_purchase(amount=amount, category=category, merchant_name=merchant_name, description=description)
    return f"{result.status}: remaining ${result.budget_remaining}"
```

## Categories

Categories are user-defined per agent. Use the `List Categories` tool to get the valid list at runtime. Unknown categories are automatically mapped to the closest match by the server.

## Self-Hosted

```python
client = LetAgentPay(
    token="agt_...",
    base_url="https://your-instance.com/api/v1/agent-api",
)
```

## Full Example

See [`examples/crewai_agent.py`](../../../examples/crewai_agent.py) for a complete working example with error handling, a shopping crew, and budget checking.

## Resources

- [Python SDK Documentation](../python_sdk.md)
- [Agent API Reference](../agent_api_reference.md)
- [Budget Rules](../budget_rules.md)
