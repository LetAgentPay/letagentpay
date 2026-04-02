# Python SDK (letagentpay)

Python SDK for integrating AI agents with LetAgentPay. Provides an API client, a `@guard` decorator for automatic policy checking, and a `make_guarded_tool` helper for framework integration.

## Installation

```bash
pip install letagentpay
```

Requirements: Python 3.10+, only dependency is `httpx`.

## Quick Start

### Client

```python
from letagentpay import LetAgentPay

client = LetAgentPay(token="agt_xxx")

# Purchase request
result = client.request_purchase(
    amount=15.0,
    category="subscriptions",
    description="OpenAI GPT-4 call",
    agent_comment="Needed for document analysis"
)

if result.status == "auto_approved":
    # Execute the purchase
    do_purchase()
    # Confirm the result
    client.confirm_purchase(
        request_id=result.request_id,
        success=True,
        actual_amount=14.50,
        receipt_url="https://example.com/receipt/123"
    )
elif result.status == "pending":
    print("Waiting for owner approval...")
elif result.status == "rejected":
    print("Rejected")
```

### Budget Check

```python
budget = client.check_budget()
print(f"Budget: {budget.budget}, spent: {budget.spent}, held: {budget.held}, remaining: {budget.remaining}")
```

### List Categories

```python
categories = client.list_categories()  # ["groceries", "subscriptions", "transport", ...]
```

### My Requests

```python
result = client.my_requests(status="pending", limit=5)
for req in result.requests:
    print(f"{req.request_id}: {req.amount} {req.currency} — {req.status}")
print(f"Total: {result.total}")
```

## @guard Decorator

Automatically requests approval before executing a function. If the request is rejected, the function is not called.

```python
from letagentpay import guard

@guard(token="agt_xxx", category="subscriptions", amount=0.03)
def call_openai_api(prompt: str) -> str:
    """OpenAI API call — cost ~$0.03 per request."""
    return openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    ).choices[0].message.content

# When called, it automatically:
# 1. Sends request_purchase to LetAgentPay
# 2. If approved — executes the function
# 3. If rejected/pending — raises LetAgentPayError
result = call_openai_api("Analyze this document")
```

### @guard Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | str | Yes* | Agent bearer token (`agt_xxx`) |
| `client` | LetAgentPay | No | Existing client instance (alternative to token) |
| `category` | str | No | Expense category (default `"other"`) |
| `amount` | float | No | Fixed amount (if not specified, taken from function arguments) |
| `description` | str | No | Purchase description |
| `agent_comment` | str | No | Agent comment |

\* Required if `client` is not provided.

## make_guarded_tool

Creates a wrapped tool for use in AI frameworks (LangChain, Claude Agent SDK, etc.). Automatically checks the policy before calling.

```python
from letagentpay import make_guarded_tool

def search_web(query: str) -> str:
    """Web search — $0.01 per request."""
    return requests.get(f"https://api.search.com?q={query}").text

guarded_search = make_guarded_tool(
    func=search_web,
    token="agt_xxx",
    category="search",
    amount=0.01,
    description="Web search"
)

# guarded_search can be passed as a tool to an AI framework
```

## Configuration

### Via Environment Variables

```bash
export LETAGENTPAY_TOKEN=agt_xxx
export LETAGENTPAY_BASE_URL=https://api.letagentpay.com/api/v1/agent-api  # optional
```

```python
from letagentpay import LetAgentPay

# Token is taken from LETAGENTPAY_TOKEN
client = LetAgentPay()
```

### Via Parameters

```python
client = LetAgentPay(
    token="agt_xxx",
    base_url="https://api.letagentpay.com/api/v1/agent-api"  # default
)
```

## API Reference

### LetAgentPay

| Method | Returns | Description |
|--------|---------|-------------|
| `request_purchase(amount, category, merchant_name?, description?, agent_comment?)` | `PurchaseResult` | Purchase request |
| `check_request(request_id)` | `RequestStatus` | Check request status |
| `confirm_purchase(request_id, success, actual_amount?, receipt_url?)` | `ConfirmResult` | Confirm purchase result |
| `check_budget()` | `BudgetInfo` | Check budget |
| `get_policy()` | `dict` | Get current policy |
| `list_categories()` | `list[str]` | List available categories |
| `my_requests(status?, limit?, offset?)` | `RequestList` | List agent requests |

### Response Types

**PurchaseResult:**
| Field | Type | Description |
|-------|------|-------------|
| `request_id` | str | Request ID |
| `status` | str | `auto_approved`, `pending`, `rejected` |
| `category` | str? | Category (normalized) |
| `policy_check` | PolicyResult? | Policy check results |
| `auto_approved` | bool | Whether auto-approved |
| `budget_remaining` | float? | Remaining budget |
| `expires_at` | str? | Expiration time (ISO 8601) |

**BudgetInfo:**
| Field | Type | Description |
|-------|------|-------------|
| `budget` | float | Total budget |
| `spent` | float | Amount spent |
| `held` | float | Amount held (pending) |
| `remaining` | float | Remaining balance |
| `currency` | str? | Currency |

**RequestList:**
| Field | Type | Description |
|-------|------|-------------|
| `requests` | list[PurchaseRequestInfo] | List of requests |
| `total` | int | Total count |
| `limit` | int | Page limit |
| `offset` | int | Offset |

## Error Handling

```python
from letagentpay import LetAgentPay, LetAgentPayError

try:
    result = client.request_purchase(amount=100, category="test")
except LetAgentPayError as e:
    print(f"API error: [{e.status}] {e.detail}")
```

## File Structure

```
sdk/
├── pyproject.toml
├── README.md
├── LICENSE
├── letagentpay/
│   ├── __init__.py       # Exports: LetAgentPay, guard, make_guarded_tool, models
│   ├── client.py         # HTTP client
│   ├── guard.py          # @guard decorator and make_guarded_tool
│   ├── models.py         # Dataclass response models
│   └── py.typed          # PEP 561 marker
└── tests/
    ├── test_client.py
    ├── test_guard.py
    └── test_models.py
```

## Related Documents

- [Agent API Reference](agent_api_reference.md) -- full API description
- [MCP Server](mcp_server.md) -- alternative connection method (no code required)
