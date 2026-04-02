# langchain_tool.py

LangChain integration example — uses LetAgentPay as a LangChain tool for budget-controlled purchases.

## Location

```
examples/langchain_tool.py
```

## Requirements

```bash
pip install letagentpay langchain langchain-openai
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LETAGENTPAY_TOKEN` | Yes | Agent bearer token (`agt_...`) |
| `OPENAI_API_KEY` | Yes | OpenAI API key for the LangChain agent |

## Usage

```bash
export LETAGENTPAY_TOKEN=agt_your_token
export OPENAI_API_KEY=sk-...
python examples/langchain_tool.py
```

## What It Does

1. Defines `LetAgentPayTool` — a LangChain `BaseTool` that wraps `client.request_purchase()`
2. Creates a `ChatOpenAI` agent with the tool
3. Runs three example tasks (groceries, lunch delivery, laptop purchase)
4. The agent checks spending policy before each purchase and reports the result

## Key Components

- `PurchaseRequestInput` — Pydantic schema for tool input validation
- `LetAgentPayTool` — LangChain tool that calls the LetAgentPay API
- `main()` — sets up an `AgentExecutor` and runs example tasks

## See Also

- [LangChain Integration Guide](../integrations/langchain.md)
- [Python SDK Documentation](../python_sdk.md)
