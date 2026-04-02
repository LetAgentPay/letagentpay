from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_account, get_owner_agent
from app.models import Account, Agent, PurchaseRequest
from app.schemas import (
    AdjustBudgetRequest,
    AgentListResponse,
    AgentResponse,
    AutoReplenishRequest,
    AutoReplenishResponse,
    BudgetResponse,
    CreateAgentRequest,
    UpdateAgentRequest,
)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


def _agent_response(agent: Agent, pending_count: int = 0) -> AgentResponse:
    auto_replenish = None
    if agent.auto_replenish_enabled:
        auto_replenish = AutoReplenishResponse(
            enabled=True,
            threshold=agent.auto_replenish_threshold,
            amount=agent.auto_replenish_amount,
            max_budget=agent.auto_replenish_max_budget,
        )
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        status=agent.status,
        is_sandbox=agent.is_sandbox,
        budget=agent.budget,
        spent=agent.spent,
        held=agent.held,
        remaining=agent.budget - agent.spent - agent.held,
        pending_count=pending_count,
        policy=agent.policy,
        policy_text=agent.policy_text,
        token=agent.token,
        auto_replenish=auto_replenish,
        created_at=agent.created_at,
    )


@router.get("", response_model=AgentListResponse)
async def list_agents(
    include_archived: bool = False,
    is_sandbox: bool | None = None,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    query = select(Agent).where(Agent.account_id == account.id)
    if not include_archived:
        query = query.where(Agent.status != "archived")
    if is_sandbox is not None:
        query = query.where(Agent.is_sandbox == is_sandbox)
    result = await db.execute(query.order_by(Agent.created_at))
    agents = result.scalars().all()

    # Fetch pending counts for all agents in one query
    agent_ids = [a.id for a in agents]
    pending_counts: dict[str, int] = {}
    if agent_ids:
        rows = await db.execute(
            select(
                PurchaseRequest.agent_id,
                func.count(PurchaseRequest.id),
            )
            .where(
                PurchaseRequest.agent_id.in_(agent_ids),
                PurchaseRequest.status == "pending",
            )
            .group_by(PurchaseRequest.agent_id)
        )
        pending_counts = {row[0]: row[1] for row in rows}

    return AgentListResponse(
        agents=[_agent_response(a, pending_counts.get(a.id, 0)) for a in agents]
    )


async def _check_name_unique(
    name: str,
    account_id: str,
    is_sandbox: bool,
    db: AsyncSession,
    exclude_agent_id: str | None = None,
) -> None:
    query = select(Agent).where(
        Agent.account_id == account_id,
        Agent.name == name,
        Agent.is_sandbox == is_sandbox,
        Agent.status != "archived",
    )
    if exclude_agent_id:
        query = query.where(Agent.id != exclude_agent_id)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="Agent with this name already exists"
        )


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    body: CreateAgentRequest,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    await _check_name_unique(body.name, account.id, body.is_sandbox, db)
    agent = Agent(
        account_id=account.id,
        name=body.name,
        description=body.description,
        is_sandbox=body.is_sandbox,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return _agent_response(agent)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_owner_agent(agent_id, account, db)
    row = await db.execute(
        select(func.count(PurchaseRequest.id)).where(
            PurchaseRequest.agent_id == agent.id,
            PurchaseRequest.status == "pending",
        )
    )
    pending_count = row.scalar() or 0
    return _agent_response(agent, pending_count)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    body: UpdateAgentRequest,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_owner_agent(agent_id, account, db)
    if body.name is not None:
        await _check_name_unique(body.name, account.id, agent.is_sandbox, db, agent.id)
        agent.name = body.name
    if body.description is not None:
        agent.description = body.description
    await db.commit()
    await db.refresh(agent)
    return _agent_response(agent)


@router.post("/{agent_id}/pause")
async def pause_agent(
    agent_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_owner_agent(agent_id, account, db)
    agent.status = "paused"
    await db.commit()
    return {"status": "paused"}


@router.post("/{agent_id}/resume")
async def resume_agent(
    agent_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_owner_agent(agent_id, account, db)
    agent.status = "active"
    await db.commit()
    return {"status": "active"}


@router.post("/{agent_id}/archive")
async def archive_agent(
    agent_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_owner_agent(agent_id, account, db)
    if agent.status == "archived":
        raise HTTPException(status_code=400, detail="Agent is already archived")
    agent.status = "archived"
    await db.commit()
    return {"status": "archived"}


@router.post("/{agent_id}/restore")
async def restore_agent(
    agent_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_owner_agent(agent_id, account, db)
    if agent.status != "archived":
        raise HTTPException(status_code=400, detail="Agent is not archived")
    agent.status = "active"
    await db.commit()
    return {"status": "active"}


@router.post("/{agent_id}/budget", response_model=BudgetResponse)
async def adjust_budget(
    agent_id: str,
    body: AdjustBudgetRequest,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_owner_agent(agent_id, account, db)
    if body.amount < 0:
        remaining = agent.budget - agent.spent - agent.held
        if remaining + body.amount < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot withdraw more than remaining ({remaining})",
            )
    agent.budget = agent.budget + body.amount
    await db.commit()
    await db.refresh(agent)
    return BudgetResponse(
        budget=agent.budget,
        spent=agent.spent,
        held=agent.held,
        remaining=agent.budget - agent.spent - agent.held,
    )


@router.put("/{agent_id}/auto-replenish", response_model=AutoReplenishResponse)
async def set_auto_replenish(
    agent_id: str,
    body: AutoReplenishRequest,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_owner_agent(agent_id, account, db)
    agent.auto_replenish_enabled = True
    agent.auto_replenish_threshold = body.threshold
    agent.auto_replenish_amount = body.amount
    agent.auto_replenish_max_budget = body.max_budget
    await db.commit()
    return AutoReplenishResponse(
        enabled=True,
        threshold=body.threshold,
        amount=body.amount,
        max_budget=body.max_budget,
    )


@router.delete("/{agent_id}/auto-replenish")
async def disable_auto_replenish(
    agent_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_owner_agent(agent_id, account, db)
    agent.auto_replenish_enabled = False
    agent.auto_replenish_threshold = None
    agent.auto_replenish_amount = None
    agent.auto_replenish_max_budget = None
    await db.commit()
    return {"message": "Auto-replenish disabled"}
