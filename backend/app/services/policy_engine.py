import logging
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

from app.models import Account, Agent, BudgetRule
from app.schemas import CreatePurchaseRequest, Policy, PolicyCheckResult
from app.services.spending import (
    get_account_counters_atomic,
    get_agent_counters_atomic,
    get_rule_counters_atomic,
    get_velocity_counters_atomic,
)


def _check_status(agent: Agent) -> PolicyCheckResult:
    if agent.status != "active":
        return PolicyCheckResult(
            rule="status", result="fail", detail=f"Agent is {agent.status}"
        )
    return PolicyCheckResult(rule="status", result="pass", detail="Agent is active")


def _check_category(category: str, policy: Policy) -> PolicyCheckResult:
    if policy.allowed_categories:
        if category in policy.allowed_categories:
            return PolicyCheckResult(
                rule="category", result="pass", detail=f"{category} in allowed list"
            )
        return PolicyCheckResult(
            rule="category", result="fail", detail=f"{category} not in allowed list"
        )
    if policy.blocked_categories and category in policy.blocked_categories:
        return PolicyCheckResult(
            rule="category", result="fail", detail=f"{category} is blocked"
        )
    return PolicyCheckResult(rule="category", result="pass", detail="Category allowed")


def _check_per_request_limit(amount: Decimal, policy: Policy) -> PolicyCheckResult:
    if policy.per_request_limit is None:
        return PolicyCheckResult(
            rule="per_request_limit", result="pass", detail="No per-request limit set"
        )
    if amount <= policy.per_request_limit:
        return PolicyCheckResult(
            rule="per_request_limit",
            result="pass",
            detail=f"{amount} <= {policy.per_request_limit}",
        )
    return PolicyCheckResult(
        rule="per_request_limit",
        result="fail",
        detail=f"{amount} > {policy.per_request_limit}",
    )


def _check_schedule(policy: Policy, timezone: str) -> PolicyCheckResult:
    if not policy.schedule:
        return PolicyCheckResult(
            rule="schedule", result="pass", detail="No schedule set"
        )

    try:
        tz = ZoneInfo(policy.schedule.timezone or timezone)
    except (ZoneInfoNotFoundError, KeyError):
        logger.warning(
            "Invalid timezone '%s', falling back to UTC",
            policy.schedule.timezone or timezone,
        )
        tz = ZoneInfo("UTC")
    now = datetime.now(tz)
    day_name = now.strftime("%a").lower()  # mon, tue, ...

    # Check overrides first
    if policy.schedule.overrides:
        for override in policy.schedule.overrides:
            if day_name in [d.lower() for d in override.days]:
                if override.deny:
                    return PolicyCheckResult(
                        rule="schedule",
                        result="fail",
                        detail=f"Transactions denied on {day_name}",
                    )
                if override.allow:
                    return _check_time_window(now, override.allow)

    # Default schedule
    if policy.schedule.default and "allow" in policy.schedule.default:
        return _check_time_window(now, policy.schedule.default["allow"])

    return PolicyCheckResult(
        rule="schedule", result="pass", detail="No time restriction"
    )


def _check_time_window(now: datetime, window: str) -> PolicyCheckResult:
    """Check if current time is within HH:MM-HH:MM window."""
    try:
        start_str, end_str = window.split("-")
        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))

        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        # Handle overnight windows like "22:00-06:00"
        if start_minutes <= end_minutes:
            in_window = start_minutes <= current_minutes <= end_minutes
        else:
            in_window = (
                current_minutes >= start_minutes or current_minutes <= end_minutes
            )

        if in_window:
            return PolicyCheckResult(
                rule="schedule",
                result="pass",
                detail=f"{now.strftime('%H:%M')} within {window}",
            )
        return PolicyCheckResult(
            rule="schedule",
            result="fail",
            detail=f"{now.strftime('%H:%M')} outside {window}",
        )
    except (ValueError, AttributeError):
        return PolicyCheckResult(
            rule="schedule",
            result="fail",
            detail="Invalid schedule format, denying (fail-closed)",
        )


def _check_daily_limit(
    amount: Decimal,
    daily_spent: Decimal,
    policy: Policy,
    timezone: str,
) -> PolicyCheckResult:
    limit = policy.daily_limit

    # Check schedule overrides for day-specific limits
    if policy.schedule and policy.schedule.overrides:
        try:
            tz = ZoneInfo(policy.schedule.timezone or timezone)
        except (ZoneInfoNotFoundError, KeyError):
            tz = ZoneInfo("UTC")
        day_name = datetime.now(tz).strftime("%a").lower()
        for override in policy.schedule.overrides:
            if (
                day_name in [d.lower() for d in override.days]
                and override.daily_limit is not None
            ):
                limit = override.daily_limit
                break

    if limit is None:
        return PolicyCheckResult(
            rule="daily_limit", result="pass", detail="No daily limit set"
        )
    if daily_spent + amount <= limit:
        return PolicyCheckResult(
            rule="daily_limit",
            result="pass",
            detail=f"{daily_spent + amount}/{limit} spent today",
        )
    return PolicyCheckResult(
        rule="daily_limit",
        result="fail",
        detail=f"{daily_spent + amount} would exceed daily limit {limit}",
    )


def _check_weekly_limit(
    amount: Decimal,
    weekly_spent: Decimal,
    policy: Policy,
) -> PolicyCheckResult:
    if policy.weekly_limit is None:
        return PolicyCheckResult(
            rule="weekly_limit", result="pass", detail="No weekly limit set"
        )
    if weekly_spent + amount <= policy.weekly_limit:
        return PolicyCheckResult(
            rule="weekly_limit",
            result="pass",
            detail=f"{weekly_spent + amount}/{policy.weekly_limit} spent this week",
        )
    return PolicyCheckResult(
        rule="weekly_limit",
        result="fail",
        detail=f"{weekly_spent + amount} would exceed weekly limit {policy.weekly_limit}",
    )


def _check_monthly_limit(
    amount: Decimal,
    monthly_spent: Decimal,
    policy: Policy,
) -> PolicyCheckResult:
    if policy.monthly_limit is None:
        return PolicyCheckResult(
            rule="monthly_limit", result="pass", detail="No monthly limit set"
        )
    if monthly_spent + amount <= policy.monthly_limit:
        return PolicyCheckResult(
            rule="monthly_limit",
            result="pass",
            detail=f"{monthly_spent + amount}/{policy.monthly_limit} spent this month",
        )
    return PolicyCheckResult(
        rule="monthly_limit",
        result="fail",
        detail=f"{monthly_spent + amount} would exceed monthly limit {policy.monthly_limit}",
    )


def _check_velocity(
    per_minute_count: int,
    per_hour_count: int,
    policy: Policy,
) -> PolicyCheckResult:
    """Check that the projected request count stays within velocity limits.

    Counters reflect requests already accepted in the current window, so the
    projected value is `count + 1`. Limits are inclusive: limit=N allows
    exactly N requests per window.
    """
    if policy.requests_per_minute is None and policy.requests_per_hour is None:
        return PolicyCheckResult(
            rule="velocity_limit", result="pass", detail="No velocity limit set"
        )

    failures = []
    if (
        policy.requests_per_minute is not None
        and per_minute_count + 1 > policy.requests_per_minute
    ):
        failures.append(
            f"{per_minute_count + 1} would exceed {policy.requests_per_minute}/minute"
        )
    if (
        policy.requests_per_hour is not None
        and per_hour_count + 1 > policy.requests_per_hour
    ):
        failures.append(
            f"{per_hour_count + 1} would exceed {policy.requests_per_hour}/hour"
        )

    if failures:
        return PolicyCheckResult(
            rule="velocity_limit", result="fail", detail="; ".join(failures)
        )

    parts = []
    if policy.requests_per_minute is not None:
        parts.append(f"{per_minute_count + 1}/{policy.requests_per_minute} this minute")
    if policy.requests_per_hour is not None:
        parts.append(f"{per_hour_count + 1}/{policy.requests_per_hour} this hour")
    return PolicyCheckResult(
        rule="velocity_limit", result="pass", detail=", ".join(parts)
    )


def _check_budget(amount: Decimal, remaining: Decimal) -> PolicyCheckResult:
    if remaining >= amount:
        return PolicyCheckResult(
            rule="budget",
            result="pass",
            detail=f"{remaining} remaining >= {amount}",
        )
    return PolicyCheckResult(
        rule="budget",
        result="fail",
        detail=f"Only {remaining} remaining, need {amount}",
    )


async def check_policy(
    agent: Agent,
    request: CreatePurchaseRequest,
    redis: aioredis.Redis,
    currency: str,
    timezone: str,
) -> tuple[list[PolicyCheckResult], bool]:
    """Run all policy checks. Returns (checks, all_passed)."""
    policy = Policy(**agent.policy) if agent.policy else Policy()
    checks: list[PolicyCheckResult] = []

    # 1. Status
    checks.append(_check_status(agent))

    # 2. Velocity (cheap-fail: short-circuit before hitting Redis for spend
    # counters or DB writes — the whole point is to absorb runaway loops)
    if policy.requests_per_minute is not None or policy.requests_per_hour is not None:
        per_minute, per_hour = await get_velocity_counters_atomic(redis, agent.id)
        velocity_check = _check_velocity(per_minute, per_hour, policy)
        checks.append(velocity_check)
        if velocity_check.result == "fail":
            return checks, False

    # 3. Category
    checks.append(_check_category(request.category, policy))

    # 4. Per-request limit
    checks.append(_check_per_request_limit(request.amount, policy))

    # 5. Schedule
    checks.append(_check_schedule(policy, timezone))

    # 6-8. Daily/Weekly/Monthly limits (atomic read via Lua script)
    counters = await get_agent_counters_atomic(redis, agent.id, currency, timezone)
    checks.append(
        _check_daily_limit(
            request.amount, counters.daily_spent + counters.daily_held, policy, timezone
        )
    )
    checks.append(
        _check_weekly_limit(
            request.amount, counters.weekly_spent + counters.weekly_held, policy
        )
    )
    checks.append(
        _check_monthly_limit(
            request.amount, counters.monthly_spent + counters.monthly_held, policy
        )
    )

    # 9. Budget (remaining minus held)
    remaining = agent.budget - agent.spent - agent.held
    checks.append(_check_budget(request.amount, remaining))

    all_passed = all(c.result == "pass" for c in checks)
    return checks, all_passed


async def evaluate_budget_rules(
    account: Account,
    amount: Decimal,
    rules: list[BudgetRule],
    redis: aioredis.Redis,
    currency: str,
    timezone: str,
) -> tuple[list[PolicyCheckResult], bool]:
    """Evaluate account-level budget rules. Returns (checks, all_passed)."""
    try:
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, KeyError):
        logger.warning("Invalid timezone '%s', falling back to UTC", timezone)
        tz = ZoneInfo("UTC")
    now = datetime.now(tz)

    # 1. Filter active rules
    active = [r for r in rules if r.is_active]

    # 2. Filter by time window
    applicable = []
    for rule in active:
        if rule.start_at and now < rule.start_at:
            continue
        if rule.end_at and now > rule.end_at:
            continue
        # 3. Filter by day of week (0=Monday)
        if rule.days_of_week is not None and now.weekday() not in rule.days_of_week:
            continue
        applicable.append(rule)

    if not applicable:
        return [], True

    # 4. Group by limit_type
    groups: dict[str, list[BudgetRule]] = {}
    for rule in applicable:
        groups.setdefault(rule.limit_type, []).append(rule)

    # 5. In each group pick highest priority (tie: strictest = min limit_amount)
    selected: list[BudgetRule] = []
    for _lt, group_rules in groups.items():
        max_prio = max(r.priority for r in group_rules)
        top = [r for r in group_rules if r.priority == max_prio]
        # Tie-break: strictest (min limit_amount)
        top.sort(key=lambda r: r.limit_amount)
        selected.append(top[0])

    # 6. Check each selected rule (spent + held) — atomic read via Lua script
    checks: list[PolicyCheckResult] = []
    acct = await get_account_counters_atomic(redis, account.id, currency, timezone)
    acct_daily = acct.daily_spent + acct.daily_held
    acct_weekly = acct.weekly_spent + acct.weekly_held
    acct_monthly = acct.monthly_spent + acct.monthly_held

    for rule in selected:
        if rule.limit_type == "daily":
            projected = acct_daily + amount
            if projected <= rule.limit_amount:
                checks.append(
                    PolicyCheckResult(
                        rule=f"account_budget:{rule.name}",
                        result="pass",
                        detail=f"Account daily {projected}/{rule.limit_amount}",
                    )
                )
            else:
                checks.append(
                    PolicyCheckResult(
                        rule=f"account_budget:{rule.name}",
                        result="fail",
                        detail=f"Account daily {projected} would exceed limit {rule.limit_amount}",
                    )
                )
        elif rule.limit_type == "weekly":
            projected = acct_weekly + amount
            if projected <= rule.limit_amount:
                checks.append(
                    PolicyCheckResult(
                        rule=f"account_budget:{rule.name}",
                        result="pass",
                        detail=f"Account weekly {projected}/{rule.limit_amount}",
                    )
                )
            else:
                checks.append(
                    PolicyCheckResult(
                        rule=f"account_budget:{rule.name}",
                        result="fail",
                        detail=f"Account weekly {projected} would exceed limit {rule.limit_amount}",
                    )
                )
        elif rule.limit_type == "monthly":
            projected = acct_monthly + amount
            if projected <= rule.limit_amount:
                checks.append(
                    PolicyCheckResult(
                        rule=f"account_budget:{rule.name}",
                        result="pass",
                        detail=f"Account monthly {projected}/{rule.limit_amount}",
                    )
                )
            else:
                checks.append(
                    PolicyCheckResult(
                        rule=f"account_budget:{rule.name}",
                        result="fail",
                        detail=f"Account monthly {projected} would exceed limit {rule.limit_amount}",
                    )
                )
        elif rule.limit_type == "total":
            # For temporal total rules, use per-rule Redis counter
            if rule.start_at and rule.end_at:
                rule_spent, rule_held = await get_rule_counters_atomic(
                    redis, account.id, rule.id, currency
                )
                projected = rule_spent + rule_held + amount
            else:
                projected = account.account_spent + account.account_held + amount
            if projected <= rule.limit_amount:
                checks.append(
                    PolicyCheckResult(
                        rule=f"account_budget:{rule.name}",
                        result="pass",
                        detail=f"Account total {projected}/{rule.limit_amount}",
                    )
                )
            else:
                checks.append(
                    PolicyCheckResult(
                        rule=f"account_budget:{rule.name}",
                        result="fail",
                        detail=f"Account total {projected} would exceed limit {rule.limit_amount}",
                    )
                )

    all_passed = all(c.result == "pass" for c in checks)
    return checks, all_passed


def should_auto_approve(request: CreatePurchaseRequest, policy: Policy) -> bool:
    """Check if request qualifies for auto-approval."""
    if not policy.auto_approve or not policy.auto_approve.enabled:
        return False
    if (
        policy.auto_approve.max_amount is not None
        and request.amount > policy.auto_approve.max_amount
    ):
        return False
    return not (
        policy.auto_approve.categories
        and request.category not in policy.auto_approve.categories
    )
