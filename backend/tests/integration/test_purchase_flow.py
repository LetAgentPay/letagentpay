"""Integration tests for the full purchase request lifecycle.

These tests exercise the complete flow through real routers, services,
and database — only Redis is mocked (dict-based).
"""

from decimal import Decimal

from sqlalchemy import select, update

from app.models import Agent, BudgetRule, PurchaseRequest
from tests.conftest import make_jwt


class TestPurchaseLifecycle:
    """Full flow: create request → approve/reject → confirm."""

    async def test_auto_approve_and_confirm(
        self, client, db, mock_redis, agent, account
    ):
        """Agent creates request → auto-approved → confirmed as completed."""
        token = agent.token
        resp = await client.post(
            "/api/v1/agent-api/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": 100.00,
                "category": "groceries",
                "merchant_name": "TestMart",
                "description": "Weekly groceries",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "auto_approved"
        assert data["auto_approved"] is True
        request_id = data["request_id"]

        # Verify budget was deducted
        budget_resp = await client.get(
            "/api/v1/agent-api/budget",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert budget_resp.status_code == 200
        budget = budget_resp.json()
        assert Decimal(budget["spent"]) == Decimal("100.00")

        # Confirm purchase
        confirm_resp = await client.post(
            f"/api/v1/agent-api/requests/{request_id}/confirm",
            headers={"Authorization": f"Bearer {token}"},
            json={"success": True, "actual_amount": 95.50},
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "completed"

        # Verify budget adjusted for actual amount
        budget_resp2 = await client.get(
            "/api/v1/agent-api/budget",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert Decimal(budget_resp2.json()["spent"]) == Decimal("95.50")

    async def test_pending_then_manual_approve(
        self, client, db, mock_redis, agent, account
    ):
        """Request exceeds auto-approve limit → pending → human approves."""
        token = agent.token
        jwt = make_jwt(account.id, account.email)
        client.cookies.set("access_token", jwt)

        # Create request above auto-approve threshold (500)
        resp = await client.post(
            "/api/v1/agent-api/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": 800.00,
                "category": "groceries",
                "merchant_name": "BigStore",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        request_id = data["request_id"]

        # Verify hold was placed
        await db.refresh(agent)
        assert agent.held == Decimal("800.00")

        # Human approves via dashboard
        approve_resp = await client.post(
            f"/api/v1/requests/{request_id}/approve",
        )
        assert approve_resp.status_code == 200

        # Verify status changed and hold released
        status_resp = await client.get(
            f"/api/v1/agent-api/requests/{request_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status_resp.json()["status"] == "approved"

        await db.refresh(agent)
        assert agent.held == Decimal("0.00")
        assert agent.spent == Decimal("800.00")

        client.cookies.clear()

    async def test_pending_then_reject(self, client, db, mock_redis, agent, account):
        """Request pending → human rejects → hold released."""
        token = agent.token
        jwt = make_jwt(account.id, account.email)
        client.cookies.set("access_token", jwt)

        resp = await client.post(
            "/api/v1/agent-api/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={"amount": 1000.00, "category": "groceries"},
        )
        assert resp.status_code == 201
        request_id = resp.json()["request_id"]
        assert resp.json()["status"] == "pending"

        # Reject
        reject_resp = await client.post(
            f"/api/v1/requests/{request_id}/reject",
        )
        assert reject_resp.status_code == 200

        await db.refresh(agent)
        assert agent.held == Decimal("0.00")
        assert agent.spent == Decimal("0.00")

        client.cookies.clear()

    async def test_policy_rejection_blocked_category(
        self, client, db, mock_redis, agent, account
    ):
        """Request with category not in allowed_categories → rejected immediately."""
        token = agent.token
        resp = await client.post(
            "/api/v1/agent-api/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={"amount": 50.00, "category": "electronics"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["auto_approved"] is False

        # No hold should be placed
        await db.refresh(agent)
        assert agent.held == Decimal("0.00")
        assert agent.spent == Decimal("0.00")

    async def test_budget_exhaustion(self, client, db, mock_redis, agent, account):
        """Request exceeding remaining budget → rejected."""
        token = agent.token

        # Set budget to almost spent
        await db.execute(
            update(Agent).where(Agent.id == agent.id).values(spent=Decimal("9900.00"))
        )
        await db.commit()

        resp = await client.post(
            "/api/v1/agent-api/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={"amount": 200.00, "category": "groceries"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "rejected"

        checks = data["policy_check"]["checks"]
        budget_check = next(c for c in checks if c["rule"] == "budget")
        assert budget_check["result"] == "fail"

    async def test_confirm_failed_purchase_refunds(
        self, client, db, mock_redis, agent, account
    ):
        """Auto-approved → confirmed as failed → spent refunded."""
        token = agent.token
        resp = await client.post(
            "/api/v1/agent-api/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={"amount": 200.00, "category": "groceries"},
        )
        request_id = resp.json()["request_id"]
        assert resp.json()["status"] == "auto_approved"

        # Confirm as failed
        confirm_resp = await client.post(
            f"/api/v1/agent-api/requests/{request_id}/confirm",
            headers={"Authorization": f"Bearer {token}"},
            json={"success": False},
        )
        assert confirm_resp.json()["status"] == "failed"

        # Verify refund
        budget_resp = await client.get(
            "/api/v1/agent-api/budget",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert Decimal(budget_resp.json()["spent"]) == Decimal("0.00")


class TestAccountBudgetRulesIntegration:
    """Budget rules block requests at account level."""

    async def test_daily_budget_rule_blocks_request(
        self, client, db, mock_redis, agent, account
    ):
        """Account daily limit of 300 → second 200 request blocked."""
        token = agent.token

        # Create account-level daily rule
        rule = BudgetRule(
            account_id=account.id,
            name="Daily limit",
            limit_type="daily",
            limit_amount=Decimal("300.00"),
            priority=0,
        )
        db.add(rule)
        await db.commit()

        # First request: 200 auto-approved
        resp1 = await client.post(
            "/api/v1/agent-api/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={"amount": 200.00, "category": "groceries"},
        )
        assert resp1.json()["status"] == "auto_approved"

        # Second request: 200 would exceed daily 300 → rejected
        resp2 = await client.post(
            "/api/v1/agent-api/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={"amount": 200.00, "category": "groceries"},
        )
        assert resp2.json()["status"] == "rejected"
        checks = resp2.json()["policy_check"]["checks"]
        account_check = next((c for c in checks if "account_budget" in c["rule"]), None)
        assert account_check is not None
        assert account_check["result"] == "fail"


class TestMultiRequestConcurrency:
    """Test that sequential requests maintain consistent state."""

    async def test_multiple_pending_requests_accumulate_holds(
        self, client, db, mock_redis, agent, account
    ):
        """Multiple pending requests each hold funds, reducing available budget."""
        token = agent.token

        # Disable auto-approve by setting max_amount to 0
        agent.policy = {
            "daily_limit": 50000,
            "per_request_limit": 5000,
            "allowed_categories": ["groceries"],
            "auto_approve": {"enabled": True, "max_amount": 0},
        }
        await db.commit()

        amounts = [1000, 1500, 2000]
        request_ids = []
        for amount in amounts:
            resp = await client.post(
                "/api/v1/agent-api/requests",
                headers={"Authorization": f"Bearer {token}"},
                json={"amount": amount, "category": "groceries"},
            )
            assert resp.status_code == 201
            assert resp.json()["status"] == "pending"
            request_ids.append(resp.json()["request_id"])

        # Total held should be sum of all amounts
        await db.refresh(agent)
        assert agent.held == Decimal("4500.00")
        assert agent.spent == Decimal("0.00")

        # Approve first, reject second
        jwt = make_jwt(account.id, account.email)
        client.cookies.set("access_token", jwt)

        await client.post(f"/api/v1/requests/{request_ids[0]}/approve")
        await client.post(f"/api/v1/requests/{request_ids[1]}/reject")

        await db.refresh(agent)
        assert agent.spent == Decimal("1000.00")
        assert agent.held == Decimal("2000.00")  # only third request still pending

        client.cookies.clear()


class TestIdempotency:
    """Idempotency key prevents duplicate requests."""

    async def test_same_idempotency_key_returns_cached(
        self, client, db, mock_redis, agent, account
    ):
        token = agent.token
        headers = {
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "unique-key-123",
        }
        body = {"amount": 100.00, "category": "groceries"}

        resp1 = await client.post(
            "/api/v1/agent-api/requests", headers=headers, json=body
        )
        resp2 = await client.post(
            "/api/v1/agent-api/requests", headers=headers, json=body
        )

        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["request_id"] == resp2.json()["request_id"]

        # Only one request should exist in DB
        result = await db.execute(
            select(PurchaseRequest).where(PurchaseRequest.agent_id == agent.id)
        )
        assert len(result.scalars().all()) == 1

    async def test_different_idempotency_keys_create_separate(
        self, client, db, mock_redis, agent, account
    ):
        token = agent.token
        body = {"amount": 50.00, "category": "groceries"}

        resp1 = await client.post(
            "/api/v1/agent-api/requests",
            headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "key-a"},
            json=body,
        )
        resp2 = await client.post(
            "/api/v1/agent-api/requests",
            headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "key-b"},
            json=body,
        )

        assert resp1.json()["request_id"] != resp2.json()["request_id"]


class TestCategoryResolution:
    """Category aliases and normalization in real requests."""

    async def test_alias_resolved_to_canonical(
        self, client, db, mock_redis, agent, account
    ):
        """'uber_eats' should resolve to 'food_delivery'."""
        # Update policy to allow food_delivery
        agent.policy = {
            "allowed_categories": ["food_delivery", "groceries"],
            "auto_approve": {"enabled": True, "max_amount": 500},
        }
        await db.commit()

        token = agent.token
        resp = await client.post(
            "/api/v1/agent-api/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={"amount": 30.00, "category": "uber_eats"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["category"] == "food_delivery"
        assert data["original_category"] == "uber_eats"

    async def test_canonical_category_no_original(
        self, client, db, mock_redis, agent, account
    ):
        token = agent.token
        resp = await client.post(
            "/api/v1/agent-api/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={"amount": 30.00, "category": "groceries"},
        )
        data = resp.json()
        assert data["category"] == "groceries"
        assert data["original_category"] is None
