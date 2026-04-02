import asyncio
import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import delete, select, update
from sqlalchemy.orm import joinedload

from app.database import async_session
from app.models import (
    Account,
    Agent,
    NotificationLog,
    PurchaseRequest,
    VerificationToken,
)
from app.redis import get_redis
from app.services.realtime import publish_event
from app.services.spending import remove_account_held, remove_held
from app.utils import clamp_zero, utcnow

logger = logging.getLogger(__name__)

EXPIRY_CHECK_INTERVAL = 60  # seconds
MAX_BACKOFF = 300  # 5 minutes
NOTIFICATION_LOG_RETENTION_DAYS = 30
_log_cleanup_counter = 0


async def expire_pending_requests_loop() -> None:
    """Background task that marks expired pending requests."""
    global _log_cleanup_counter
    backoff = EXPIRY_CHECK_INTERVAL
    while True:
        try:
            await _expire_batch()
            await _cleanup_expired_tokens()
            # Run notification log cleanup once per day (~1440 iterations at 60s)
            _log_cleanup_counter += 1
            if _log_cleanup_counter >= 1440:
                _log_cleanup_counter = 0
                await _cleanup_notification_log()
            backoff = EXPIRY_CHECK_INTERVAL  # reset on success
        except Exception:
            logger.exception("Error in expiry task")
            backoff = min(backoff * 2, MAX_BACKOFF)
        await asyncio.sleep(backoff)


async def _expire_batch() -> int:
    """Expire all pending requests past their expires_at and release holds."""
    async with async_session() as db:
        now = utcnow()
        # SKIP LOCKED: if a request is being approved/rejected concurrently,
        # skip it — the other transaction will handle its status change.
        # Two-step: lock rows first (no JOINs — PG forbids FOR UPDATE with
        # LEFT OUTER JOIN), then eagerly load relationships.
        lock_result = await db.execute(
            select(PurchaseRequest.id)
            .where(
                PurchaseRequest.status == "pending",
                PurchaseRequest.expires_at < now,
            )
            .with_for_update(skip_locked=True)
        )
        locked_ids = [row[0] for row in lock_result.all()]
        if not locked_ids:
            return 0

        result = await db.execute(
            select(PurchaseRequest)
            .options(joinedload(PurchaseRequest.agent).joinedload(Agent.account))
            .where(PurchaseRequest.id.in_(locked_ids))
        )
        expired = result.unique().scalars().all()
        if not expired:
            return 0

        # Group hold amounts by agent and account (DB holds are currency-agnostic)
        agent_holds_db: dict[str, Decimal] = defaultdict(Decimal)
        account_holds_db: dict[str, Decimal] = defaultdict(Decimal)
        # Redis holds are per-currency: (id, currency) -> amount
        agent_holds_redis: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
        account_holds_redis: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
        agent_tz: dict[str, str] = {}
        account_tz: dict[str, str] = {}

        for req in expired:
            req.status = "expired"
            req_currency = req.currency or req.agent.account.currency
            agent_holds_db[req.agent_id] += req.amount
            account_holds_db[req.agent.account_id] += req.amount
            agent_holds_redis[(req.agent_id, req_currency)] += req.amount
            account_holds_redis[(req.agent.account_id, req_currency)] += req.amount
            agent_tz[req.agent_id] = req.agent.account.timezone
            account_tz[req.agent.account_id] = req.agent.account.timezone

        # Release holds in DB
        for agent_id, total in agent_holds_db.items():
            await db.execute(
                update(Agent)
                .where(Agent.id == agent_id)
                .values(held=clamp_zero(Agent.held - total))
            )
        for acct_id, total in account_holds_db.items():
            await db.execute(
                update(Account)
                .where(Account.id == acct_id)
                .values(account_held=clamp_zero(Account.account_held - total))
            )

        await db.commit()

        # Release Redis holds + publish events
        redis = get_redis()
        for (agent_id, currency), total in agent_holds_redis.items():
            await remove_held(redis, agent_id, total, currency, agent_tz[agent_id])
        for (acct_id, currency), total in account_holds_redis.items():
            await remove_account_held(
                redis, acct_id, total, currency, account_tz[acct_id]
            )

        for req in expired:
            await publish_event(
                redis,
                req.agent_id,
                "request_updated",
                {"request_id": req.id, "status": "expired"},
            )

        count = len(expired)
        logger.info("Expired %d pending requests, released holds", count)
        return count


async def _cleanup_expired_tokens() -> int:
    """Remove expired verification tokens. Returns count."""
    async with async_session() as db:
        now = utcnow()
        result = await db.execute(
            delete(VerificationToken).where(VerificationToken.expires_at < now)
        )
        count = result.rowcount  # type: ignore[attr-defined]
        if count:
            await db.commit()
            logger.info("Cleaned up %d expired verification tokens", count)
        return count


async def _cleanup_notification_log() -> int:
    """Remove notification log entries older than retention period. Returns count."""
    async with async_session() as db:
        cutoff = utcnow() - timedelta(days=NOTIFICATION_LOG_RETENTION_DAYS)
        result = await db.execute(
            delete(NotificationLog).where(NotificationLog.created_at < cutoff)
        )
        count = result.rowcount  # type: ignore[attr-defined]
        if count:
            await db.commit()
            logger.info("Cleaned up %d old notification log entries", count)
        return count
