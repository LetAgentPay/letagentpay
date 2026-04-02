from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_account
from app.models import Account, Agent, PurchaseRequest
from app.redis import get_redis
from app.schemas import AccountResponse, KillSwitchRequest, UpdateAccountRequest
from app.services.spending import clear_account_spending, clear_agent_spending

router = APIRouter(prefix="/api/v1/me", tags=["account"])


@router.get("", response_model=AccountResponse)
async def get_profile(account: Account = Depends(get_current_account)):
    return _account_response(account)


def _account_response(account: Account) -> AccountResponse:
    """Build AccountResponse from Account model.

    Enterprise overlay enriches this with billing data (plan_price, billing_period).
    """
    return AccountResponse(
        id=account.id,
        email=account.email,
        name=account.name,
        currency=account.currency,
        timezone=account.timezone,
        plan=account.plan,
        is_admin=account.is_admin,
        blocked=account.blocked,
        all_agents_paused=account.all_agents_paused,
        request_expiry_minutes=account.request_expiry_minutes,
        created_at=account.created_at,
    )


@router.put("", response_model=AccountResponse)
async def update_profile(
    body: UpdateAccountRequest,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    if body.name is not None:
        account.name = body.name
    if body.currency is not None and body.currency != account.currency:
        has_pending = await db.scalar(
            select(
                exists().where(
                    PurchaseRequest.agent_id == Agent.id,
                    Agent.account_id == account.id,
                    PurchaseRequest.status == "pending",
                )
            )
        )
        if has_pending:
            raise HTTPException(
                status_code=400,
                detail="Cannot change currency while there are pending purchase requests",
            )
        # Deduct old-currency spent from budget, reset counters
        result = await db.execute(select(Agent).where(Agent.account_id == account.id))
        agent_ids = []
        for agent in result.scalars():
            agent.budget = max(agent.budget - agent.spent, Decimal("0"))
            agent.spent = Decimal("0")
            agent.held = Decimal("0")
            agent_ids.append(agent.id)

        account.account_spent = Decimal("0")
        account.account_held = Decimal("0")

        # Clear Redis counters
        redis = get_redis()
        for aid in agent_ids:
            await clear_agent_spending(redis, aid)
        await clear_account_spending(redis, account.id)

        account.currency = body.currency
    if body.timezone is not None:
        account.timezone = body.timezone
    if body.request_expiry_minutes is not None:
        account.request_expiry_minutes = body.request_expiry_minutes
    await db.commit()
    await db.refresh(account)
    return _account_response(account)


@router.post("/kill-switch")
async def toggle_kill_switch(
    body: KillSwitchRequest,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    account.all_agents_paused = body.paused
    await db.commit()
    return {"all_agents_paused": account.all_agents_paused}
