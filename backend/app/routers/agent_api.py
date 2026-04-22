import asyncio
import json
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.dependencies import get_agent_by_token
from app.models import Account, Agent, BudgetRule, Category, PurchaseRequest
from app.redis import get_redis
from app.schemas import (
    BudgetResponse,
    ConfirmPurchaseRequest,
    CreatePurchaseRequest,
    Policy,
    PurchaseRequestResponse,
)
from app.services.auto_replenish import maybe_auto_replenish
from app.services.category_resolver import resolve_category
from app.services.notification_dispatcher import (
    NotificationEvent,
    dispatch_notification,
)
from app.services.playground import PLAYGROUND_EMAIL_DOMAIN, increment_request_count
from app.services.policy_engine import (
    check_policy,
    evaluate_budget_rules,
    should_auto_approve,
)
from app.services.rate_limit import check_rate_limit
from app.services.realtime import publish_event
from app.services.spending import (
    add_account_held,
    add_account_spent,
    add_held,
    add_spent,
    remove_account_held,
    remove_held,
)
from app.utils import clamp_zero, ensure_utc, utcnow

router = APIRouter(prefix="/api/v1/agent-api", tags=["agent-api"])


_IDEMPOTENCY_TTL = 24 * 3600  # 24 hours
_MAX_PENDING_REQUESTS = 100


@router.post("/requests", response_model=PurchaseRequestResponse, status_code=201)
async def create_purchase_request(
    body: CreatePurchaseRequest,
    agent: Agent = Depends(get_agent_by_token),
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    # Rate limit: 60 requests per minute per agent
    redis = get_redis()
    await check_rate_limit(redis, f"rate_limit:agent:{agent.id}", 60, 60)

    # Playground request limit
    if agent.account.email.endswith(f"@{PLAYGROUND_EMAIL_DOMAIN}"):
        session_id = agent.account.email.split("@")[0]
        try:
            await increment_request_count(session_id)
        except ValueError as e:
            raise HTTPException(status_code=429, detail=str(e))

    # Idempotency: return cached response if same key was used before
    if idempotency_key:
        cache_key = f"idempotency:{agent.id}:{idempotency_key}"
        cached = await redis.get(cache_key)
        if cached:
            return PurchaseRequestResponse(**json.loads(cached))

    # Resolve category (per-account aliases + AI fallback)
    resolved_category, original_category, category_status = await resolve_category(
        body.category, agent.account_id, db
    )
    resolved_body = body.model_copy(update={"category": resolved_category})

    # Lock agent row to serialise concurrent requests for the same agent.
    # populate_existing=True forces SQLAlchemy to overwrite cached ORM state
    # with fresh DB values, so we see changes committed by prior requests.
    result = await db.execute(
        select(Agent)
        .options(joinedload(Agent.account))
        .where(Agent.id == agent.id)
        .with_for_update(of=Agent)
        .execution_options(populate_existing=True)
    )
    agent = result.scalar_one()

    # Also lock Account row to serialise requests across different agents
    # of the same account, preventing account-level budget limit bypass.
    await db.execute(
        select(Account)
        .where(Account.id == agent.account_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    # Guard against excessive pending requests
    pending_count_result = await db.execute(
        select(func.count())
        .select_from(PurchaseRequest)
        .where(
            PurchaseRequest.agent_id == agent.id,
            PurchaseRequest.status == "pending",
        )
    )
    if (pending_count_result.scalar() or 0) >= _MAX_PENDING_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Too many pending requests. Wait for existing requests to be resolved.",
        )

    # Validate currency if provided
    if body.currency and body.currency != agent.account.currency:
        raise HTTPException(
            status_code=400,
            detail=f"Currency mismatch: expected {agent.account.currency}",
        )

    timezone = agent.account.timezone
    request_currency = body.currency or agent.account.currency

    # Run agent-level policy checks (using resolved category)
    checks, all_passed = await check_policy(
        agent, resolved_body, redis, request_currency, timezone
    )
    policy_check_data = {
        "passed": all_passed,
        "checks": [c.model_dump() for c in checks],
    }

    if not all_passed:
        # Rejected by agent policy — save but don't create pending request
        req = PurchaseRequest(
            agent_id=agent.id,
            amount=body.amount,
            currency=request_currency,
            category=resolved_category,
            original_category=original_category,
            category_status=category_status,
            merchant=body.merchant_name,
            description=body.description,
            agent_comment=body.agent_comment,
            status="rejected",
            policy_check=policy_check_data,
            expires_at=utcnow(),
            reviewed_at=utcnow(),
        )
        db.add(req)
        await db.commit()
        await db.refresh(req)

        await publish_event(
            redis,
            agent.id,
            "new_request",
            {
                "request_id": req.id,
                "status": "rejected",
                "amount": str(body.amount),
                "currency": request_currency,
                "category": resolved_category,
            },
        )

        resp = PurchaseRequestResponse(
            request_id=req.id,
            status="rejected",
            currency=request_currency,
            category=resolved_category,
            original_category=original_category,
            policy_check=policy_check_data,
            auto_approved=False,
        )
        if idempotency_key:
            await redis.set(cache_key, resp.model_dump_json(), ex=_IDEMPOTENCY_TTL)
        return resp

    # Run account-level budget rules
    rules_result = await db.execute(
        select(BudgetRule).where(BudgetRule.account_id == agent.account_id)
    )
    budget_rules = rules_result.scalars().all()

    if budget_rules:
        acct_checks, acct_passed = await evaluate_budget_rules(
            agent.account,
            body.amount,
            list(budget_rules),
            redis,
            request_currency,
            timezone,
        )
        if not acct_passed:
            # Merge agent checks + account checks
            all_checks = checks + acct_checks
            policy_check_data = {
                "passed": False,
                "checks": [c.model_dump() for c in all_checks],
            }
            req = PurchaseRequest(
                agent_id=agent.id,
                amount=body.amount,
                currency=request_currency,
                category=resolved_category,
                original_category=original_category,
                category_status=category_status,
                merchant=body.merchant_name,
                description=body.description,
                agent_comment=body.agent_comment,
                status="rejected",
                policy_check=policy_check_data,
                expires_at=utcnow(),
                reviewed_at=utcnow(),
            )
            db.add(req)
            await db.commit()
            await db.refresh(req)

            await publish_event(
                redis,
                agent.id,
                "new_request",
                {
                    "request_id": req.id,
                    "status": "rejected",
                    "amount": str(body.amount),
                    "currency": request_currency,
                    "category": resolved_category,
                },
            )

            resp = PurchaseRequestResponse(
                request_id=req.id,
                status="rejected",
                currency=request_currency,
                category=resolved_category,
                original_category=original_category,
                policy_check=policy_check_data,
                auto_approved=False,
            )
            if idempotency_key:
                await redis.set(cache_key, resp.model_dump_json(), ex=_IDEMPOTENCY_TTL)
            return resp
        # Add account-level checks to the result
        checks.extend(acct_checks)
        policy_check_data = {
            "passed": True,
            "checks": [c.model_dump() for c in checks],
        }

    # Check auto-approve
    policy = Policy(**agent.policy) if agent.policy else Policy()
    auto = should_auto_approve(resolved_body, policy)

    # Collect active temporal rule IDs for Redis tracking
    active_temporal_rule_ids = (
        [
            r.id
            for r in budget_rules
            if r.is_active and r.limit_type == "total" and r.start_at and r.end_at
        ]
        if budget_rules
        else []
    )

    if auto:
        # Auto-approve: deduct immediately
        req = PurchaseRequest(
            agent_id=agent.id,
            amount=body.amount,
            currency=request_currency,
            category=resolved_category,
            original_category=original_category,
            category_status=category_status,
            merchant=body.merchant_name,
            description=body.description,
            agent_comment=body.agent_comment,
            status="auto_approved",
            policy_check=policy_check_data,
            expires_at=utcnow(),
            reviewed_at=utcnow(),
        )
        db.add(req)
        # Atomic increment (row is locked by SELECT FOR UPDATE)
        await db.execute(
            update(Agent)
            .where(Agent.id == agent.id)
            .values(spent=Agent.spent + body.amount)
        )
        await db.execute(
            update(Account)
            .where(Account.id == agent.account_id)
            .values(account_spent=Account.account_spent + body.amount)
        )
        # Update Redis counters before commit so concurrent requests
        # (waiting on FOR UPDATE lock) see fresh values upon unlock
        await add_spent(redis, agent.id, body.amount, request_currency, timezone)
        await add_account_spent(
            redis,
            agent.account_id,
            body.amount,
            request_currency,
            timezone,
            active_temporal_rule_ids,
        )
        # Auto-replenish if remaining dropped below threshold
        await maybe_auto_replenish(agent, db)
        await db.commit()
        await db.refresh(req)
        await db.refresh(agent)
        await publish_event(
            redis,
            agent.id,
            "new_request",
            {
                "request_id": req.id,
                "status": "auto_approved",
                "amount": str(body.amount),
                "currency": request_currency,
                "category": resolved_category,
            },
        )
        await publish_event(
            redis,
            agent.id,
            "budget_updated",
            {
                "budget": str(agent.budget),
                "spent": str(agent.spent),
                "currency": request_currency,
            },
        )

        resp = PurchaseRequestResponse(
            request_id=req.id,
            status="auto_approved",
            currency=request_currency,
            category=resolved_category,
            original_category=original_category,
            policy_check=policy_check_data,
            auto_approved=True,
            budget_remaining=agent.budget - agent.spent - agent.held,
        )
        if idempotency_key:
            await redis.set(cache_key, resp.model_dump_json(), ex=_IDEMPOTENCY_TTL)
        return resp

    # Manual approval needed
    expiry_minutes = agent.account.request_expiry_minutes
    expires_at = utcnow() + timedelta(minutes=expiry_minutes)
    req = PurchaseRequest(
        agent_id=agent.id,
        amount=body.amount,
        currency=request_currency,
        category=resolved_category,
        original_category=original_category,
        category_status=category_status,
        merchant=body.merchant_name,
        description=body.description,
        agent_comment=body.agent_comment,
        status="pending",
        policy_check=policy_check_data,
        expires_at=expires_at,
    )
    db.add(req)
    # Hold funds so concurrent requests see reduced available budget
    await db.execute(
        update(Agent).where(Agent.id == agent.id).values(held=Agent.held + body.amount)
    )
    await db.execute(
        update(Account)
        .where(Account.id == agent.account_id)
        .values(account_held=Account.account_held + body.amount)
    )
    await add_held(redis, agent.id, body.amount, request_currency, timezone)
    await add_account_held(
        redis,
        agent.account_id,
        body.amount,
        request_currency,
        timezone,
        active_temporal_rule_ids,
    )
    await db.commit()
    await db.refresh(req)

    await publish_event(
        redis,
        agent.id,
        "new_request",
        {
            "request_id": req.id,
            "status": "pending",
            "amount": str(body.amount),
            "currency": request_currency,
            "category": resolved_category,
            "merchant": body.merchant_name,
        },
    )

    # Dispatch notifications in background — failures must not block the API response.
    # Pass db=None so the dispatcher creates its own session (ours closes with the handler).
    asyncio.create_task(
        dispatch_notification(
            None,
            redis,
            agent.account_id,
            NotificationEvent(
                event_type="pending_request",
                request_id=req.id,
                agent_name=agent.name,
                amount=str(body.amount),
                currency=request_currency,
                category=resolved_category,
                expires_at=expires_at,
                account_expiry_minutes=agent.account.request_expiry_minutes,
                merchant=body.merchant_name,
                agent_comment=body.agent_comment,
            ),
        )
    )

    if category_status == "unresolved":
        asyncio.create_task(
            dispatch_notification(
                None,
                redis,
                agent.account_id,
                NotificationEvent(
                    event_type="unresolved_category",
                    request_id=req.id,
                    agent_name=agent.name,
                    amount=str(body.amount),
                    currency=request_currency,
                    category="other",
                    merchant=body.merchant_name,
                    agent_comment=f"Unknown category: {body.category}",
                ),
            )
        )

    resp = PurchaseRequestResponse(
        request_id=req.id,
        status="pending",
        currency=request_currency,
        category=resolved_category,
        original_category=original_category,
        policy_check=policy_check_data,
        auto_approved=False,
        expires_at=expires_at,
    )
    if idempotency_key:
        await redis.set(cache_key, resp.model_dump_json(), ex=_IDEMPOTENCY_TTL)
    return resp


@router.get("/requests")
async def list_requests(
    agent: Agent = Depends(get_agent_by_token),
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """List agent's purchase requests with optional status filter."""
    limit = min(limit, 100)
    query = (
        select(PurchaseRequest)
        .where(PurchaseRequest.agent_id == agent.id)
        .order_by(PurchaseRequest.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status:
        query = query.where(PurchaseRequest.status == status)

    result = await db.execute(query)
    requests = result.scalars().all()
    return {
        "requests": [
            {
                "request_id": r.id,
                "status": r.status,
                "amount": r.amount,
                "currency": r.currency,
                "category": r.category,
                "merchant": r.merchant,
                "description": r.description,
                "created_at": r.created_at,
                "reviewed_at": r.reviewed_at,
                "expires_at": r.expires_at,
            }
            for r in requests
        ],
        "total": len(requests),
        "limit": limit,
        "offset": offset,
    }


@router.get("/requests/{request_id}")
async def get_request_status(
    request_id: str,
    agent: Agent = Depends(get_agent_by_token),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PurchaseRequest).where(
            PurchaseRequest.id == request_id,
            PurchaseRequest.agent_id == agent.id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Check expiry — release hold if expired
    if req.status == "pending" and ensure_utc(req.expires_at) < utcnow():
        req.status = "expired"
        await db.execute(
            update(Agent)
            .where(Agent.id == req.agent_id)
            .values(held=clamp_zero(Agent.held - req.amount))
        )
        # Load account for hold release
        agent_result = await db.execute(
            select(Agent)
            .options(joinedload(Agent.account))
            .where(Agent.id == req.agent_id)
        )
        agent_obj = agent_result.scalar_one()
        await db.execute(
            update(Account)
            .where(Account.id == agent_obj.account_id)
            .values(account_held=clamp_zero(Account.account_held - req.amount))
        )
        await db.commit()
        redis = get_redis()
        tz = agent_obj.account.timezone
        req_currency = req.currency or agent_obj.account.currency
        await remove_held(redis, req.agent_id, req.amount, req_currency, tz)
        await remove_account_held(
            redis, agent_obj.account_id, req.amount, req_currency, tz
        )

    return {
        "request_id": req.id,
        "status": req.status,
        "amount": req.amount,
        "category": req.category,
        "created_at": req.created_at,
        "reviewed_at": req.reviewed_at,
    }


@router.post("/requests/{request_id}/confirm")
async def confirm_purchase(
    request_id: str,
    body: ConfirmPurchaseRequest,
    agent: Agent = Depends(get_agent_by_token),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PurchaseRequest).where(
            PurchaseRequest.id == request_id,
            PurchaseRequest.agent_id == agent.id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.status not in ("approved", "auto_approved"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm request with status '{req.status}'",
        )

    req.status = "completed" if body.success else "failed"
    req.completed_at = utcnow()

    # Load agent with account for timezone
    agent_result = await db.execute(
        select(Agent).options(joinedload(Agent.account)).where(Agent.id == agent.id)
    )
    agent_with_account = agent_result.scalar_one()
    tz = agent_with_account.account.timezone
    account_id = agent_with_account.account_id

    req_currency = req.currency or agent_with_account.account.currency

    if not body.success:
        # Purchase failed — refund the spent amount
        await db.execute(
            update(Agent)
            .where(Agent.id == agent.id)
            .values(spent=clamp_zero(Agent.spent - req.amount))
        )
        await db.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(account_spent=clamp_zero(Account.account_spent - req.amount))
        )
        redis = get_redis()
        await add_spent(redis, agent.id, -req.amount, req_currency, tz)
        await add_account_spent(redis, account_id, -req.amount, req_currency, tz)
    elif body.actual_amount is not None:
        # Adjust spent if actual amount differs
        diff = body.actual_amount - req.amount
        if diff != 0:
            await db.execute(
                update(Agent)
                .where(Agent.id == agent.id)
                .values(spent=Agent.spent + diff)
            )
            redis = get_redis()
            await add_spent(redis, agent.id, diff, req_currency, tz)
            await db.execute(
                update(Account)
                .where(Account.id == account_id)
                .values(account_spent=Account.account_spent + diff)
            )
            await add_account_spent(redis, account_id, diff, req_currency, tz)
        req.actual_amount = body.actual_amount

    if body.receipt_url is not None:
        req.receipt_url = body.receipt_url

    await db.commit()

    redis = get_redis()
    await publish_event(
        redis,
        agent.id,
        "request_updated",
        {
            "request_id": req.id,
            "status": req.status,
        },
    )

    return {
        "request_id": req.id,
        "status": req.status,
        "actual_amount": str(req.actual_amount) if req.actual_amount else None,
    }


@router.get("/budget", response_model=BudgetResponse)
async def get_budget(
    agent: Agent = Depends(get_agent_by_token),
    db: AsyncSession = Depends(get_db),
):
    # Reload with account for currency
    result = await db.execute(
        select(Agent).options(joinedload(Agent.account)).where(Agent.id == agent.id)
    )
    agent = result.scalar_one()
    return BudgetResponse(
        budget=agent.budget,
        spent=agent.spent,
        held=agent.held,
        remaining=agent.budget - agent.spent - agent.held,
        currency=agent.account.currency,
    )


@router.get("/policy")
async def get_policy(
    agent: Agent = Depends(get_agent_by_token),
):
    return {"policy": agent.policy}


@router.get("/categories")
async def get_categories(
    agent: Agent = Depends(get_agent_by_token),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Category.name)
        .where(Category.account_id == agent.account_id, Category.is_active.is_(True))
        .order_by(Category.name)
    )
    return {"categories": [row[0] for row in result.all()]}
