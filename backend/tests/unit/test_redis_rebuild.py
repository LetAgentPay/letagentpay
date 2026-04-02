"""Tests for Redis rebuild service."""

from datetime import timedelta
from decimal import Decimal

from app.models import BudgetRule, PurchaseRequest
from app.services.redis_rebuild import _rebuild, check_redis_needs_rebuild
from app.services.spending import _to_subunits
from app.utils import utcnow


class TestRebuild:
    async def test_no_agents_returns_zero(self, db, mock_redis):
        result = await _rebuild(db, mock_redis)

        assert result["agents"] == 0
        assert result["keys_set"] == 0

    async def test_no_requests_returns_zero_keys(self, db, mock_redis, agent):
        result = await _rebuild(db, mock_redis)

        assert result["agents"] == 1
        assert result["keys_set"] == 0

    async def test_approved_request_creates_spent_keys(
        self, db, mock_redis, agent, account
    ):
        req = PurchaseRequest(
            agent_id=agent.id,
            amount=Decimal("150.00"),
            category="groceries",
            merchant="Store",
            status="approved",
            policy_check={"passed": True, "checks": []},
            expires_at=utcnow() + timedelta(minutes=30),
        )
        db.add(req)
        await db.commit()

        result = await _rebuild(db, mock_redis)

        assert result["keys_set"] > 0
        # Verify spent keys contain correct subunit amount
        spent_keys = [k for k in mock_redis._store if k.startswith("spent:")]
        assert len(spent_keys) > 0
        for key in spent_keys:
            assert mock_redis._store[key] == str(_to_subunits(Decimal("150.00")))

    async def test_pending_request_creates_hold_keys(
        self, db, mock_redis, agent, account
    ):
        req = PurchaseRequest(
            agent_id=agent.id,
            amount=Decimal("200.00"),
            category="groceries",
            merchant="Store",
            status="pending",
            policy_check={"passed": True, "checks": []},
            expires_at=utcnow() + timedelta(minutes=30),
        )
        db.add(req)
        await db.commit()

        await _rebuild(db, mock_redis)

        hold_keys = [k for k in mock_redis._store if k.startswith("hold:")]
        assert len(hold_keys) > 0
        for key in hold_keys:
            assert mock_redis._store[key] == str(_to_subunits(Decimal("200.00")))

    async def test_account_level_counters_created(self, db, mock_redis, agent, account):
        req = PurchaseRequest(
            agent_id=agent.id,
            amount=Decimal("100.00"),
            category="groceries",
            merchant="Store",
            status="approved",
            policy_check={"passed": True, "checks": []},
            expires_at=utcnow() + timedelta(minutes=30),
        )
        db.add(req)
        await db.commit()

        await _rebuild(db, mock_redis)

        acct_keys = [k for k in mock_redis._store if k.startswith("acct_spent:")]
        assert len(acct_keys) > 0

    async def test_multiple_requests_accumulate(self, db, mock_redis, agent, account):
        for amount in [Decimal("100.00"), Decimal("250.00")]:
            req = PurchaseRequest(
                agent_id=agent.id,
                amount=amount,
                category="groceries",
                merchant="Store",
                status="approved",
                policy_check={"passed": True, "checks": []},
                expires_at=utcnow() + timedelta(minutes=30),
            )
            db.add(req)
        await db.commit()

        await _rebuild(db, mock_redis)

        # Find any spent key for this agent (daily, weekly, or monthly)
        spent_keys = [
            k for k in mock_redis._store if k.startswith(f"spent:{agent.id}:")
        ]
        assert len(spent_keys) > 0
        # All matching keys should have accumulated amount
        expected = str(_to_subunits(Decimal("350.00")))
        for key in spent_keys:
            assert mock_redis._store[key] == expected

    async def test_rejected_request_ignored(self, db, mock_redis, agent, account):
        req = PurchaseRequest(
            agent_id=agent.id,
            amount=Decimal("500.00"),
            category="groceries",
            merchant="Store",
            status="rejected",
            policy_check={"passed": True, "checks": []},
            expires_at=utcnow() + timedelta(minutes=30),
        )
        db.add(req)
        await db.commit()

        result = await _rebuild(db, mock_redis)

        assert result["keys_set"] == 0

    async def test_completed_request_counts_as_spent(
        self, db, mock_redis, agent, account
    ):
        req = PurchaseRequest(
            agent_id=agent.id,
            amount=Decimal("75.00"),
            category="groceries",
            merchant="Store",
            status="completed",
            policy_check={"passed": True, "checks": []},
            expires_at=utcnow() + timedelta(minutes=30),
        )
        db.add(req)
        await db.commit()

        await _rebuild(db, mock_redis)

        spent_keys = [k for k in mock_redis._store if k.startswith("spent:")]
        assert len(spent_keys) > 0

    async def test_auto_approved_counts_as_spent(self, db, mock_redis, agent, account):
        req = PurchaseRequest(
            agent_id=agent.id,
            amount=Decimal("50.00"),
            category="groceries",
            merchant="Store",
            status="auto_approved",
            policy_check={"passed": True, "checks": []},
            expires_at=utcnow() + timedelta(minutes=30),
        )
        db.add(req)
        await db.commit()

        await _rebuild(db, mock_redis)

        spent_keys = [k for k in mock_redis._store if k.startswith("spent:")]
        assert len(spent_keys) > 0

    async def test_creates_time_bucketed_keys(self, db, mock_redis, agent, account):
        """Rebuild creates agent-level and account-level keys in matching time buckets."""
        req = PurchaseRequest(
            agent_id=agent.id,
            amount=Decimal("100.00"),
            category="groceries",
            merchant="Store",
            status="approved",
            policy_check={"passed": True, "checks": []},
            expires_at=utcnow() + timedelta(minutes=30),
        )
        db.add(req)
        await db.commit()

        result = await _rebuild(db, mock_redis)

        # Should create at least some keys (agent + account level)
        assert result["keys_set"] >= 2
        all_keys = list(mock_redis._store.keys())
        # At least one time bucket type should be present
        has_time_bucket = any(
            any(f":{bucket}:" in k for k in all_keys)
            for bucket in ("daily", "weekly", "monthly")
        )
        assert has_time_bucket

    async def test_temporal_budget_rule_counters(self, db, mock_redis, agent, account):
        rule = BudgetRule(
            account_id=account.id,
            name="Q1 limit",
            limit_type="total",
            limit_amount=Decimal("10000.00"),
            start_at=utcnow() - timedelta(days=30),
            end_at=utcnow() + timedelta(days=30),
            priority=0,
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)

        req = PurchaseRequest(
            agent_id=agent.id,
            amount=Decimal("500.00"),
            category="groceries",
            merchant="Store",
            status="approved",
            policy_check={"passed": True, "checks": []},
            expires_at=utcnow() + timedelta(minutes=30),
        )
        db.add(req)
        await db.commit()

        await _rebuild(db, mock_redis)

        rule_keys = [k for k in mock_redis._store if ":rule:" in k]
        assert len(rule_keys) > 0
        rule_key = [k for k in rule_keys if f"rule:{rule.id}" in k][0]
        assert mock_redis._store[rule_key] == str(_to_subunits(Decimal("500.00")))

    async def test_pending_request_with_temporal_rule(
        self, db, mock_redis, agent, account
    ):
        rule = BudgetRule(
            account_id=account.id,
            name="Q1 limit",
            limit_type="total",
            limit_amount=Decimal("10000.00"),
            start_at=utcnow() - timedelta(days=30),
            end_at=utcnow() + timedelta(days=30),
            priority=0,
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)

        req = PurchaseRequest(
            agent_id=agent.id,
            amount=Decimal("300.00"),
            category="groceries",
            merchant="Store",
            status="pending",
            policy_check={"passed": True, "checks": []},
            expires_at=utcnow() + timedelta(minutes=30),
        )
        db.add(req)
        await db.commit()

        await _rebuild(db, mock_redis)

        hold_rule_keys = [
            k for k in mock_redis._store if "acct_hold:" in k and ":rule:" in k
        ]
        assert len(hold_rule_keys) > 0


class TestCheckRedisNeedsRebuild:
    async def test_empty_redis_needs_rebuild(self, mock_redis):
        import app.services.redis_rebuild as rebuild_mod

        original = rebuild_mod.get_redis
        rebuild_mod.get_redis = lambda: mock_redis
        try:
            result = await check_redis_needs_rebuild()
            assert result is True
        finally:
            rebuild_mod.get_redis = original

    async def test_redis_with_spent_keys_no_rebuild(self, mock_redis):
        mock_redis._store["spent:agent-1:USD:daily:2026-04-01"] = "10000"

        import app.services.redis_rebuild as rebuild_mod

        original = rebuild_mod.get_redis
        rebuild_mod.get_redis = lambda: mock_redis
        try:
            result = await check_redis_needs_rebuild()
            assert result is False
        finally:
            rebuild_mod.get_redis = original

    async def test_redis_with_hold_keys_no_rebuild(self, mock_redis):
        mock_redis._store["hold:agent-1:USD:daily:2026-04-01"] = "5000"

        import app.services.redis_rebuild as rebuild_mod

        original = rebuild_mod.get_redis
        rebuild_mod.get_redis = lambda: mock_redis
        try:
            result = await check_redis_needs_rebuild()
            assert result is False
        finally:
            rebuild_mod.get_redis = original
