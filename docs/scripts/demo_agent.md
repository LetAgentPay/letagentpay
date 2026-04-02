# demo_agent.py

Demo agent for testing the LetAgentPay API. Uses the `letagentpay` Python SDK to send purchase requests.

## Prerequisites

```bash
pip install letagentpay
```

## Usage

```bash
# Burst -- 5 random requests (default)
python scripts/demo_agent.py --token agt_<your_token>

# Burst -- 10 requests
python scripts/demo_agent.py --token agt_<your_token> --count 10

# Continuous -- a request every 10-30 seconds (Ctrl+C to stop)
python scripts/demo_agent.py --token agt_<your_token> --mode continuous

# Interactive -- manual input of amount and category
python scripts/demo_agent.py --token agt_<your_token> --mode interactive

# Against production
python scripts/demo_agent.py --token agt_<your_token> --base-url https://api.letagentpay.com
```

## Modes

| Mode | Description |
|------|-------------|
| `burst` | Sends N random requests with a 1-second interval (default 5). Auto-confirms approved purchases. Shows recent requests at the end. |
| `continuous` | Continuously sends random requests every 10-30 seconds |
| `interactive` | Manual input of parameters for each request |

## Parameters

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--token` | yes | -- | Agent bearer token (`agt_...`) |
| `--base-url` | no | `http://localhost:8000` | Backend API URL |
| `--mode` | no | `burst` | Operating mode |
| `--count` | no | `5` | Number of requests in burst mode |

## What It Demonstrates

- `LetAgentPay` client initialization with token and base URL
- `request_purchase()` with typed `PurchaseResult` response
- `confirm_purchase()` for completed purchases
- `check_budget()` with `BudgetInfo` model
- `list_categories()` and `my_requests()` pagination
- Error handling via `LetAgentPayError`
