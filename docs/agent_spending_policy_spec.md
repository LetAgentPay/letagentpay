# Agent Spending Policy Specification (ASPS)

**Version:** 1.0
**Status:** Stable
**Authors:** LetAgentPay contributors
**Date:** 2026-04-09

## Abstract

ASPS v1 defines a vendor-neutral JSON format for describing spending rules for a single AI agent. It covers budgets, limits, categories, schedules, auto-approval, and account-level budget rules.

ASPS is not tied to a specific payment provider or AI framework. It works with Stripe, Visa, Google AP2, LangChain, CrewAI, OpenClaw, or any other system. LetAgentPay is the reference implementation.

For multi-agent coordination (shared budgets, phases, dependencies), see [ASPS v2: Mission Policy](/asps/v2).

## 1. Design Principles

1. **Vendor-neutral** — no dependency on a specific payment provider or AI framework
2. **Declarative** — policies describe *what* is allowed, not *how* to enforce it
3. **Composable** — agent-level and account-level policies stack independently
4. **Human-readable** — a non-engineer should be able to read a policy and understand the rules
5. **Machine-evaluable** — any conforming engine can produce the same pass/fail result for a given request
6. **Incrementally adoptable** — all fields are optional; an empty policy `{}` means "allow everything"

## 2. Terminology

| Term | Definition |
|------|-----------|
| **Principal** | The entity that owns and funds agents (a person or organization) |
| **Agent** | An AI system authorized to make spending requests |
| **Request** | A single spending intent: amount, currency, category, description |
| **Policy** | A set of rules attached to an agent that govern its spending |
| **Budget Rule** | An account-level rule that governs aggregate spending across all agents |
| **Check** | A single pass/fail evaluation of one rule against a request |
| **Decision** | The final outcome: `approved`, `rejected`, or `pending` (requires human review) |

## 3. Policy Object

A Policy is a JSON object. All fields are optional. Omitted fields impose no restriction.

```json
{
  "version": "1.0",
  "daily_limit": 500.00,
  "weekly_limit": 2000.00,
  "monthly_limit": 5000.00,
  "per_request_limit": 200.00,
  "allowed_categories": ["groceries", "food_delivery"],
  "blocked_categories": [],
  "schedule": { ... },
  "auto_approve": { ... },
  "metadata": {}
}
```

### 3.1 Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | `string` | Spec version (e.g. `"0.1"`). Optional, defaults to latest |
| `daily_limit` | `number` | Maximum spending per calendar day |
| `weekly_limit` | `number` | Maximum spending per ISO week (Mon–Sun) |
| `monthly_limit` | `number` | Maximum spending per calendar month |
| `per_request_limit` | `number` | Maximum amount for a single request |
| `allowed_categories` | `string[]` | Whitelist of categories. If set, only these categories are allowed |
| `blocked_categories` | `string[]` | Blacklist of categories. Ignored if `allowed_categories` is set |
| `schedule` | `Schedule` | Time-based access rules |
| `auto_approve` | `AutoApprove` | Conditions for automatic approval without human review |
| `metadata` | `object` | Arbitrary key-value pairs for implementation-specific extensions |

### 3.2 Amount semantics

- All amounts are in the agent's configured currency (currency is not part of the policy — it's part of the agent/account configuration)
- Amounts MUST be non-negative
- Limit checks are inclusive: a $200 request against a $200 `per_request_limit` passes

### 3.3 Category semantics

- Each request carries exactly **one category** (a single string). If a purchase spans multiple domains, the agent or application selects the primary category
- Categories are lowercase strings, underscore-separated (e.g. `food_delivery`)
- Categories are **user-defined** — the specification does not mandate a fixed set. Each application chooses categories that fit its domain
- The specification treats categories as opaque strings. A conforming engine does not validate whether a category value is "known" — it only checks membership in `allowed_categories` / `blocked_categories`

**Evaluation rules:**
- If `allowed_categories` is set, it takes precedence over `blocked_categories`. A request with a category **not** in the list is rejected
- If only `blocked_categories` is set, a request with a category **in** the list is rejected. All other categories are allowed
- If neither list is set, all categories are allowed
- A category not present in either list is implicitly allowed (unless `allowed_categories` is set, which acts as a whitelist)

**Example categories** (as used by LetAgentPay):

```
accommodation, clothing, education, electronics, entertainment,
flights, food_delivery, gas, groceries, health, household,
other, restaurants, subscriptions, taxi, transport
```

## 4. Schedule Object

Controls when the agent is allowed to spend.

```json
{
  "timezone": "America/New_York",
  "default": {
    "allow": "09:00-17:00"
  },
  "overrides": [
    { "days": ["sat", "sun"], "deny": true },
    { "days": ["fri"], "allow": "09:00-13:00", "daily_limit": 100.00 }
  ]
}
```

### 4.1 Fields

| Field | Type | Description |
|-------|------|-------------|
| `timezone` | `string` | IANA timezone (e.g. `America/New_York`). Required if schedule is set |
| `default` | `object` | Default time window. `{ "allow": "HH:MM-HH:MM" }` |
| `overrides` | `ScheduleOverride[]` | Day-specific overrides |

### 4.2 ScheduleOverride

| Field | Type | Description |
|-------|------|-------------|
| `days` | `string[]` | Day abbreviations: `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun` |
| `allow` | `string` | Time window `"HH:MM-HH:MM"`. Overrides default |
| `deny` | `boolean` | If `true`, all spending is denied on these days |
| `daily_limit` | `number` | Override daily limit for these days |

### 4.3 Time window semantics

- Format: `"HH:MM-HH:MM"` (24-hour)
- Overnight windows are supported: `"22:00-06:00"` means 22:00 to next-day 06:00
- Overrides take precedence over default
- If an override matches the current day, the default is ignored
- If `deny: true` is set, `allow` is ignored for that override

## 5. AutoApprove Object

Defines conditions under which a request that passes all checks is approved automatically (without human review).

```json
{
  "enabled": true,
  "max_amount": 50.00,
  "categories": ["groceries", "food_delivery"]
}
```

### 5.1 Fields

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `boolean` | Required. Whether auto-approval is active |
| `max_amount` | `number` | Maximum amount eligible for auto-approval |
| `categories` | `string[]` | Only these categories are eligible. If omitted, all categories qualify |

### 5.2 Evaluation

A request qualifies for auto-approval if ALL conditions are met:
1. `enabled` is `true`
2. `amount <= max_amount` (if `max_amount` is set)
3. `category` is in `categories` (if `categories` is set)

If auto-approval does not qualify, the request enters `pending` state for human review.

## 6. Budget Rules (Account-Level)

Budget Rules apply across all agents under one principal. They are evaluated **after** agent-level policy checks pass.

```json
{
  "name": "Weekday limit",
  "limit_type": "daily",
  "limit_amount": 200.00,
  "days_of_week": [0, 1, 2, 3, 4],
  "start_at": null,
  "end_at": null,
  "priority": 0,
  "is_active": true
}
```

### 6.1 Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `string` | Human-readable rule name |
| `limit_type` | `enum` | `daily`, `weekly`, `monthly`, or `total` |
| `limit_amount` | `number` | The limit |
| `days_of_week` | `int[]` or `null` | Days when rule applies (0=Monday, 6=Sunday). `null` = all days |
| `start_at` | `datetime` or `null` | Rule active from (for time-bound rules) |
| `end_at` | `datetime` or `null` | Rule active until |
| `priority` | `int` | Conflict resolution: higher wins. Equal priority → strictest (min amount) wins |
| `is_active` | `boolean` | Whether the rule is currently enforced |

### 6.2 Evaluation order

1. Filter active rules (`is_active: true`)
2. Filter by time window (`start_at` / `end_at`)
3. Filter by day of week
4. Group by `limit_type`
5. In each group, select the rule with the highest `priority` (tie-break: lowest `limit_amount`)
6. Check each selected rule against aggregate spending

## 7. Request Object

A spending request that is evaluated against the policy.

```json
{
  "amount": 42.50,
  "currency": "USD",
  "category": "groceries",
  "description": "Weekly grocery order from Instacart",
  "idempotency_key": "req_abc123"
}
```

### 7.1 Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amount` | `number` | Yes | Requested amount (must be > 0) |
| `currency` | `string` | Yes | ISO 4217 currency code |
| `category` | `string` | Yes | Spending category |
| `description` | `string` | Yes | Human-readable description of the purchase |
| `idempotency_key` | `string` | No | Client-generated key to prevent duplicate requests |

## 8. Check Result Object

Each rule evaluation produces a check result.

```json
{
  "rule": "daily_limit",
  "result": "pass",
  "detail": "150.00/500.00 spent today"
}
```

### 8.1 Fields

| Field | Type | Description |
|-------|------|-------------|
| `rule` | `string` | Rule identifier (e.g. `status`, `category`, `daily_limit`, `budget`, `account_budget:Rule Name`) |
| `result` | `enum` | `pass` or `fail` |
| `detail` | `string` | Human-readable explanation |

## 9. Evaluation Order

A conforming policy engine MUST evaluate checks in this order:

1. **Agent status** — agent must be active
2. **Category** — against allowed/blocked lists
3. **Per-request limit** — single transaction cap
4. **Schedule** — time window check
5. **Daily limit** — against daily spending (including held amounts)
6. **Weekly limit** — against weekly spending (including held amounts)
7. **Monthly limit** — against monthly spending (including held amounts)
8. **Budget** — against remaining budget (budget - spent - held)
9. **Account-level budget rules** — aggregate checks across all agents

If any check fails, the request is rejected. All checks are evaluated (not short-circuited) to provide a complete report.

## 10. Fund Holding

When a request enters `pending` state (awaiting human approval):
- The requested amount MUST be reserved (held) against the agent's budget
- Held amounts MUST be included in limit checks (daily, weekly, monthly, budget)
- On approval: hold converts to spent
- On rejection or expiry: hold is released

This prevents over-commitment when multiple requests are pending simultaneously.

## 11. Decision Flow

```
Request → Agent Policy Checks (1-8)
  ├── Any check fails → REJECTED
  └── All checks pass → Account Budget Rules (9)
        ├── Any rule fails → REJECTED
        └── All rules pass → Auto-Approve check
              ├── Qualifies → APPROVED (auto)
              └── Does not qualify → PENDING (human review)
```

## 12. Extensibility

### 12.1 metadata field

The `metadata` field in the Policy object allows implementations to add custom fields without breaking compatibility. Conforming engines MUST ignore unknown metadata keys.

### 12.2 Categories

Categories are user-defined strings. There is no fixed set mandated by the specification. Implementations define whatever categories fit their domain.

### 12.3 Custom check rules

Implementations MAY add custom check rules. Custom rules MUST be evaluated after the standard 9 checks and MUST use a namespaced rule identifier (e.g. `custom:geo_fence`).

## 13. JSON Schema

The normative JSON Schema for ASPS objects is published at:
`https://letagentpay.com/schemas/asps/v0.1/policy.json`

The schema defines all objects: `Policy` (root), `Schedule`, `ScheduleOverride`, `AutoApprove`, `Request`, `CheckResult`, and `BudgetRule`.

## Appendix A: Full Example

```json
{
  "version": "1.0",
  "daily_limit": 500.00,
  "weekly_limit": 2000.00,
  "monthly_limit": 5000.00,
  "per_request_limit": 200.00,
  "allowed_categories": [
    "groceries",
    "food_delivery",
    "subscriptions",
    "transport"
  ],
  "schedule": {
    "timezone": "America/New_York",
    "default": {
      "allow": "08:00-22:00"
    },
    "overrides": [
      {
        "days": ["sat", "sun"],
        "allow": "10:00-18:00",
        "daily_limit": 100.00
      },
      {
        "days": ["wed"],
        "deny": true
      }
    ]
  },
  "auto_approve": {
    "enabled": true,
    "max_amount": 50.00,
    "categories": ["groceries", "food_delivery"]
  }
}
```

This policy says:
- Agent can spend up to $500/day, $2000/week, $5000/month
- Single purchase up to $200
- Only groceries, food delivery, subscriptions, and transport
- Weekdays 08:00–22:00, weekends 10:00–18:00, no spending on Wednesdays
- Weekend daily limit reduced to $100
- Groceries and food delivery under $50 are auto-approved

## Appendix B: Conformance

An implementation is **ASPS-conformant** if it:
1. Accepts Policy objects as defined in Section 3
2. Evaluates all 9 standard checks in the specified order (Section 9)
3. Produces Check Result objects as defined in Section 8
4. Implements fund holding as defined in Section 10
5. Ignores unknown fields in Policy objects (forward compatibility)

An implementation MAY extend the spec with custom checks, categories, and metadata, provided it does not alter the behavior of standard checks.