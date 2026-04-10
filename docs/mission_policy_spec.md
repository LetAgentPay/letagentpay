# ASPS v2: Mission Policy Specification

**Version:** 2.0-draft
**Status:** Draft
**Date:** 2026-04-09
**Extends:** [ASPS v1: Agent Spending Policy](agent_spending_policy_spec.md)

## Abstract

ASPS v2 extends ASPS v1 to support coordinated spending across multiple AI agents working toward a common goal. While v1 defines rules for a single agent, v2 defines rules for a **mission** — a task with shared resources, phases, dependencies, dynamic budget allocation, and risk scoring.

ASPS v2 is a **layer above** v1, not a replacement. Every agent inside a mission still uses an ASPS v1 policy for individual spending rules.

## 1. Motivation

AI agents increasingly work in teams. A travel planning task may involve 5 agents (flights, hotels, activities, research, logistics). A marketing campaign may involve 3 agents (content, ads, analytics). An incident response may involve 4 agents (monitoring, diagnosis, remediation, postmortem).

These teams share budgets, have dependencies between tasks, progress through phases, and need coordinated spending control. No existing specification addresses this.

## 2. Core Concepts

### 2.1 Mission

A mission is a goal-oriented task with a shared resource pool and a set of participating agents.

```json
{
  "version": "2.0",
  "name": "Barcelona trip, May 15-22",
  "budget": 5000,
  "currency": "USD",
  "deadline": "2026-05-10T00:00:00Z",
  "agents": { ... },
  "phases": [ ... ],
  "constraints": [ ... ],
  "on_failure": "pause"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | `string` | No | Spec version |
| `name` | `string` | Yes | Human-readable mission name |
| `budget` | `number` | Yes | Total mission budget |
| `currency` | `string` | Yes | ISO 4217 currency code |
| `deadline` | `datetime` | No | Mission deadline (ISO 8601) |
| `agents` | `object` | Yes | Agent definitions (keyed by role) |
| `phases` | `Phase[]` | Yes | Ordered list of mission phases |
| `constraints` | `Constraint[]` | No | Cross-agent and cross-phase constraints |
| `on_failure` | `enum` | No | What happens when a phase fails: `pause`, `rollback`, `abort`. Default: `pause` |

### 2.2 Agent Role

Each agent in a mission has a role and an optional individual ASPS policy.

```json
{
  "agents": {
    "flights": {
      "description": "Searches and books flights",
      "policy": {
        "allowed_categories": ["flights", "transport"],
        "per_request_limit": 1500
      }
    },
    "hotel": {
      "description": "Searches and books accommodation",
      "policy": {
        "allowed_categories": ["accommodation"],
        "per_request_limit": 2000
      }
    },
    "entertainment": {
      "description": "Plans and books activities",
      "policy": {
        "allowed_categories": ["entertainment", "restaurants", "transport"]
      }
    },
    "research": {
      "description": "Weather, reviews, safety analysis",
      "can_spend": false
    }
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | `string` | No | What this agent does |
| `policy` | `Policy` | No | ASPS policy for this agent within the mission |
| `can_spend` | `boolean` | No | If `false`, agent participates but cannot make spending requests. Default: `true` |

The agent-level ASPS policy (if set) is applied **in addition to** phase-level and mission-level rules. All must pass.

### 2.3 Phase

A phase is a stage of the mission with its own budget allocation, active agents, and entry/exit conditions.

```json
{
  "phases": [
    {
      "name": "research",
      "agents": ["research", "flights", "hotel"],
      "allocation": { "type": "fixed", "amount": 0 },
      "exit_condition": { "type": "manual" }
    },
    {
      "name": "booking",
      "agents": ["flights", "hotel"],
      "allocation": { "type": "share", "percent": 70 },
      "exit_condition": {
        "type": "all_confirmed",
        "agents": ["flights", "hotel"]
      }
    },
    {
      "name": "activities",
      "agents": ["entertainment"],
      "allocation": { "type": "remaining" },
      "exit_condition": { "type": "manual" }
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `string` | Yes | Phase identifier |
| `agents` | `string[]` | Yes | Agent roles active in this phase |
| `allocation` | `Allocation` | Yes | How budget is allocated to this phase |
| `exit_condition` | `ExitCondition` | No | When this phase is considered complete |
| `on_failure` | `enum` | No | Override mission-level `on_failure` for this phase |
| `timeout` | `string` | No | Max duration for this phase (e.g. `"24h"`, `"7d"`) |

Phases are **ordered**. A phase starts when the previous phase's `exit_condition` is met. The first phase starts immediately.

Multiple phases MAY be active simultaneously if explicitly configured (see `parallel` in Section 5).

## 3. Budget Allocation

### 3.1 Allocation Types

| Type | Description | Example |
|------|-------------|---------|
| `fixed` | Fixed dollar amount | `{ "type": "fixed", "amount": 500 }` |
| `share` | Percentage of total mission budget | `{ "type": "share", "percent": 70 }` |
| `remaining` | Whatever is left after previous phases | `{ "type": "remaining" }` |
| `per_agent` | Fixed amount per agent in the phase | `{ "type": "per_agent", "amount": 100 }` |
| `competitive` | Initial amount per agent, winner gets the rest | `{ "type": "competitive", "seed": 100, "prize": 1000, "metric": "lowest_price" }` |

### 3.2 Dynamic Reallocation

Within a phase, unspent budget from one agent is available to others. This is the default behavior.

```json
{
  "allocation": {
    "type": "share",
    "percent": 70,
    "reallocation": "dynamic"
  }
}
```

| Reallocation | Description |
|---|---|
| `dynamic` | Unspent budget is available to other agents in the phase (default) |
| `partitioned` | Each agent gets a fixed slice, no reallocation |

With `dynamic` reallocation: if flights agent spends $800 of a $3500 phase budget, hotel agent can spend up to $2700.

With `partitioned`: flights gets $1750, hotel gets $1750, regardless of what each spends.

### 3.3 Budget Cascade

Budget flows top-down:

```
Mission budget ($5000)
  → Phase allocation (research: $0, booking: $3500, activities: remaining)
    → Agent policy (per_request_limit, categories, etc.)
      → ASPS checks (9 standard checks)
```

A request must pass ALL levels. Mission budget exhausted → reject, even if phase and agent budgets allow it.

## 4. Transitions and Exit Conditions

### 4.1 Exit Condition Types

| Type | Description | Example |
|------|-------------|---------|
| `manual` | Human explicitly advances to next phase | `{ "type": "manual" }` |
| `all_confirmed` | All specified agents have confirmed purchases | `{ "type": "all_confirmed", "agents": ["flights", "hotel"] }` |
| `any_confirmed` | At least one agent has confirmed | `{ "type": "any_confirmed", "agents": ["agent_a", "agent_b"] }` |
| `budget_depleted` | Phase budget is fully spent | `{ "type": "budget_depleted" }` |
| `timeout` | Phase duration exceeded | Configured via `timeout` field on Phase |
| `condition` | Custom expression | `{ "type": "condition", "expr": "flights.spent > 0 AND hotel.spent > 0" }` |

### 4.2 Phase Transitions

When a phase's exit condition is met:
1. Current phase is marked `completed`
2. Unspent phase budget returns to the mission pool (available for `remaining` allocations)
3. Next phase starts, its agents become active
4. Agents not in the new phase are paused (cannot make requests)

### 4.3 Failure Handling

When a phase fails (timeout, constraint violation, explicit failure signal):

| on_failure | Behavior |
|---|---|
| `pause` | Mission pauses. Human decides next step. (Default) |
| `rollback` | Engine emits rollback signals for confirmed purchases in the failed phase. Previous phase reactivates. |
| `abort` | Mission terminates. All pending requests are cancelled. Holds are released. |

Rollback is a **signal**, not an automatic refund. The engine tells agents "this purchase should be reversed." The actual reversal is the agent's responsibility.

## 5. Constraints

Constraints express relationships between agents and phases.

```json
{
  "constraints": [
    {
      "type": "dependency",
      "agent": "hotel",
      "requires": "flights",
      "condition": "confirmed"
    },
    {
      "type": "combined_limit",
      "agents": ["flights", "hotel"],
      "max_share": 0.7
    },
    {
      "type": "conditional_limit",
      "if": "hotel.last_amount > 200",
      "then": { "agent": "entertainment", "daily_limit": 50 }
    }
  ]
}
```

### 5.1 Constraint Types

| Type | Description |
|------|-------------|
| `dependency` | Agent B cannot spend until Agent A meets a condition |
| `combined_limit` | Sum of spending across listed agents cannot exceed a limit |
| `conditional_limit` | If a condition is true, apply additional limits to an agent |
| `exclusion` | If Agent A has spent, Agent B is blocked (mutually exclusive) |
| `priority_order` | Agents spend in priority order; lower-priority agents wait |

### 5.2 Dependency Constraint

```json
{
  "type": "dependency",
  "agent": "hotel",
  "requires": "flights",
  "condition": "confirmed"
}
```

| Condition | Meaning |
|---|---|
| `confirmed` | Required agent has at least one confirmed purchase |
| `approved` | Required agent has at least one approved request |
| `phase_complete` | Required agent's phase is complete |
| `spent_above` | Required agent has spent above a threshold: `"condition": "spent_above:500"` |

### 5.3 Combined Limit Constraint

```json
{
  "type": "combined_limit",
  "agents": ["flights", "hotel"],
  "max_share": 0.7
}
```

Sum of all spending by listed agents cannot exceed `max_share` (as fraction of mission budget) or `max_amount` (absolute value).

### 5.4 Conditional Limit Constraint

```json
{
  "type": "conditional_limit",
  "if": "hotel.last_amount > 200",
  "then": { "agent": "entertainment", "daily_limit": 50 }
}
```

If the condition evaluates to true, the `then` policy is merged with the agent's existing policy (stricter values win).

## 6. Escalation Model

For scenarios where agents gain more authority over time (customer service, incident response).

```json
{
  "phases": [
    {
      "name": "L1",
      "agents": ["support"],
      "allocation": { "type": "fixed", "amount": 50 },
      "exit_condition": { "type": "manual" }
    },
    {
      "name": "L2",
      "agents": ["support"],
      "allocation": { "type": "fixed", "amount": 500 },
      "exit_condition": { "type": "manual" }
    },
    {
      "name": "L3",
      "agents": ["support"],
      "allocation": { "type": "fixed", "amount": 5000 },
      "exit_condition": { "type": "manual" }
    }
  ]
}
```

In escalation, the same agent participates in multiple phases with increasing budgets. Each phase is a new level of authority. Transition is typically `manual` (a human or system escalates).

Note: in escalation, phase budgets are **not cumulative** — each level has its own allocation. Unspent L1 budget does not carry to L2.

## 7. Competitive Allocation

For scenarios where agents compete and the winner gets the budget.

```json
{
  "phases": [
    {
      "name": "search",
      "agents": ["supplier_a", "supplier_b", "supplier_c"],
      "allocation": {
        "type": "competitive",
        "seed": 50,
        "prize": 2000,
        "metric": "lowest_price"
      },
      "timeout": "24h"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `seed` | `number` | Initial budget per agent for research/exploration |
| `prize` | `number` | Budget awarded to the winning agent |
| `metric` | `string` | How to pick the winner: `lowest_price`, `highest_quality`, `manual` |

When the phase ends (timeout or manual trigger), the engine evaluates results by `metric` and awards `prize` to the winning agent. Losing agents are paused.

## 8. Mission Lifecycle

```
CREATED → ACTIVE → COMPLETED
              ↓
           PAUSED → ACTIVE (resume)
              ↓
           ABORTED
```

### 8.1 States

| State | Description |
|---|---|
| `created` | Mission defined but not started |
| `active` | At least one phase is active, agents can make requests |
| `paused` | Mission paused (failure, manual intervention). No requests accepted |
| `completed` | All phases completed successfully |
| `aborted` | Mission terminated. All holds released |

### 8.2 Request Evaluation Within a Mission

When an agent submits a spending request:

1. **Mission state** — mission must be `active`
2. **Phase check** — agent must be in the currently active phase
3. **Agent role** — agent must have `can_spend: true`
4. **Phase budget** — request must fit within phase allocation (considering dynamic reallocation)
5. **Mission budget** — request must fit within total mission budget
6. **Constraints** — all applicable constraints must pass (dependencies, combined limits, conditional limits)
7. **Agent ASPS policy** — standard 9 ASPS checks against agent's individual policy
8. **Risk check** — if risk policy is configured (see ASPS risk scoring)

All checks must pass. Failure at any level → reject with detailed report.

## 9. Risk Scoring

ASPS v2 adds an optional risk scoring check that detects anomalous spending patterns. Unlike deterministic checks (limits, categories), risk scoring evaluates whether a request is **unusual** for this agent, even if it formally passes all rules.

### 9.1 RiskPolicy Object

Added to the agent's ASPS v1 policy or to the mission-level configuration.

```json
{
  "risk": {
    "risk_threshold": 0.7,
    "on_high_risk": "pending",
    "baseline_window": "30d"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `risk_threshold` | `number` | Yes | Score threshold (0.0–1.0). Requests scoring above this are flagged |
| `on_high_risk` | `enum` | No | Action when threshold exceeded: `pending` or `reject`. Default: `pending` |
| `baseline_window` | `string` | No | Period for building baseline behavior (e.g. `"30d"`, `"7d"`). Default: `"30d"` |

### 9.2 Risk Check

Evaluated as the last check (after ASPS v1 checks and mission-level checks). The specification defines the **interface**, not the algorithm — implementations choose how to compute the score.

**Recommended risk factors** (implementations SHOULD consider):

| Factor ID | Description |
|---|---|
| `unusual_amount` | Amount significantly deviates from agent's typical spending in this category |
| `unusual_category` | Agent has not previously used this category |
| `unusual_time` | Request at an atypical time for this agent |
| `unusual_frequency` | Atypical request frequency (e.g. 3 requests/minute vs usual 2/hour) |
| `description_mismatch` | Description does not semantically match the category |

Implementations MAY add custom factors.

### 9.3 Risk Check Result

```json
{
  "rule": "risk",
  "result": "fail",
  "detail": "Risk score 0.82 exceeds threshold 0.7",
  "risk_score": 0.82,
  "risk_factors": ["unusual_amount", "unusual_time"]
}
```

The `risk_score` and `risk_factors` fields extend the standard Check Result object (ASPS v1 Section 8).

### 9.4 Implementation Approaches

The specification does not mandate an algorithm. Possible approaches (from simple to complex):

1. **Statistical (z-score)** — deviation from mean per factor
2. **Rule-based** — weighted heuristics
3. **ML model** — trained on agent's transaction history

## 10. Relationship to ASPS v1

ASPS v2 is a **layer above** v1, not a replacement.

```
ASPS v2 (missions, coordination, risk scoring)
  └── ASPS v1 (per-agent spending rules)
        └── 9 standard checks
```

- An agent inside a mission still has an ASPS v1 policy
- ASPS v1 checks are evaluated as part of step 7 (see Section 8.2)
- An agent can operate independently (with just ASPS v1) or as part of a mission
- Account-level Budget Rules (ASPS v1 Section 6) apply across all missions
- Risk scoring (Section 9) can be used with or without missions

## 11. Extensibility

### 11.1 Custom exit conditions

Implementations MAY define custom exit condition types. Custom types SHOULD use a namespace prefix (e.g. `custom:ml_confidence`).

### 11.2 Custom constraint types

Implementations MAY define custom constraint types beyond the standard set.

### 11.3 Custom metrics

For competitive allocation, implementations MAY define custom metrics beyond `lowest_price`, `highest_quality`, `manual`.

### 11.4 Metadata

Both Mission and Phase objects support a `metadata` field for implementation-specific extensions.

## Appendix A: Full Example — Travel Planning

```json
{
  "version": "2.0",
  "name": "Barcelona trip, May 15-22, 2 people",
  "budget": 5000,
  "currency": "USD",
  "deadline": "2026-05-10T00:00:00Z",

  "agents": {
    "research": {
      "description": "Weather, reviews, safety, geopolitics",
      "can_spend": false
    },
    "flights": {
      "description": "Search and book flights",
      "policy": {
        "allowed_categories": ["flights", "transport"],
        "per_request_limit": 1500
      }
    },
    "hotel": {
      "description": "Search and book accommodation",
      "policy": {
        "allowed_categories": ["accommodation"],
        "per_request_limit": 2000
      }
    },
    "entertainment": {
      "description": "Plan and book activities, restaurants",
      "policy": {
        "allowed_categories": ["entertainment", "restaurants", "transport"],
        "per_request_limit": 200
      }
    }
  },

  "phases": [
    {
      "name": "research",
      "agents": ["research", "flights", "hotel"],
      "allocation": { "type": "fixed", "amount": 0 },
      "exit_condition": { "type": "manual" }
    },
    {
      "name": "booking",
      "agents": ["flights", "hotel"],
      "allocation": { "type": "share", "percent": 70, "reallocation": "dynamic" },
      "exit_condition": {
        "type": "all_confirmed",
        "agents": ["flights", "hotel"]
      }
    },
    {
      "name": "activities",
      "agents": ["entertainment"],
      "allocation": { "type": "remaining" },
      "exit_condition": { "type": "manual" }
    }
  ],

  "constraints": [
    {
      "type": "dependency",
      "agent": "hotel",
      "requires": "flights",
      "condition": "approved"
    },
    {
      "type": "combined_limit",
      "agents": ["flights", "hotel"],
      "max_share": 0.75
    }
  ],

  "on_failure": "pause"
}
```

This mission:
- Total budget $5,000 for the trip
- Research phase: agents explore options, no spending
- Booking phase: 70% of budget ($3,500), dynamic reallocation between flights and hotel
- Hotel cannot book until flights are at least approved
- Flights + hotel combined cannot exceed 75% of total ($3,750)
- Activities phase: gets whatever remains after booking
- If anything fails, mission pauses for human decision

## Appendix B: Full Example — Incident Response (Escalation)

```json
{
  "version": "2.0",
  "name": "Production outage #4521",
  "budget": 10000,
  "currency": "USD",

  "agents": {
    "monitor": {
      "description": "Detects and reports issues",
      "can_spend": false
    },
    "diagnose": {
      "description": "Investigates root cause",
      "policy": {
        "allowed_categories": ["compute", "diagnostics"]
      }
    },
    "remediate": {
      "description": "Fixes the issue",
      "policy": {
        "allowed_categories": ["compute", "networking", "storage"]
      }
    }
  },

  "phases": [
    {
      "name": "detection",
      "agents": ["monitor"],
      "allocation": { "type": "fixed", "amount": 0 },
      "exit_condition": { "type": "manual" }
    },
    {
      "name": "diagnosis",
      "agents": ["diagnose"],
      "allocation": { "type": "fixed", "amount": 500 },
      "timeout": "2h",
      "exit_condition": { "type": "manual" }
    },
    {
      "name": "remediation",
      "agents": ["remediate"],
      "allocation": { "type": "fixed", "amount": 5000 },
      "timeout": "4h",
      "exit_condition": { "type": "manual" }
    },
    {
      "name": "escalation",
      "agents": ["remediate"],
      "allocation": { "type": "remaining" },
      "exit_condition": { "type": "manual" }
    }
  ],

  "on_failure": "pause"
}
```

## Appendix C: Full Example — Competitive Search

```json
{
  "version": "2.0",
  "name": "Find best laptop deal",
  "budget": 2500,
  "currency": "USD",

  "agents": {
    "amazon": { "description": "Searches Amazon" },
    "ebay": { "description": "Searches eBay" },
    "bestbuy": { "description": "Searches Best Buy" }
  },

  "phases": [
    {
      "name": "search",
      "agents": ["amazon", "ebay", "bestbuy"],
      "allocation": {
        "type": "competitive",
        "seed": 0,
        "prize": 2500,
        "metric": "lowest_price"
      },
      "timeout": "12h",
      "exit_condition": { "type": "timeout" }
    }
  ]
}
```
