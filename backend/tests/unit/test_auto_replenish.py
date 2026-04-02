from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.services.auto_replenish import maybe_auto_replenish


def _make_agent(
    budget="100.00",
    spent="0.00",
    held="0.00",
    enabled=False,
    threshold=None,
    amount=None,
    max_budget=None,
):
    agent = MagicMock()
    agent.id = "agent-1"
    agent.budget = Decimal(budget)
    agent.spent = Decimal(spent)
    agent.held = Decimal(held)
    agent.auto_replenish_enabled = enabled
    agent.auto_replenish_threshold = Decimal(threshold) if threshold else None
    agent.auto_replenish_amount = Decimal(amount) if amount else None
    agent.auto_replenish_max_budget = Decimal(max_budget) if max_budget else None
    return agent


class TestMaybeAutoReplenish:
    async def test_disabled(self):
        agent = _make_agent(budget="5.00", spent="0.00", enabled=False)
        db = AsyncMock()
        result = await maybe_auto_replenish(agent, db)
        assert result is None
        db.execute.assert_not_called()

    async def test_above_threshold(self):
        agent = _make_agent(
            budget="100.00",
            spent="80.00",
            enabled=True,
            threshold="10.00",
            amount="50.00",
        )
        db = AsyncMock()
        # remaining = 100 - 80 = 20 >= 10 threshold
        result = await maybe_auto_replenish(agent, db)
        assert result is None

    async def test_triggers_when_below_threshold(self):
        agent = _make_agent(
            budget="100.00",
            spent="95.00",
            enabled=True,
            threshold="10.00",
            amount="50.00",
        )
        db = AsyncMock()
        # remaining = 100 - 95 = 5 < 10 threshold → top up by 50
        result = await maybe_auto_replenish(agent, db)
        assert result == Decimal("50.00")
        db.execute.assert_called_once()

    async def test_respects_max_budget_cap(self):
        agent = _make_agent(
            budget="480.00",
            spent="475.00",
            enabled=True,
            threshold="10.00",
            amount="50.00",
            max_budget="500.00",
        )
        db = AsyncMock()
        # remaining = 5 < 10 → want to add 50, but capped at 500-480=20
        result = await maybe_auto_replenish(agent, db)
        assert result == Decimal("20.00")

    async def test_max_budget_already_reached(self):
        agent = _make_agent(
            budget="500.00",
            spent="495.00",
            enabled=True,
            threshold="10.00",
            amount="50.00",
            max_budget="500.00",
        )
        db = AsyncMock()
        # budget already at max_budget → no top-up
        result = await maybe_auto_replenish(agent, db)
        assert result is None

    async def test_no_threshold_set(self):
        agent = _make_agent(budget="5.00", spent="0.00", enabled=True)
        db = AsyncMock()
        result = await maybe_auto_replenish(agent, db)
        assert result is None

    async def test_held_reduces_remaining(self):
        agent = _make_agent(
            budget="100.00",
            spent="80.00",
            held="15.00",
            enabled=True,
            threshold="10.00",
            amount="50.00",
        )
        db = AsyncMock()
        # remaining = 100 - 80 - 15 = 5 < 10 → triggers
        result = await maybe_auto_replenish(agent, db)
        assert result == Decimal("50.00")
