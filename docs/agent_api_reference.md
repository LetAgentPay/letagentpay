# Agent API Reference

The Agent API is used by AI agents to interact with the LetAgentPay platform.

## Authentication

All requests require a Bearer token in the header:

```
Authorization: Bearer agt_xxxxxxxxxxxxx
```

The token is created when the agent is set up and is available on the connection page.

## Base URL

```
https://api.letagentpay.com/api/v1/agent-api
```

For local development: `http://localhost:8000/api/v1/agent-api`

---

## Endpoints

### POST /requests — Create a purchase request

**Body (JSON):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amount` | number | yes | Purchase amount (> 0) |
| `category` | string | yes | Category (see GET /categories) |
| `merchant_name` | string | no | Store/service name |
| `description` | string | no | Purchase description |
| `agent_comment` | string | no | Agent's comment for the human reviewer (up to 2000 characters) |

**Response (201):**

```json
{
  "request_id": "uuid",
  "status": "pending | auto_approved | rejected",
  "policy_check": {
    "passed": true,
    "checks": [
      {"rule": "category", "result": "pass", "detail": "..."},
      {"rule": "per_request_limit", "result": "pass", "detail": "..."}
    ]
  },
  "auto_approved": true,
  "budget_remaining": "9500.00",
  "expires_at": null
}
```

**Examples:**

<details>
<summary>curl</summary>

```bash
curl -X POST https://api.letagentpay.com/api/v1/agent-api/requests \
  -H "Authorization: Bearer agt_your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 25.00,
    "category": "groceries",
    "merchant_name": "SuperMart",
    "description": "Weekly groceries",
    "agent_comment": "Needed for meal prep this week"
  }'
```

</details>

<details>
<summary>Python</summary>

```python
import requests

resp = requests.post(
    "https://api.letagentpay.com/api/v1/agent-api/requests",
    headers={"Authorization": "Bearer agt_your_token_here"},
    json={
        "amount": 25.00,
        "category": "groceries",
        "merchant_name": "SuperMart",
        "description": "Weekly groceries",
        "agent_comment": "Needed for meal prep this week",
    },
)
data = resp.json()
print(f"Status: {data['status']}, ID: {data['request_id']}")
```

</details>

<details>
<summary>JavaScript</summary>

```javascript
const resp = await fetch(
  "https://api.letagentpay.com/api/v1/agent-api/requests",
  {
    method: "POST",
    headers: {
      Authorization: "Bearer agt_your_token_here",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      amount: 25.0,
      category: "groceries",
      merchant_name: "SuperMart",
      description: "Weekly groceries",
      agent_comment: "Needed for meal prep this week",
    }),
  }
);
const data = await resp.json();
```

</details>

**Notifications:** If the request goes to `pending`, the account owner is notified via all configured channels (Web Push, Email, Telegram). The owner can approve or reject directly from the notification.

---

### GET /requests/{request_id} — Check request status

**Response (200):**

```json
{
  "request_id": "uuid",
  "status": "pending | approved | auto_approved | rejected | expired | completed | failed",
  "amount": "25.00",
  "category": "groceries",
  "created_at": "2026-03-18T12:00:00",
  "reviewed_at": "2026-03-18T12:05:00"
}
```

---

### POST /requests/{request_id}/confirm — Confirm a purchase

Called by the agent after the purchase has been approved (status `approved` or `auto_approved`).

**Body (JSON):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `success` | boolean | yes | Was the purchase completed successfully? |
| `actual_amount` | number | no | Actual amount (if different from the requested amount) |
| `receipt_url` | string | no | Link to the receipt or confirmation |

**Response (200):**

```json
{
  "request_id": "uuid",
  "status": "completed",
  "actual_amount": "23.50"
}
```

If `actual_amount` differs from the requested amount, the agent's balance is adjusted automatically.

---

### GET /budget — Check budget

**Response (200):**

```json
{
  "budget": "10000.00",
  "spent": "500.00",
  "remaining": "9500.00"
}
```

---

### GET /policy — Get the current policy

**Response (200):**

```json
{
  "policy": {
    "daily_limit": 5000,
    "per_request_limit": 2000,
    "allowed_categories": ["groceries", "food_delivery"],
    "auto_approve": {
      "enabled": true,
      "max_amount": 500,
      "categories": ["groceries"]
    }
  }
}
```

---

### GET /categories — List categories

Requires Bearer token authentication. Returns categories defined for the authenticated agent's account.

Categories are **per-account**, not global. New accounts start with just the `"other"` category. Account owners can import 16 default categories with one click from the dashboard, or create custom categories with optional aliases (synonyms). If a purchase request uses an unknown category, it is resolved to `"other"` and flagged for user review.

**Response (200):**

```json
{
  "categories": [
    "groceries", "food_delivery", "subscriptions", "other"
  ]
}
```

The actual list depends on which categories the account owner has configured.

---

---

## x402 Payment Authorization

LetAgentPay acts as policy middleware for x402 crypto-micropayments. The agent asks LAP for authorization before making an on-chain payment, then reports the transaction hash for audit. LAP never touches private keys or funds.

**Base URL:** `https://api.letagentpay.com/api/v1/x402`

### POST /authorize — Request payment authorization

The agent receives HTTP 402 from a resource and asks LAP: "can I pay?"

**Body (JSON):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `payment_requirements.scheme` | string | yes | Payment scheme (`exact` or `upto`) |
| `payment_requirements.network` | string | yes | CAIP-2 network ID (e.g. `eip155:8453` for Base) |
| `payment_requirements.amount` | string | yes | Amount in smallest units |
| `payment_requirements.asset` | string | yes | Asset symbol (`USDC`, `USDT`) |
| `payment_requirements.pay_to` | string | yes | Recipient address |
| `payment_requirements.resource` | string | no | Resource URL |
| `max_amount_usd` | number | yes | Maximum amount in USD |

**Response (200):**

```json
{
  "authorized": true,
  "authorization_id": "uuid",
  "expires_at": "2026-04-13T12:01:00Z",
  "remaining_daily_budget": 49.95,
  "remaining_monthly_budget": 499.95
}
```

**Decline reasons:** `CHAIN_NOT_ALLOWED`, `DOMAIN_BLOCKED`, `DOMAIN_NOT_ALLOWED`, `AMOUNT_EXCEEDS_PER_REQUEST_LIMIT`, `DAILY_BUDGET_EXCEEDED`, `WEEKLY_BUDGET_EXCEEDED`, `MONTHLY_BUDGET_EXCEEDED`, `BUDGET_EXCEEDED`, `STABLECOIN_DEPEG`.

---

### POST /report — Report completed transaction

After paying, the agent reports the transaction hash for audit logging.

**Body (JSON):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `authorization_id` | string | yes | ID from authorize response |
| `tx_hash` | string | yes | On-chain transaction hash |
| `actual_amount_usd` | number | no | Actual USD amount |
| `resource_url` | string | no | Resource URL accessed |

---

### GET /budget — x402 budget state

Returns x402-specific budget info including wallet addresses, allowed chains, and spending counters.

---

### POST /wallets — Register a wallet

Register a wallet address for x402 payments (reference only — LAP never holds keys).

**Body (JSON):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `wallet_address` | string | yes | Wallet address |
| `chain` | string | yes | Chain name (`base`, `base-sepolia`, `ethereum`, `solana`) |
| `wallet_provider` | string | no | Provider name (`coinbase`, `crossmint`, `privy`) |

### GET /wallets — List wallets

Returns all registered wallets for the agent.

---

### x402 Flow

```
1. Agent → GET resource → HTTP 402 + payment requirements
2. Agent → POST /x402/authorize → LAP checks policy → authorized/declined
3. Agent → signs tx with own wallet → pays → gets resource
4. Agent → POST /x402/report → tx_hash for audit
```

---

## Request statuses

| Status | Description |
|--------|-------------|
| `pending` | Awaiting manual approval |
| `approved` | Approved by a human |
| `auto_approved` | Automatically approved by policy |
| `rejected` | Rejected (by policy or by a human) |
| `expired` | Timed out waiting for approval (30 minutes) |
| `completed` | Purchase completed (confirmed by the agent) |
| `failed` | Purchase failed (reported by the agent) |

## Error codes

| Code | Description |
|------|-------------|
| 400 | Invalid category or incorrect request status |
| 401 | Invalid or missing token |
| 403 | Agent is paused |
| 404 | Request not found |
| 422 | Validation error (required fields missing) |
