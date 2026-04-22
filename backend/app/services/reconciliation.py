"""Periodic reconciliation of Redis spending counters against PostgreSQL.

Redis counters can drift from the DB source of truth if the process crashes
between a Redis INCRBY and the subsequent DB commit (or vice versa).
This job runs periodically, compares counters, and corrects any drift.

Design: safe-side — if Redis shows MORE spending than DB (agent is over-limited),
we correct immediately. If Redis shows LESS (agent could overdraw), we also correct.
"""

import asyncio
import logging
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database import async_session
from app.models import Account, Agent, BudgetRule, PurchaseRequest
from app.redis import get_redis
from app.services.spending import (
    DAILY_TTL,
    MONTHLY_TTL,
    WEEKLY_TTL,
    _to_subunits,
)

logger = logging.getLogger(__name__)

# How often to run (seconds)
_INTERVAL = 3600  # 1 hour

# Statuses that contribute to "spent" counters
_SPENT_STATUSES = ("approved", "auto_approved", "completed")
# Statuses that contribute to "hold" counters
_HOLD_STATUSES = ("pending",)


async def reconciliation_loop() -> None:
    """Background loop: reconcile Redis counters with DB every _INTERVAL seconds."""
    # Delay first run to avoid startup contention
    await asyncio.sleep(120)
    backoff = _INTERVAL

    while True:
        try:
            corrections = await _reconcile()
            if corrections:
                logger.warning("Reconciliation corrected %d Redis keys", corrections)
            else:
                logger.debug("Reconciliation: all counters consistent")
            backoff = _INTERVAL
        except Exception:
            logger.exception("Reconciliation failed, retrying in %ds", backoff)
            backoff = min(backoff * 2, _INTERVAL * 4)
        await asyncio.sleep(backoff)


async def _reconcile() -> int:
    """Compare Redis counters with DB and fix drift. Returns number of corrections."""
    redis = get_redis()
    corrections = 0

    async with async_session() as db:
        # Load all agents with accounts
        result = await db.execute(select(Agent).options(joinedload(Agent.account)))
        agents = result.unique().scalars().all()

        if not agents:
            return 0

        # Load temporal budget rules
        rules_result = await db.execute(
            select(BudgetRule).where(
                BudgetRule.is_active.is_(True),
                BudgetRule.limit_type == "total",
                BudgetRule.start_at.isnot(None),
                BudgetRule.end_at.isnot(None),
            )
        )
        temporal_rules = rules_result.scalars().all()
        rules_by_account: dict[str, list[BudgetRule]] = defaultdict(list)
        for rule in temporal_rules:
            rules_by_account[rule.account_id].append(rule)

        # Compute expected counters from DB
        from datetime import UTC, datetime
        from zoneinfo import ZoneInfo

        expected: dict[str, int] = defaultdict(int)
        keys_ttl: dict[str, int] = {}

        for agent in agents:
            account: Account = agent.account
            tz = ZoneInfo(account.timezone)
            now = datetime.now(tz)
            now_daily = now.strftime("%Y-%m-%d")
            now_weekly = now.strftime("%G-W%V")
            now_monthly = now.strftime("%Y-%m")
            currency = account.currency

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
                local_created = req.created_at.astimezone(tz)
                req_daily = local_created.strftime("%Y-%m-%d")
                req_weekly = local_created.strftime("%G-W%V")
                req_monthly = local_created.strftime("%Y-%m")

                if req.status in _SPENT_STATUSES:
                    prefix = "spent"
                    acct_prefix = "acct_spent"
                else:
                    prefix = "hold"
                    acct_prefix = "acct_hold"

                # Agent-level
                if req_daily == now_daily:
                    key = f"{prefix}:{agent.id}:{req_currency}:daily:{req_daily}"
                    expected[key] += amount_subunits
                    keys_ttl[key] = DAILY_TTL
                if req_weekly == now_weekly:
                    key = f"{prefix}:{agent.id}:{req_currency}:weekly:{req_weekly}"
                    expected[key] += amount_subunits
                    keys_ttl[key] = WEEKLY_TTL
                if req_monthly == now_monthly:
                    key = f"{prefix}:{agent.id}:{req_currency}:monthly:{req_monthly}"
                    expected[key] += amount_subunits
                    keys_ttl[key] = MONTHLY_TTL

                # Account-level
                if req_daily == now_daily:
                    key = f"{acct_prefix}:{account.id}:{req_currency}:daily:{req_daily}"
                    expected[key] += amount_subunits
                    keys_ttl[key] = DAILY_TTL
                if req_weekly == now_weekly:
                    key = (
                        f"{acct_prefix}:{account.id}:{req_currency}:weekly:{req_weekly}"
                    )
                    expected[key] += amount_subunits
                    keys_ttl[key] = WEEKLY_TTL
                if req_monthly == now_monthly:
                    key = f"{acct_prefix}:{account.id}:{req_currency}:monthly:{req_monthly}"
                    expected[key] += amount_subunits
                    keys_ttl[key] = MONTHLY_TTL

                # Per-rule counters
                for rule in rules_by_account.get(account.id, []):
                    if (
                        rule.start_at
                        and rule.end_at
                        and rule.start_at <= req.created_at <= rule.end_at
                    ):
                        if req.status in _SPENT_STATUSES:
                            key = (
                                f"acct_spent:{account.id}:{req_currency}:rule:{rule.id}"
                            )
                        else:
                            key = (
                                f"acct_hold:{account.id}:{req_currency}:rule:{rule.id}"
                            )
                        expected[key] += amount_subunits
                        remaining = (rule.end_at - datetime.now(UTC)).total_seconds()
                        if remaining > 0:
                            keys_ttl[key] = int(remaining) + 86400

    # Compare expected vs actual Redis values and correct drift
    if not expected:
        return 0

    pipe = redis.pipeline()
    keys_to_check = list(expected.keys())

    # Read all current Redis values
    for key in keys_to_check:
        pipe.get(key)
    actual_values = await pipe.execute()

    # Find and fix discrepancies
    fix_pipe = redis.pipeline()
    for key, actual_raw in zip(keys_to_check, actual_values, strict=True):
        actual = int(actual_raw) if actual_raw else 0
        expected_val = expected[key]

        if actual != expected_val:
            fix_pipe.set(key, expected_val)
            if key in keys_ttl:
                fix_pipe.expire(key, keys_ttl[key])
            corrections += 1
            logger.info(
                "Reconciliation fix: %s actual=%d expected=%d (diff=%+d)",
                key,
                actual,
                expected_val,
                expected_val - actual,
            )

    if corrections:
        await fix_pipe.execute()

    # Check for Redis keys that shouldn't exist (DB has no matching data)
    # Scan for spending keys not in expected set
    orphan_keys = []
    for pattern in ("spent:*", "hold:*", "acct_spent:*", "acct_hold:*"):
        async for key in redis.scan_iter(match=pattern, count=200):
            if key not in expected:
                orphan_keys.append(key)

    if orphan_keys:
        await redis.delete(*orphan_keys)
        corrections += len(orphan_keys)
        logger.info("Reconciliation: removed %d orphan Redis keys", len(orphan_keys))

    return corrections
