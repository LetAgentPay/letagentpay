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

**Response (200):**

```json
{
  "categories": [
    "clothing", "education", "electronics", "entertainment",
    "food_delivery", "gas", "groceries", "health", "household",
    "other", "restaurants", "subscriptions", "taxi", "transport"
  ]
}
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
