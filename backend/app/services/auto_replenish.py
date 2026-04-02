from decimal import Decimal

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent


async def maybe_auto_replenish(agent: Agent, db: AsyncSession) -> Decimal | None:
    """Top up agent budget if remaining drops below threshold.

    Returns the top-up amount if replenishment occurred, None otherwise.
    Must be called while the agent row is locked (SELECT FOR UPDATE).
    """
    if not agent.auto_replenish_enabled:
        return None
    if agent.auto_replenish_threshold is None or agent.auto_replenish_amount is None:
        return None

    remaining = agent.budget - agent.spent - agent.held
    if remaining >= agent.auto_replenish_threshold:
        return None

    top_up = agent.auto_replenish_amount

    if agent.auto_replenish_max_budget is not None:
        if agent.budget >= agent.auto_replenish_max_budget:
            return None
        top_up = min(top_up, agent.auto_replenish_max_budget - agent.budget)

    if top_up <= 0:
        return None

    await db.execute(
        update(Agent).where(Agent.id == agent.id).values(budget=Agent.budget + top_up)
    )
    return top_up
