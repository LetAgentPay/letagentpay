"""Shared approve/reject logic for purchase requests.

Called from:
- routers/requests.py (dashboard approve/reject)
- services/action_tokens.py (email/telegram one-click approve/reject)

Caller is responsible for:
- Loading and locking the PurchaseRequest (WITH FOR UPDATE)
- Validating status == "pending" and ownership
- The request must have agent and agent.account eagerly loaded
"""

import redis.asyncio as aioredis
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, Agent, PurchaseRequest
from app.services.auto_replenish import maybe_auto_replenish
from app.services.realtime import publish_event
from app.services.spending import (
    add_account_spent,
    add_spent,
    remove_account_held,
    remove_held,
)
from app.utils import clamp_zero, utcnow


async def approve_purchase_request(
    db: AsyncSession,
    redis: aioredis.Redis,
    req: PurchaseRequest,
    account_id: str,
) -> None:
    """Convert hold to spent. Commits the transaction.

    Caller must have locked the request row via FOR UPDATE.
    """
    req_currency = req.currency or req.agent.account.currency
    tz = req.agent.account.timezone

    # DB: convert hold → spent
    req.status = "approved"
    req.reviewed_at = utcnow()
    await db.execute(
        update(Agent)
        .where(Agent.id == req.agent_id)
        .values(
            spent=Agent.spent + req.amount,
            held=clamp_zero(Agent.held - req.amount),
        )
    )
    await db.execute(
        update(Account)
        .where(Account.id == account_id)
        .values(
            account_spent=Account.account_spent + req.amount,
            account_held=clamp_zero(Account.account_held - req.amount),
        )
    )
    await maybe_auto_replenish(req.agent, db)
    await db.commit()
    await db.refresh(req.agent)

    # Redis: add spent, remove hold
    await add_spent(redis, req.agent_id, req.amount, req_currency, tz)
    await add_account_spent(redis, account_id, req.amount, req_currency, tz)
    await remove_held(redis, req.agent_id, req.amount, req_currency, tz)
    await remove_account_held(redis, account_id, req.amount, req_currency, tz)

    # Realtime events
    await publish_event(
        redis,
        req.agent_id,
        "request_updated",
        {"request_id": req.id, "status": "approved"},
    )
    await publish_event(
        redis,
        req.agent_id,
        "budget_updated",
        {"budget": str(req.agent.budget), "spent": str(req.agent.spent)},
    )


async def reject_purchase_request(
    db: AsyncSession,
    redis: aioredis.Redis,
    req: PurchaseRequest,
    account_id: str,
) -> None:
    """Release hold. Commits the transaction.

    Caller must have locked the request row via FOR UPDATE.
    """
    req_currency = req.currency or req.agent.account.currency
    tz = req.agent.account.timezone

    # DB: release hold
    req.status = "rejected"
    req.reviewed_at = utcnow()
    await db.execute(
        update(Agent)
        .where(Agent.id == req.agent_id)
        .values(held=clamp_zero(Agent.held - req.amount))
    )
    await db.execute(
        update(Account)
        .where(Account.id == account_id)
        .values(account_held=clamp_zero(Account.account_held - req.amount))
    )
    await db.commit()

    # Redis: release hold
    await remove_held(redis, req.agent_id, req.amount, req_currency, tz)
    await remove_account_held(redis, account_id, req.amount, req_currency, tz)

    # Realtime event
    await publish_event(
        redis,
        req.agent_id,
        "request_updated",
        {"request_id": req.id, "status": "rejected"},
    )
