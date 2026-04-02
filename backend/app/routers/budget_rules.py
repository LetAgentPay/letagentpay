from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_account
from app.models import Account, BudgetRule
from app.redis import get_redis
from app.schemas import (
    AccountBudgetResponse,
    BudgetRuleCreate,
    BudgetRuleResponse,
    BudgetRuleUpdate,
)
from app.services.spending import (
    get_account_daily_spent,
    get_account_monthly_spent,
    get_account_weekly_spent,
    get_rule_spent,
)

router = APIRouter(prefix="/api/v1/me/budget", tags=["budget-rules"])


async def _rule_response(
    rule: BudgetRule,
    account_id: str,
    currency: str,
) -> BudgetRuleResponse:
    """Build response for a single rule, including spent for temporal total rules."""
    spent = None
    if rule.limit_type == "total" and rule.start_at and rule.end_at:
        redis = get_redis()
        spent = await get_rule_spent(redis, account_id, rule.id, currency)
    return BudgetRuleResponse(
        id=rule.id,
        name=rule.name,
        is_active=rule.is_active,
        priority=rule.priority,
        limit_type=rule.limit_type,
        limit_amount=rule.limit_amount,
        days_of_week=rule.days_of_week,
        start_at=rule.start_at,
        end_at=rule.end_at,
        created_at=rule.created_at,
        spent=spent,
    )


@router.get("", response_model=AccountBudgetResponse)
async def get_account_budget(
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    redis = get_redis()
    tz = account.timezone

    currency = account.currency
    daily = await get_account_daily_spent(redis, account.id, currency, tz)
    weekly = await get_account_weekly_spent(redis, account.id, currency, tz)
    monthly = await get_account_monthly_spent(redis, account.id, currency, tz)

    result = await db.execute(
        select(BudgetRule)
        .where(BudgetRule.account_id == account.id, BudgetRule.is_active.is_(True))
        .order_by(BudgetRule.priority.desc(), BudgetRule.created_at)
    )
    rules = result.scalars().all()

    rule_responses = [await _rule_response(r, account.id, currency) for r in rules]

    return AccountBudgetResponse(
        account_spent=account.account_spent,
        currency=account.currency,
        daily_spent=daily,
        weekly_spent=weekly,
        monthly_spent=monthly,
        rules=rule_responses,
    )


@router.get("/rules", response_model=list[BudgetRuleResponse])
async def list_budget_rules(
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BudgetRule)
        .where(BudgetRule.account_id == account.id)
        .order_by(BudgetRule.priority.desc(), BudgetRule.created_at)
    )
    rules = result.scalars().all()
    return [await _rule_response(r, account.id, account.currency) for r in rules]


@router.post("/rules", response_model=BudgetRuleResponse, status_code=201)
async def create_budget_rule(
    body: BudgetRuleCreate,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    # Validate days_of_week
    if body.days_of_week is not None and not all(
        0 <= d <= 6 for d in body.days_of_week
    ):
        raise HTTPException(
            status_code=400,
            detail="days_of_week values must be 0-6 (Mon-Sun)",
        )

    # Validate start_at/end_at
    if body.start_at and body.end_at and body.start_at >= body.end_at:
        raise HTTPException(
            status_code=400,
            detail="start_at must be before end_at",
        )

    rule = BudgetRule(
        account_id=account.id,
        name=body.name,
        limit_type=body.limit_type,
        limit_amount=body.limit_amount,
        priority=body.priority,
        days_of_week=body.days_of_week,
        start_at=body.start_at,
        end_at=body.end_at,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return await _rule_response(rule, account.id, account.currency)


@router.put("/rules/{rule_id}", response_model=BudgetRuleResponse)
async def update_budget_rule(
    rule_id: str,
    body: BudgetRuleUpdate,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BudgetRule).where(
            BudgetRule.id == rule_id, BudgetRule.account_id == account.id
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Budget rule not found")

    if body.name is not None:
        rule.name = body.name
    if body.limit_amount is not None:
        rule.limit_amount = body.limit_amount
    if body.priority is not None:
        rule.priority = body.priority
    if body.is_active is not None:
        rule.is_active = body.is_active
    if body.days_of_week is not None:
        if not all(0 <= d <= 6 for d in body.days_of_week):
            raise HTTPException(
                status_code=400,
                detail="days_of_week values must be 0-6 (Mon-Sun)",
            )
        rule.days_of_week = body.days_of_week
    if body.start_at is not None:
        rule.start_at = body.start_at
    if body.end_at is not None:
        rule.end_at = body.end_at

    await db.commit()
    await db.refresh(rule)

    return await _rule_response(rule, account.id, account.currency)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_budget_rule(
    rule_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BudgetRule).where(
            BudgetRule.id == rule_id, BudgetRule.account_id == account.id
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Budget rule not found")

    await db.delete(rule)
    await db.commit()
