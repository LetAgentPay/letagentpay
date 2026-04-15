from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.dependencies import get_current_account
from app.models import Account, Agent, PurchaseRequest
from app.redis import get_redis
from app.schemas import PurchaseRequestListItem
from app.services.request_actions import (
    approve_purchase_request,
    reject_purchase_request,
)
from app.services.spending import remove_account_held, remove_held
from app.utils import clamp_zero, ensure_utc, utcnow

router = APIRouter(prefix="/api/v1", tags=["requests"])


def _extract_rejection_reason(policy_check: dict | None) -> str | None:
    if not policy_check:
        return None
    checks = policy_check.get("checks", [])
    failed = [c["detail"] for c in checks if c.get("result") == "fail"]
    return "; ".join(failed) if failed else None


@router.get("/agents/{agent_id}/requests")
async def list_requests(
    agent_id: str,
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    # Verify ownership
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.account_id == account.id)
    )
    agent_obj = result.scalar_one_or_none()
    if not agent_obj:
        raise HTTPException(status_code=404, detail="Agent not found")

    query = select(PurchaseRequest).where(PurchaseRequest.agent_id == agent_id)
    count_query = (
        select(func.count())
        .select_from(PurchaseRequest)
        .where(PurchaseRequest.agent_id == agent_id)
    )

    if status:
        query = query.where(PurchaseRequest.status == status)
        count_query = count_query.where(PurchaseRequest.status == status)

    query = (
        query.order_by(PurchaseRequest.created_at.desc()).offset(offset).limit(limit)
    )

    req_result = await db.execute(query)
    requests = req_result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return {
        "items": [
            PurchaseRequestListItem(
                id=r.id,
                agent_id=r.agent_id,
                agent_name=agent_obj.name,
                amount=r.amount,
                category=r.category,
                original_category=r.original_category,
                merchant=r.merchant,
                description=r.description,
                agent_comment=r.agent_comment,
                status=r.status,
                rejection_reason=(
                    _extract_rejection_reason(r.policy_check)
                    if r.status == "rejected"
                    else None
                ),
                actual_amount=r.actual_amount,
                receipt_url=r.receipt_url,
                settlement_method=r.settlement_method,
                settlement_currency=r.settlement_currency,
                tx_hash=r.tx_hash,
                completed_at=r.completed_at,
                created_at=r.created_at,
                reviewed_at=r.reviewed_at,
            )
            for r in requests
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/requests/{request_id}")
async def get_request(
    request_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PurchaseRequest)
        .options(joinedload(PurchaseRequest.agent))
        .where(PurchaseRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req or req.agent.account_id != account.id:
        raise HTTPException(status_code=404, detail="Request not found")

    return {
        "id": req.id,
        "agent_id": req.agent_id,
        "amount": req.amount,
        "category": req.category,
        "merchant": req.merchant,
        "description": req.description,
        "agent_comment": req.agent_comment,
        "status": req.status,
        "actual_amount": req.actual_amount,
        "receipt_url": req.receipt_url,
        "settlement_method": req.settlement_method,
        "settlement_currency": req.settlement_currency,
        "tx_hash": req.tx_hash,
        "policy_check": req.policy_check,
        "created_at": req.created_at,
        "reviewed_at": req.reviewed_at,
        "completed_at": req.completed_at,
        "expires_at": req.expires_at,
    }


@router.post("/requests/{request_id}/approve")
async def approve_request(
    request_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    # Lock request row to prevent concurrent approve/reject race condition
    result = await db.execute(
        select(PurchaseRequest)
        .options(joinedload(PurchaseRequest.agent).joinedload(Agent.account))
        .where(PurchaseRequest.id == request_id)
        .with_for_update(of=PurchaseRequest)
    )
    req = result.scalar_one_or_none()
    if not req or req.agent.account_id != account.id:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")
    if ensure_utc(req.expires_at) < utcnow():
        req.status = "expired"
        # Release hold on expiry
        await db.execute(
            update(Agent)
            .where(Agent.id == req.agent_id)
            .values(held=clamp_zero(Agent.held - req.amount))
        )
        await db.execute(
            update(Account)
            .where(Account.id == account.id)
            .values(account_held=clamp_zero(Account.account_held - req.amount))
        )
        await db.commit()
        redis = get_redis()
        tz = req.agent.account.timezone
        req_currency = req.currency or req.agent.account.currency
        await remove_held(redis, req.agent_id, req.amount, req_currency, tz)
        await remove_account_held(redis, account.id, req.amount, req_currency, tz)
        raise HTTPException(status_code=400, detail="Request has expired")

    # Approve — convert hold to spent
    redis = get_redis()
    await approve_purchase_request(db, redis, req, account.id)

    return {
        "request_id": req.id,
        "status": "approved",
        "budget_remaining": req.agent.budget - req.agent.spent,
    }


@router.post("/requests/{request_id}/reject")
async def reject_request(
    request_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    # Lock request row to prevent concurrent approve/reject race condition
    result = await db.execute(
        select(PurchaseRequest)
        .options(joinedload(PurchaseRequest.agent).joinedload(Agent.account))
        .where(PurchaseRequest.id == request_id)
        .with_for_update(of=PurchaseRequest)
    )
    req = result.scalar_one_or_none()
    if not req or req.agent.account_id != account.id:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    # Reject — release hold
    redis = get_redis()
    await reject_purchase_request(db, redis, req, account.id)

    return {"request_id": req.id, "status": "rejected"}
