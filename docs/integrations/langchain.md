# LangChain Integration

Use LetAgentPay as a LangChain tool to add spending controls to any LangChain agent.

## Installation

```bash
pip install letagentpay langchain langchain-openai
```

## Quick Start

```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from letagentpay import LetAgentPay

class PurchaseRequestInput(BaseModel):
    amount: float = Field(description="Amount to spend in dollars")
    category: str = Field(description="Spending category")
    merchant_name: str = Field(description="Merchant name")
    description: str = Field(description="What the purchase is for")

class LetAgentPayTool(BaseTool):
    name: str = "request_purchase"
    description: str = (
        "Request approval to spend money. Use BEFORE making any purchase."
    )
    args_schema: type[BaseModel] = PurchaseRequestInput
    client: LetAgentPay = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = LetAgentPay()  # reads LETAGENTPAY_TOKEN from env

    def _run(self, amount, category, merchant_name, description):
        result = self.client.request_purchase(
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
```

## Using with an Agent

```python
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

purchase_tool = LetAgentPayTool()
llm = ChatOpenAI(model="gpt-4o-mini")

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a shopping assistant. ALWAYS use request_purchase before buying anything."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, [purchase_tool], prompt)
executor = AgentExecutor(agent=agent, tools=[purchase_tool])

result = executor.invoke({"input": "Buy groceries at Whole Foods for $25"})
```

## How It Works

1. The LangChain agent decides it needs to make a purchase
2. It calls the `request_purchase` tool with amount, category, merchant, and description
3. LetAgentPay checks the request against your spending policies (budget, category restrictions, daily/weekly/monthly limits, schedule)
4. The tool returns the decision: **auto_approved**, **pending**, or **rejected**
5. The agent proceeds only if approved

## Categories

Categories are per-account and fully customizable. New accounts start with just `"other"` — import the 16 default categories with one click from the dashboard, or create your own with optional aliases. Use the `list_categories` tool to get the valid list at runtime. Unknown categories are resolved to `"other"` and flagged for review in the dashboard.

## Self-Hosted

```python
purchase_tool = LetAgentPayTool(
    token="agt_...",
    base_url="https://your-instance.com/api/v1/agent-api",
)
```

## Full Example

See [`examples/langchain_tool.py`](../../../examples/langchain_tool.py) for a complete working example with error handling and multiple tasks.

## Resources

- [Python SDK Documentation](../python_sdk.md)
- [Agent API Reference](../agent_api_reference.md)
- [Budget Rules](../budget_rules.md)
