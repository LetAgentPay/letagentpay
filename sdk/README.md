# letagentpay

Python SDK for [LetAgentPay](https://letagentpay.com) — AI agent spending policy middleware. Set budgets, define spending policies, and control AI agent purchases.

## Installation

```bash
pip install letagentpay
```

## Quick Start

```python
from letagentpay import LetAgentPay

client = LetAgentPay(token="agt_xxx")

# Create a purchase request
result = client.request_purchase(
    amount=15.0,
    category="api_calls",
    description="OpenAI GPT-4 call",
)
print(result.status)  # "auto_approved" / "pending" / "rejected"

# Check budget
budget = client.check_budget()
print(f"Remaining: ${budget.remaining}")
```

## @guard Decorator

Automatically check the spending policy before executing a function:

```python
from letagentpay import guard

@guard(token="agt_xxx", category="api_calls", amount=0.03)
def call_openai(prompt: str) -> str:
    return openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    ).choices[0].message.content

# Runs only if the policy allows it
result = call_openai("Analyze this document")
```

## x402 Crypto-Micropayments

Authorize on-chain USDC payments via the x402 protocol. Same policy engine, same token — different payment rail.

```python
client = LetAgentPay(token="agt_xxx")

# Agent receives HTTP 402 — ask LAP for authorization
auth = client.x402.authorize(
    amount_usd=0.05,
    asset="USDC",
    network="eip155:8453",       # Base mainnet
    pay_to="0xMerchant...",
    resource_url="https://api.example.com/data",
)

if auth.authorized:
    # Sign tx with your own wallet, then report
    client.x402.report(
        authorization_id=auth.authorization_id,
        tx_hash="0xabc123...",
    )
else:
    print(f"Declined: {auth.reason}")

# Check x402 budget and wallets
budget = client.x402.budget()

# Register wallet address (LAP never holds keys)
client.x402.register_wallet("0x1234...", chain="base")
```

## Environment Variables

```bash
export LETAGENTPAY_TOKEN=agt_xxx
export LETAGENTPAY_BASE_URL=https://api.letagentpay.com/api/v1/agent-api  # optional
```

```python
# Token is taken from LETAGENTPAY_TOKEN
client = LetAgentPay()
```

## Security Model

LetAgentPay uses **server-side cooperative enforcement**. When your agent calls `request_purchase()`, the request is evaluated by the policy engine on the LetAgentPay server. The agent receives only the result (approved/denied/pending) and cannot:

- Modify its own policies (the `agt_` token grants access only to the Agent API)
- Override policy check results (they come from the server)
- Approve its own pending requests (only a human can do that via the dashboard)

This is a **cooperative model** — it protects against budget overruns, category violations, and scheduling mistakes by well-behaved agents. It does not sandbox a malicious agent that has direct access to payment APIs.

### Best Practices

- **Don't give your agent raw payment credentials** (Stripe keys, credit card numbers). LetAgentPay should be the only spending channel
- Use `pending` + manual approval for high-value purchases
- Set per-request limits as an additional barrier
- Review the audit trail in the dashboard regularly

## Documentation

- [Python SDK docs](https://letagentpay.com/developers)
- [Agent API Reference](https://letagentpay.com/developers)
- [GitHub](https://github.com/letagentpay/letagentpay-python)

## License

MIT
