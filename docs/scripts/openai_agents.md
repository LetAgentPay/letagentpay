# openai_agents.py

OpenAI Agents SDK integration example — uses LetAgentPay with function calling for budget-controlled purchases.

## Location

```
examples/openai_agents.py
```

## Requirements

```bash
pip install letagentpay openai-agents
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LETAGENTPAY_TOKEN` | Yes | Agent bearer token (`agt_...`) |
| `OPENAI_API_KEY` | Yes | OpenAI API key for the agent |

## Usage

```bash
export LETAGENTPAY_TOKEN=agt_your_token
export OPENAI_API_KEY=sk-...
python examples/openai_agents.py
```

## What It Does

1. Defines `request_purchase` and `check_budget` as `@function_tool` functions
2. Creates an OpenAI agent with these tools
3. Runs three example tasks (groceries, budget check, laptop purchase)
4. The agent checks spending policy before each purchase and reports the result

## Key Components

- `request_purchase` — function tool that calls `client.request_purchase()`
- `check_budget` — function tool that checks remaining budget
- `agent` — OpenAI Agent with instructions to always check policy first

## See Also

- [OpenAI Agents SDK Integration Guide](../integrations/openai_agents.md)
- [Python SDK Documentation](../python_sdk.md)
