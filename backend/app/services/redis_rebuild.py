"""Rebuild Redis spending/hold counters from PostgreSQL.

Used when Redis data is lost (restart without persistence, OOM, migration).
All counters are recomputed from purchase_requests table — the DB is the
source of truth.
"""

import logging
from collections import defaultdict
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import async_session
from app.models import Account, Agent, BudgetRule, PurchaseRequest
from app.redis import get_redis
from app.services.spending import DAILY_TTL, MONTHLY_TTL, WEEKLY_TTL, _to_subunits

logger = logging.getLogger(__name__)

# Statuses that contribute to "spent" counters
_SPENT_STATUSES = ("approved", "auto_approved", "completed")
# Statuses that contribute to "hold" counters
_HOLD_STATUSES = ("pending",)


def _time_keys(dt: datetime, tz: ZoneInfo) -> tuple[str, str, str]:
    """Return (daily_suffix, weekly_suffix, monthly_suffix) for a given datetime."""
    local = dt.astimezone(tz)
    return (
        local.strftime("%Y-%m-%d"),
        local.strftime("%G-W%V"),
        local.strftime("%Y-%m"),
    )


def _now_keys(tz: ZoneInfo) -> tuple[str, str, str]:
    """Current time keys — used to filter which requests fall into current buckets."""
    return _time_keys(datetime.now(tz), tz)


async def rebuild_all_counters() -> dict:
    """Recompute all Redis spending/hold counters from the database.

    Returns a summary dict with counts of rebuilt keys.
    """
    redis = get_redis()
    async with async_session() as db:
        return await _rebuild(db, redis)


async def _rebuild(db: AsyncSession, redis) -> dict:
    # Load all agents with their accounts
    result = await db.execute(select(Agent).options(joinedload(Agent.account)))
    agents = result.unique().scalars().all()

    if not agents:
        logger.info("No agents found, nothing to rebuild")
        return {"agents": 0, "keys_set": 0}

    # Load active temporal budget rules (limit_type=total with date range)
    rules_result = await db.execute(
        select(BudgetRule).where(
            BudgetRule.is_active.is_(True),
            BudgetRule.limit_type == "total",
            BudgetRule.start_at.isnot(None),
            BudgetRule.end_at.isnot(None),
        )
    )
    temporal_rules = rules_result.scalars().all()
    # Group rules by account_id
    rules_by_account: dict[str, list[BudgetRule]] = defaultdict(list)
    for rule in temporal_rules:
        rules_by_account[rule.account_id].append(rule)

    # Accumulators: key -> amount_in_subunits
    counters: dict[str, int] = defaultdict(int)
    keys_ttl: dict[str, int] = {}

    for agent in agents:
        account: Account = agent.account
        tz = ZoneInfo(account.timezone)
        now_daily, now_weekly, now_monthly = _now_keys(tz)
        currency = account.currency

        # Fetch all requests for this agent that are either spent or pending
        reqs_result = await db.execute(
            select(PurchaseRequest).where(
                PurchaseRequest.agent_id == agent.id,
                PurchaseRequest.status.in_(
                    list(_SPENT_STATUSES) + list(_HOLD_STATUSES)
                ),
            )
        )
        requests = reqs_result.scalars().all()

        for req in requests:
            req_currency = req.currency or currency
            amount_subunits = _to_subunits(req.amount)

            # Determine the time of the request in account timezone
            req_daily, req_weekly, req_monthly = _time_keys(req.created_at, tz)

            if req.status in _SPENT_STATUSES:
                prefix = "spent"
                acct_prefix = "acct_spent"
            else:
                prefix = "hold"
                acct_prefix = "acct_hold"

            # Agent-level: only if request falls into current time bucket
            if req_daily == now_daily:
                key = f"{prefix}:{agent.id}:{req_currency}:daily:{req_daily}"
                counters[key] += amount_subunits
                keys_ttl[key] = DAILY_TTL

            if req_weekly == now_weekly:
                key = f"{prefix}:{agent.id}:{req_currency}:weekly:{req_weekly}"
                counters[key] += amount_subunits
                keys_ttl[key] = WEEKLY_TTL

            if req_monthly == now_monthly:
                key = f"{prefix}:{agent.id}:{req_currency}:monthly:{req_monthly}"
                counters[key] += amount_subunits
                keys_ttl[key] = MONTHLY_TTL

            # Account-level
            if req_daily == now_daily:
                key = f"{acct_prefix}:{account.id}:{req_currency}:daily:{req_daily}"
                counters[key] += amount_subunits
                keys_ttl[key] = DAILY_TTL

            if req_weekly == now_weekly:
                key = f"{acct_prefix}:{account.id}:{req_currency}:weekly:{req_weekly}"
                counters[key] += amount_subunits
                keys_ttl[key] = WEEKLY_TTL

            if req_monthly == now_monthly:
                key = f"{acct_prefix}:{account.id}:{req_currency}:monthly:{req_monthly}"
                counters[key] += amount_subunits
                keys_ttl[key] = MONTHLY_TTL

            # Per-rule counters (temporal total rules)
            if req.status in _SPENT_STATUSES:
                for rule in rules_by_account.get(account.id, []):
                    if (
                        rule.start_at
                        and rule.end_at
                        and rule.start_at <= req.created_at <= rule.end_at
                    ):
                        key = f"acct_spent:{account.id}:{req_currency}:rule:{rule.id}"
                        counters[key] += amount_subunits
                        remaining = (rule.end_at - datetime.now(UTC)).total_seconds()
                        if remaining > 0:
                            keys_ttl[key] = int(remaining) + 86400  # +1d buffer
            elif req.status in _HOLD_STATUSES:
                for rule in rules_by_account.get(account.id, []):
                    if (
                        rule.start_at
                        and rule.end_at
                        and rule.start_at <= req.created_at <= rule.end_at
                    ):
                        key = f"acct_hold:{account.id}:{req_currency}:rule:{rule.id}"
                        counters[key] += amount_subunits
                        remaining = (rule.end_at - datetime.now(UTC)).total_seconds()
                        if remaining > 0:
                            keys_ttl[key] = int(remaining) + 86400

    # Write all counters to Redis via pipeline
    if not counters:
        logger.info("No counters to rebuild")
        return {"agents": len(agents), "keys_set": 0}

    pipe = redis.pipeline()
    for key, value in counters.items():
        pipe.set(key, value)
        if key in keys_ttl:
            pipe.expire(key, keys_ttl[key])

    await pipe.execute()

    logger.info(
        "Redis counters rebuilt: %d keys for %d agents",
        len(counters),
        len(agents),
    )
    return {"agents": len(agents), "keys_set": len(counters)}


async def check_redis_needs_rebuild() -> bool:
    """Check if Redis has any spending keys. If not, a rebuild is needed."""
    redis = get_redis()
    # SCAN for any spent:* key — if none exist, Redis is empty
    async for _ in redis.scan_iter(match="spent:*", count=1):
        return False
    # Also check hold keys — system might only have pending requests
    async for _ in redis.scan_iter(match="hold:*", count=1):
        return False
    return True
