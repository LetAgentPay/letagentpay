# crewai_agent.py

CrewAI integration example — uses LetAgentPay with a CrewAI crew for budget-controlled purchases.

## Location

```
examples/crewai_agent.py
```

## Requirements

```bash
pip install letagentpay crewai crewai-tools
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LETAGENTPAY_TOKEN` | Yes | Agent bearer token (`agt_...`) |
| `OPENAI_API_KEY` | Yes | OpenAI API key for the CrewAI agent |

## Usage

```bash
export LETAGENTPAY_TOKEN=agt_your_token
export OPENAI_API_KEY=sk-...
python examples/crewai_agent.py
```

## What It Does

1. Defines `request_purchase` and `check_budget` as CrewAI `@tool` functions
2. Creates a `Shopping Assistant` agent with budget-aware behavior
3. Assigns a shopping task (groceries, lunch delivery, office supplies)
4. The agent requests approval for each purchase and reports results

## Key Components

- `request_purchase` — CrewAI tool wrapping `client.request_purchase()`
- `check_budget` — CrewAI tool for checking remaining budget
- `shopping_agent` — Agent with instructions to always check policy first
- `shopping_task` — Task with a multi-item shopping list

## See Also

- [CrewAI Integration Guide](../integrations/crewai.md)
- [Python SDK Documentation](../python_sdk.md)
