"""Unit tests for policy engine — no DB or HTTP, pure logic."""

from datetime import UTC, datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from app.schemas import CreatePurchaseRequest, Policy, Schedule, ScheduleOverride
from app.services.policy_engine import (
    _check_budget,
    _check_category,
    _check_daily_limit,
    _check_monthly_limit,
    _check_per_request_limit,
    _check_schedule,
    _check_status,
    _check_time_window,
    _check_weekly_limit,
    check_policy,
    evaluate_budget_rules,
    should_auto_approve,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeAgent:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "agent-1")
        self.status = kwargs.get("status", "active")
        self.budget = Decimal(kwargs.get("budget", "10000"))
        self.spent = Decimal(kwargs.get("spent", "0"))
        self.held = Decimal(kwargs.get("held", "0"))
        self.policy = kwargs.get("policy", {})
        self.account = type(
            "Acc", (), {"timezone": "America/New_York", "account_held": Decimal("0")}
        )()


def make_request(**kwargs) -> CreatePurchaseRequest:
    defaults = {"amount": Decimal("100"), "category": "groceries"}
    defaults.update(kwargs)
    return CreatePurchaseRequest(**defaults)


# ---------------------------------------------------------------------------
# Status check
# ---------------------------------------------------------------------------


class TestCheckStatus:
    def test_active(self):
        r = _check_status(FakeAgent(status="active"))
        assert r.result == "pass"

    def test_paused(self):
        r = _check_status(FakeAgent(status="paused"))
        assert r.result == "fail"


# ---------------------------------------------------------------------------
# Category check
# ---------------------------------------------------------------------------


class TestCheckCategory:
    def test_allowed_pass(self):
        policy = Policy(allowed_categories=["groceries", "taxi"])
        r = _check_category("groceries", policy)
        assert r.result == "pass"

    def test_allowed_fail(self):
        policy = Policy(allowed_categories=["groceries"])
        r = _check_category("electronics", policy)
        assert r.result == "fail"

    def test_blocked_fail(self):
        policy = Policy(blocked_categories=["electronics"])
        r = _check_category("electronics", policy)
        assert r.result == "fail"

    def test_blocked_pass(self):
        policy = Policy(blocked_categories=["electronics"])
        r = _check_category("groceries", policy)
        assert r.result == "pass"

    def test_no_restrictions(self):
        policy = Policy()
        r = _check_category("anything", policy)
        assert r.result == "pass"


# ---------------------------------------------------------------------------
# Per-request limit
# ---------------------------------------------------------------------------


class TestCheckPerRequestLimit:
    def test_within_limit(self):
        policy = Policy(per_request_limit=Decimal("500"))
        r = _check_per_request_limit(Decimal("300"), policy)
        assert r.result == "pass"

    def test_at_limit(self):
        policy = Policy(per_request_limit=Decimal("500"))
        r = _check_per_request_limit(Decimal("500"), policy)
        assert r.result == "pass"

    def test_over_limit(self):
        policy = Policy(per_request_limit=Decimal("500"))
        r = _check_per_request_limit(Decimal("501"), policy)
        assert r.result == "fail"

    def test_no_limit(self):
        policy = Policy()
        r = _check_per_request_limit(Decimal("999999"), policy)
        assert r.result == "pass"


# ---------------------------------------------------------------------------
# Schedule check
# ---------------------------------------------------------------------------


class TestCheckSchedule:
    def test_no_schedule(self):
        r = _check_schedule(Policy(), "America/New_York")
        assert r.result == "pass"

    @patch("app.services.policy_engine.datetime")
    def test_within_window(self, mock_dt):
        from app.schemas import Schedule

        mock_dt.now.return_value = datetime(2026, 3, 16, 14, 0, tzinfo=timezone.utc)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        policy = Policy(
            schedule=Schedule(
                timezone="UTC",
                default={"allow": "07:00-23:00"},
            )
        )
        r = _check_schedule(policy, "UTC")
        assert r.result == "pass"

    @patch("app.services.policy_engine.datetime")
    def test_outside_window(self, mock_dt):
        from app.schemas import Schedule

        mock_dt.now.return_value = datetime(2026, 3, 16, 3, 0, tzinfo=timezone.utc)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        policy = Policy(
            schedule=Schedule(
                timezone="UTC",
                default={"allow": "07:00-23:00"},
            )
        )
        r = _check_schedule(policy, "UTC")
        assert r.result == "fail"


# ---------------------------------------------------------------------------
# Daily limit
# ---------------------------------------------------------------------------


class TestCheckDailyLimit:
    def test_within(self):
        policy = Policy(daily_limit=Decimal("5000"))
        r = _check_daily_limit(Decimal("500"), Decimal("3000"), policy, "UTC")
        assert r.result == "pass"

    def test_exceeded(self):
        policy = Policy(daily_limit=Decimal("5000"))
        r = _check_daily_limit(Decimal("500"), Decimal("4800"), policy, "UTC")
        assert r.result == "fail"

    def test_no_limit(self):
        policy = Policy()
        r = _check_daily_limit(Decimal("999999"), Decimal("0"), policy, "UTC")
        assert r.result == "pass"


# ---------------------------------------------------------------------------
# Weekly / Monthly limits
# ---------------------------------------------------------------------------


class TestCheckWeeklyLimit:
    def test_within(self):
        policy = Policy(weekly_limit=Decimal("20000"))
        r = _check_weekly_limit(Decimal("1000"), Decimal("15000"), policy)
        assert r.result == "pass"

    def test_exceeded(self):
        policy = Policy(weekly_limit=Decimal("20000"))
        r = _check_weekly_limit(Decimal("6000"), Decimal("15000"), policy)
        assert r.result == "fail"


class TestCheckMonthlyLimit:
    def test_within(self):
        policy = Policy(monthly_limit=Decimal("50000"))
        r = _check_monthly_limit(Decimal("5000"), Decimal("40000"), policy)
        assert r.result == "pass"

    def test_exceeded(self):
        policy = Policy(monthly_limit=Decimal("50000"))
        r = _check_monthly_limit(Decimal("15000"), Decimal("40000"), policy)
        assert r.result == "fail"


# ---------------------------------------------------------------------------
# Budget check
# ---------------------------------------------------------------------------


class TestCheckBudget:
    def test_sufficient(self):
        r = _check_budget(Decimal("500"), Decimal("10000"))
        assert r.result == "pass"

    def test_insufficient(self):
        r = _check_budget(Decimal("500"), Decimal("100"))
        assert r.result == "fail"

    def test_exact(self):
        r = _check_budget(Decimal("500"), Decimal("500"))
        assert r.result == "pass"


# ---------------------------------------------------------------------------
# Full check_policy
# ---------------------------------------------------------------------------


class TestCheckPolicy:
    async def test_all_pass(self, mock_redis):
        agent = FakeAgent(
            budget="10000",
            spent="0",
            policy={
                "daily_limit": 5000,
                "allowed_categories": ["groceries"],
            },
        )
        req = make_request(amount=Decimal("100"), category="groceries")
        checks, passed = await check_policy(agent, req, mock_redis, "USD", "UTC")
        assert passed is True
        assert all(c.result == "pass" for c in checks)

    async def test_category_fail(self, mock_redis):
        agent = FakeAgent(
            budget="10000",
            policy={"allowed_categories": ["groceries"]},
        )
        req = make_request(amount=Decimal("100"), category="electronics")
        checks, passed = await check_policy(agent, req, mock_redis, "USD", "UTC")
        assert passed is False
        failed = [c for c in checks if c.result == "fail"]
        assert any(c.rule == "category" for c in failed)

    async def test_budget_fail(self, mock_redis):
        agent = FakeAgent(budget="100", spent="90")
        req = make_request(amount=Decimal("50"))
        checks, passed = await check_policy(agent, req, mock_redis, "USD", "UTC")
        assert passed is False
        failed = [c for c in checks if c.result == "fail"]
        assert any(c.rule == "budget" for c in failed)

    async def test_paused_agent_fails(self, mock_redis):
        agent = FakeAgent(status="paused", budget="10000")
        req = make_request()
        checks, passed = await check_policy(agent, req, mock_redis, "USD", "UTC")
        assert passed is False


# ---------------------------------------------------------------------------
# Auto-approve
# ---------------------------------------------------------------------------


class TestAutoApprove:
    def test_enabled_within_limits(self):
        policy = Policy(
            auto_approve={
                "enabled": True,
                "max_amount": 500,
                "categories": ["groceries"],
            }
        )
        req = make_request(amount=Decimal("300"), category="groceries")
        assert should_auto_approve(req, policy) is True

    def test_amount_too_high(self):
        policy = Policy(
            auto_approve={
                "enabled": True,
                "max_amount": 500,
                "categories": ["groceries"],
            }
        )
        req = make_request(amount=Decimal("600"), category="groceries")
        assert should_auto_approve(req, policy) is False

    def test_wrong_category(self):
        policy = Policy(
            auto_approve={
                "enabled": True,
                "max_amount": 500,
                "categories": ["groceries"],
            }
        )
        req = make_request(amount=Decimal("100"), category="taxi")
        assert should_auto_approve(req, policy) is False

    def test_disabled(self):
        policy = Policy(auto_approve={"enabled": False})
        req = make_request()
        assert should_auto_approve(req, policy) is False

    def test_no_auto_approve(self):
        policy = Policy()
        req = make_request()
        assert should_auto_approve(req, policy) is False

    def test_no_category_restriction(self):
        policy = Policy(auto_approve={"enabled": True, "max_amount": 500})
        req = make_request(amount=Decimal("100"), category="electronics")
        assert should_auto_approve(req, policy) is True

    def test_no_amount_restriction(self):
        policy = Policy(auto_approve={"enabled": True, "categories": ["groceries"]})
        req = make_request(amount=Decimal("99999"), category="groceries")
        assert should_auto_approve(req, policy) is True


# ---------------------------------------------------------------------------
# Schedule overrides
# ---------------------------------------------------------------------------


class TestCheckScheduleOverrides:
    @patch("app.services.policy_engine.datetime")
    def test_override_deny(self, mock_dt):
        """Lines 81-88: override with deny=True returns fail."""
        # Wednesday
        mock_dt.now.return_value = datetime(2026, 3, 18, 14, 0, tzinfo=timezone.utc)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        policy = Policy(
            schedule=Schedule(
                timezone="UTC",
                default={"allow": "07:00-23:00"},
                overrides=[
                    ScheduleOverride(days=["wed"], deny=True),
                ],
            )
        )
        r = _check_schedule(policy, "UTC")
        assert r.result == "fail"
        assert "denied" in r.detail.lower()

    @patch("app.services.policy_engine.datetime")
    def test_override_allow_within(self, mock_dt):
        """Lines 89-90: override with allow window, current time inside."""
        mock_dt.now.return_value = datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        policy = Policy(
            schedule=Schedule(
                timezone="UTC",
                default={"allow": "07:00-23:00"},
                overrides=[
                    ScheduleOverride(days=["wed"], allow="09:00-17:00"),
                ],
            )
        )
        r = _check_schedule(policy, "UTC")
        assert r.result == "pass"

    @patch("app.services.policy_engine.datetime")
    def test_override_allow_outside(self, mock_dt):
        """Override allow window, current time outside."""
        mock_dt.now.return_value = datetime(2026, 3, 18, 20, 0, tzinfo=timezone.utc)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        policy = Policy(
            schedule=Schedule(
                timezone="UTC",
                default={"allow": "07:00-23:00"},
                overrides=[
                    ScheduleOverride(days=["wed"], allow="09:00-17:00"),
                ],
            )
        )
        r = _check_schedule(policy, "UTC")
        assert r.result == "fail"

    @patch("app.services.policy_engine.datetime")
    def test_schedule_no_default_no_override_match(self, mock_dt):
        """Line 96: schedule exists but no default allow and no matching override."""
        mock_dt.now.return_value = datetime(2026, 3, 18, 14, 0, tzinfo=timezone.utc)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        policy = Policy(
            schedule=Schedule(
                timezone="UTC",
                default={},
                overrides=[
                    ScheduleOverride(days=["mon"], deny=True),  # different day
                ],
            )
        )
        r = _check_schedule(policy, "UTC")
        assert r.result == "pass"
        assert "no time restriction" in r.detail.lower()


# ---------------------------------------------------------------------------
# Time window edge cases
# ---------------------------------------------------------------------------


class TestCheckTimeWindow:
    def test_overnight_window_in_range(self):
        """Line 116: overnight window like 22:00-06:00, time at 23:00."""
        now = datetime(2026, 3, 18, 23, 0, tzinfo=timezone.utc)
        r = _check_time_window(now, "22:00-06:00")
        assert r.result == "pass"

    def test_overnight_window_in_range_early(self):
        """Overnight window, time at 03:00."""
        now = datetime(2026, 3, 18, 3, 0, tzinfo=timezone.utc)
        r = _check_time_window(now, "22:00-06:00")
        assert r.result == "pass"

    def test_overnight_window_out_of_range(self):
        """Overnight window, time at 12:00 (midday)."""
        now = datetime(2026, 3, 18, 12, 0, tzinfo=timezone.utc)
        r = _check_time_window(now, "22:00-06:00")
        assert r.result == "fail"

    def test_invalid_window_format(self):
        """Lines 131-132: invalid format returns fail (fail-closed)."""
        now = datetime(2026, 3, 18, 12, 0, tzinfo=timezone.utc)
        r = _check_time_window(now, "invalid")
        assert r.result == "fail"
        assert "invalid" in r.detail.lower()


# ---------------------------------------------------------------------------
# Daily limit with schedule overrides
# ---------------------------------------------------------------------------


class TestDailyLimitOverrides:
    @patch("app.services.policy_engine.datetime")
    def test_override_daily_limit(self, mock_dt):
        """Lines 147-155: schedule override with day-specific daily_limit."""
        mock_dt.now.return_value = datetime(2026, 3, 18, 14, 0, tzinfo=timezone.utc)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        policy = Policy(
            daily_limit=Decimal("5000"),
            schedule=Schedule(
                timezone="UTC",
                default={"allow": "07:00-23:00"},
                overrides=[
                    ScheduleOverride(days=["wed"], daily_limit=Decimal("1000")),
                ],
            ),
        )
        # 800 + 500 = 1300 > 1000 override limit
        r = _check_daily_limit(Decimal("500"), Decimal("800"), policy, "UTC")
        assert r.result == "fail"

    @patch("app.services.policy_engine.datetime")
    def test_override_daily_limit_pass(self, mock_dt):
        """Override daily limit — within limit."""
        mock_dt.now.return_value = datetime(2026, 3, 18, 14, 0, tzinfo=timezone.utc)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        policy = Policy(
            daily_limit=Decimal("5000"),
            schedule=Schedule(
                timezone="UTC",
                default={"allow": "07:00-23:00"},
                overrides=[
                    ScheduleOverride(days=["wed"], daily_limit=Decimal("1000")),
                ],
            ),
        )
        r = _check_daily_limit(Decimal("100"), Decimal("200"), policy, "UTC")
        assert r.result == "pass"


# ---------------------------------------------------------------------------
# evaluate_budget_rules
# ---------------------------------------------------------------------------


class FakeAccount:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "acct-1")
        self.account_spent = Decimal(kwargs.get("account_spent", "0"))
        self.account_held = Decimal(kwargs.get("account_held", "0"))


class FakeBudgetRule:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "rule-1")
        self.name = kwargs.get("name", "Test Rule")
        self.is_active = kwargs.get("is_active", True)
        self.priority = kwargs.get("priority", 0)
        self.limit_type = kwargs.get("limit_type", "daily")
        self.limit_amount = Decimal(kwargs.get("limit_amount", "1000"))
        self.days_of_week = kwargs.get("days_of_week")
        self.start_at = kwargs.get("start_at")
        self.end_at = kwargs.get("end_at")


class TestEvaluateBudgetRules:
    async def test_no_applicable_rules_returns_empty(self, mock_redis):
        """Line 309: no applicable rules → empty list, True."""
        account = FakeAccount()
        rule = FakeBudgetRule(is_active=False)
        checks, passed = await evaluate_budget_rules(
            account, Decimal("100"), [rule], mock_redis, "USD", "UTC"
        )
        assert checks == []
        assert passed is True

    async def test_rule_start_at_in_future_skipped(self, mock_redis):
        """Line 300: rule with start_at in the future is skipped."""
        account = FakeAccount()
        rule = FakeBudgetRule(
            start_at=datetime(2099, 1, 1, tzinfo=UTC),
        )
        checks, passed = await evaluate_budget_rules(
            account, Decimal("100"), [rule], mock_redis, "USD", "UTC"
        )
        assert checks == []
        assert passed is True

    async def test_rule_end_at_in_past_skipped(self, mock_redis):
        """Line 302: rule with end_at in the past is skipped."""
        account = FakeAccount()
        rule = FakeBudgetRule(
            end_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
        checks, passed = await evaluate_budget_rules(
            account, Decimal("100"), [rule], mock_redis, "USD", "UTC"
        )
        assert checks == []
        assert passed is True

    async def test_rule_wrong_day_of_week_skipped(self, mock_redis):
        """Line 305: rule with days_of_week not matching today is skipped."""
        account = FakeAccount()
        # Use a day that can never be today (we use all 7 minus today)
        rule = FakeBudgetRule(days_of_week=[])  # empty = never matches
        checks, passed = await evaluate_budget_rules(
            account, Decimal("100"), [rule], mock_redis, "USD", "UTC"
        )
        assert checks == []
        assert passed is True

    async def test_weekly_rule_pass(self, mock_redis):
        """Lines 353-370: weekly rule type — pass."""
        account = FakeAccount()
        rule = FakeBudgetRule(limit_type="weekly", limit_amount="5000")
        checks, passed = await evaluate_budget_rules(
            account, Decimal("100"), [rule], mock_redis, "USD", "UTC"
        )
        assert passed is True
        assert len(checks) == 1
        assert checks[0].result == "pass"
        assert "weekly" in checks[0].detail.lower()

    async def test_weekly_rule_fail(self, mock_redis):
        """Weekly rule type — fail."""
        account = FakeAccount()
        rule = FakeBudgetRule(limit_type="weekly", limit_amount="50")
        # Pre-load spending in redis

        # Set weekly spent high via redis store
        mock_redis._store.clear()
        checks, passed = await evaluate_budget_rules(
            account, Decimal("100"), [rule], mock_redis, "USD", "UTC"
        )
        assert passed is False
        assert checks[0].result == "fail"

    async def test_monthly_rule_pass(self, mock_redis):
        """Lines 371-388: monthly rule type — pass."""
        account = FakeAccount()
        rule = FakeBudgetRule(limit_type="monthly", limit_amount="10000")
        checks, passed = await evaluate_budget_rules(
            account, Decimal("100"), [rule], mock_redis, "USD", "UTC"
        )
        assert passed is True
        assert len(checks) == 1
        assert checks[0].result == "pass"
        assert "monthly" in checks[0].detail.lower()

    async def test_monthly_rule_fail(self, mock_redis):
        """Monthly rule type — fail."""
        account = FakeAccount()
        rule = FakeBudgetRule(limit_type="monthly", limit_amount="50")
        checks, passed = await evaluate_budget_rules(
            account, Decimal("100"), [rule], mock_redis, "USD", "UTC"
        )
        assert passed is False
        assert checks[0].result == "fail"

    async def test_total_rule_pass(self, mock_redis):
        """Lines 389-412: total rule type without time window — pass."""
        account = FakeAccount(account_spent="100", account_held="0")
        rule = FakeBudgetRule(limit_type="total", limit_amount="5000")
        checks, passed = await evaluate_budget_rules(
            account, Decimal("100"), [rule], mock_redis, "USD", "UTC"
        )
        assert passed is True
        assert checks[0].result == "pass"
        assert "total" in checks[0].detail.lower()

    async def test_total_rule_fail(self, mock_redis):
        """Total rule type — fail."""
        account = FakeAccount(account_spent="4950", account_held="0")
        rule = FakeBudgetRule(limit_type="total", limit_amount="5000")
        checks, passed = await evaluate_budget_rules(
            account, Decimal("100"), [rule], mock_redis, "USD", "UTC"
        )
        assert passed is False
        assert checks[0].result == "fail"

    async def test_total_rule_temporal_uses_redis(self, mock_redis):
        """Lines 391-394: total rule with start_at and end_at uses Redis counters."""
        account = FakeAccount(account_spent="0", account_held="0")
        rule = FakeBudgetRule(
            limit_type="total",
            limit_amount="500",
            start_at=datetime(2020, 1, 1, tzinfo=UTC),
            end_at=datetime(2099, 12, 31, tzinfo=UTC),
        )
        checks, passed = await evaluate_budget_rules(
            account, Decimal("100"), [rule], mock_redis, "USD", "UTC"
        )
        assert passed is True
        assert checks[0].result == "pass"
