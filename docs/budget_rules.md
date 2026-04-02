# Account-Level Budget Rules

## Overview

Account-level budget rules allow you to control the aggregate spending of **all agents** within an account. Even if an individual agent passes its own policy, a request may be rejected if the account budget is exhausted.

## Rule Types

| Type | Description | Example |
|------|-------------|---------|
| `daily` | Daily limit | "No more than $200/day" |
| `weekly` | Weekly limit | "No more than $1000/week" |
| `monthly` | Monthly limit | "No more than $3000/month" |
| `total` | Total limit (or time-bound) | "$100 for the duration of a flight" |

## Conditions

- **`days_of_week`** -- array of days [0-6], 0=Monday. `null` = all days.
- **`start_at` / `end_at`** -- time window when the rule is active (for time-bound limits).
- **`priority`** -- in case of conflict (multiple rules of the same type), the rule with the highest priority applies. If priorities are equal, the strictest rule wins (min limit_amount).

## Examples

### Different limits for weekdays vs. weekends
```
"Weekdays":  daily, $200, days_of_week=[0,1,2,3,4], priority=0
"Weekends":  daily, $50,  days_of_week=[5,6],       priority=0
```

### Time-bound rule for a flight
```
"Flight MAD->JFK": total, $100, start_at=2026-03-20T10:00, end_at=2026-03-20T20:00, priority=10
```

### Monthly budget
```
"Monthly limit": monthly, $3000, priority=0
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/me/budget` | Account budget overview + active rules |
| GET | `/api/v1/me/budget/rules` | All rules (including inactive) |
| POST | `/api/v1/me/budget/rules` | Create a rule |
| PUT | `/api/v1/me/budget/rules/{id}` | Update a rule |
| DELETE | `/api/v1/me/budget/rules/{id}` | Delete a rule |

## Check Order

1. Agent-level policy (status, category, limits, budget)
2. Account-level budget rules
3. If the agent rejects the request, account rules are not checked
4. On approve/auto_approve, counters at both levels are updated

## Currency

- All amounts are in the account currency (`account.currency`)
- PurchaseRequest accepts `currency` (must match account.currency)
- Cross-currency conversion is out of scope for the MVP

## Redis Counters

```
acct_spent:{account_id}:{currency}:daily:{YYYY-MM-DD}     TTL 26h
acct_spent:{account_id}:{currency}:weekly:{YYYY-Www}       TTL 8d
acct_spent:{account_id}:{currency}:monthly:{YYYY-MM}       TTL 32d
acct_spent:{account_id}:{currency}:rule:{rule_id}          TTL = end_at - now
```

## UI

Rule management: Dashboard -> Settings -> Account Budget Rules
