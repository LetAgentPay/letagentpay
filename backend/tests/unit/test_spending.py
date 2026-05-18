"""Tests for Redis spending counters."""

from decimal import Decimal

from app.services.spending import (
    _from_subunits,
    _to_subunits,
    add_spent,
    add_velocity,
    claim_velocity_log_slot,
    get_daily_spent,
    get_monthly_spent,
    get_velocity_counters_atomic,
    get_weekly_spent,
)


class TestSpendingCounters:
    async def test_daily_spent_empty(self, mock_redis):
        result = await get_daily_spent(mock_redis, "agent-1", "USD", "UTC")
        assert result == Decimal(0)

    async def test_add_and_get_daily(self, mock_redis):
        await add_spent(mock_redis, "agent-1", Decimal("150.50"), "USD", "UTC")
        result = await get_daily_spent(mock_redis, "agent-1", "USD", "UTC")
        assert result == Decimal("150.5")

    async def test_accumulate_daily(self, mock_redis):
        await add_spent(mock_redis, "agent-1", Decimal("100"), "USD", "UTC")
        await add_spent(mock_redis, "agent-1", Decimal("200.50"), "USD", "UTC")
        result = await get_daily_spent(mock_redis, "agent-1", "USD", "UTC")
        assert result == Decimal("300.5")

    async def test_weekly_spent(self, mock_redis):
        await add_spent(mock_redis, "agent-1", Decimal("500"), "USD", "UTC")
        result = await get_weekly_spent(mock_redis, "agent-1", "USD", "UTC")
        assert result == Decimal("500")

    async def test_monthly_spent(self, mock_redis):
        await add_spent(mock_redis, "agent-1", Decimal("1000"), "USD", "UTC")
        result = await get_monthly_spent(mock_redis, "agent-1", "USD", "UTC")
        assert result == Decimal("1000")

    async def test_separate_agents(self, mock_redis):
        await add_spent(mock_redis, "agent-1", Decimal("100"), "USD", "UTC")
        await add_spent(mock_redis, "agent-2", Decimal("200"), "USD", "UTC")

        r1 = await get_daily_spent(mock_redis, "agent-1", "USD", "UTC")
        r2 = await get_daily_spent(mock_redis, "agent-2", "USD", "UTC")
        assert r1 == Decimal("100")
        assert r2 == Decimal("200")

    async def test_expire_called(self, mock_redis):
        await add_spent(mock_redis, "agent-1", Decimal("100"), "USD", "UTC")
        # 3 calls: daily, weekly, monthly
        assert mock_redis.expire.call_count == 3

    async def test_separate_currencies(self, mock_redis):
        await add_spent(mock_redis, "agent-1", Decimal("100"), "USD", "UTC")
        await add_spent(mock_redis, "agent-1", Decimal("200"), "EUR", "UTC")

        usd = await get_daily_spent(mock_redis, "agent-1", "USD", "UTC")
        eur = await get_daily_spent(mock_redis, "agent-1", "EUR", "UTC")
        assert usd == Decimal("100")
        assert eur == Decimal("200")


class TestSubunitConversion:
    def test_to_subunits_basic(self):
        assert _to_subunits(Decimal("150.50")) == 15050

    def test_to_subunits_whole_number(self):
        assert _to_subunits(Decimal("100")) == 10000

    def test_to_subunits_one_cent(self):
        assert _to_subunits(Decimal("0.01")) == 1

    def test_to_subunits_zero(self):
        assert _to_subunits(Decimal("0")) == 0

    def test_to_subunits_large_amount(self):
        assert _to_subunits(Decimal("9999999.99")) == 999999999

    def test_to_subunits_rounding(self):
        # Uses ROUND_HALF_EVEN (banker's rounding): 1.005 * 100 = 100.5 → 100
        assert _to_subunits(Decimal("1.005")) == 100
        # 1.015 * 100 = 101.5 → 102 (rounds to even)
        assert _to_subunits(Decimal("1.015")) == 102
        # Below midpoint always truncates: 1.004 → 100
        assert _to_subunits(Decimal("1.004")) == 100

    def test_from_subunits_basic(self):
        assert _from_subunits("15050") == Decimal("150.50")

    def test_from_subunits_none(self):
        assert _from_subunits(None) == Decimal(0)

    def test_from_subunits_empty(self):
        assert _from_subunits("") == Decimal(0)

    def test_from_subunits_zero(self):
        assert _from_subunits("0") == Decimal(0)

    def test_from_subunits_bytes(self):
        assert _from_subunits(b"15050") == Decimal("150.50")

    def test_roundtrip_precision(self):
        amounts = [
            Decimal("0.01"),
            Decimal("1.00"),
            Decimal("99.99"),
            Decimal("150.50"),
            Decimal("9999999.99"),
        ]
        for amount in amounts:
            assert _from_subunits(str(_to_subunits(amount))) == amount


class TestVelocityCounters:
    async def test_empty_counters(self, mock_redis):
        per_minute, per_hour = await get_velocity_counters_atomic(mock_redis, "agent-1")
        assert per_minute == 0
        assert per_hour == 0

    async def test_single_increment(self, mock_redis):
        await add_velocity(mock_redis, "agent-1")
        per_minute, per_hour = await get_velocity_counters_atomic(mock_redis, "agent-1")
        assert per_minute == 1
        assert per_hour == 1

    async def test_multiple_increments(self, mock_redis):
        for _ in range(5):
            await add_velocity(mock_redis, "agent-1")
        per_minute, per_hour = await get_velocity_counters_atomic(mock_redis, "agent-1")
        assert per_minute == 5
        assert per_hour == 5

    async def test_separate_agents(self, mock_redis):
        await add_velocity(mock_redis, "agent-1")
        await add_velocity(mock_redis, "agent-1")
        await add_velocity(mock_redis, "agent-2")

        a1_minute, _ = await get_velocity_counters_atomic(mock_redis, "agent-1")
        a2_minute, _ = await get_velocity_counters_atomic(mock_redis, "agent-2")
        assert a1_minute == 2
        assert a2_minute == 1


class TestClaimVelocityLogSlot:
    async def test_first_caller_wins(self, mock_redis):
        result = await claim_velocity_log_slot(mock_redis, "agent-1", "minute", "req-1")
        assert result is None

    async def test_subsequent_callers_get_existing_id(self, mock_redis):
        first = await claim_velocity_log_slot(mock_redis, "agent-1", "minute", "req-1")
        assert first is None

        second = await claim_velocity_log_slot(mock_redis, "agent-1", "minute", "req-2")
        assert second == "req-1"

        third = await claim_velocity_log_slot(mock_redis, "agent-1", "minute", "req-3")
        assert third == "req-1"

    async def test_minute_and_hour_scopes_independent(self, mock_redis):
        await claim_velocity_log_slot(mock_redis, "agent-1", "minute", "req-minute")
        # Hour scope must have its own slot
        result = await claim_velocity_log_slot(
            mock_redis, "agent-1", "hour", "req-hour"
        )
        assert result is None

    async def test_separate_agents_independent(self, mock_redis):
        await claim_velocity_log_slot(mock_redis, "agent-1", "minute", "req-1")
        result = await claim_velocity_log_slot(mock_redis, "agent-2", "minute", "req-2")
        assert result is None
