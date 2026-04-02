"""Tests for fund holding (reservation) on pending requests."""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from app.models import Agent, PurchaseRequest
from app.utils import utcnow


class TestHoldOnPending:
    """When a request goes to pending, funds should be held."""

    async def test_pending_request_holds_funds(self, auth_client, agent, db):
        """Auto-approve is off for food_delivery category but policy passes.
        Request should go to pending and hold funds."""
        resp = await auth_client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": 200,
                "category": "food_delivery",
                "merchant_name": "DoorDash",
                "description": "Dinner",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"

        # Verify agent.held was incremented
        result = await db.execute(select(Agent).where(Agent.id == agent.id))
        refreshed_agent = result.scalar_one()
        assert refreshed_agent.held == Decimal("200.00")
        assert refreshed_agent.spent == Decimal("0")  # Not spent yet

    async def test_auto_approved_no_hold(self, auth_client, agent, db):
        """Auto-approved requests should NOT create holds."""
        resp = await auth_client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": 100,
                "category": "groceries",
                "merchant_name": "Whole Foods",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "auto_approved"

        result = await db.execute(select(Agent).where(Agent.id == agent.id))
        refreshed_agent = result.scalar_one()
        assert refreshed_agent.held == Decimal("0")
        assert refreshed_agent.spent == Decimal("100.00")

    async def test_rejected_no_hold(self, auth_client, agent, db):
        """Rejected requests should NOT create holds."""
        # electronics is not in allowed_categories
        resp = await auth_client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": 100,
                "category": "electronics",
                "merchant_name": "Amazon",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "rejected"

        result = await db.execute(select(Agent).where(Agent.id == agent.id))
        refreshed_agent = result.scalar_one()
        assert refreshed_agent.held == Decimal("0")


class TestHoldRelease:
    """Holds should be released on approve, reject, and expiry."""

    async def test_approve_converts_hold_to_spent(
        self, auth_client, agent, pending_request, db
    ):
        resp = await auth_client.post(f"/api/v1/requests/{pending_request.id}/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

        result = await db.execute(select(Agent).where(Agent.id == agent.id))
        refreshed_agent = result.scalar_one()
        assert refreshed_agent.held == Decimal("0")
        assert refreshed_agent.spent == Decimal("1500.00")

    async def test_reject_releases_hold(self, auth_client, agent, pending_request, db):
        resp = await auth_client.post(f"/api/v1/requests/{pending_request.id}/reject")
        assert resp.status_code == 200

        result = await db.execute(select(Agent).where(Agent.id == agent.id))
        refreshed_agent = result.scalar_one()
        assert refreshed_agent.held == Decimal("0")
        assert refreshed_agent.spent == Decimal("0")

    async def test_expired_releases_hold_on_status_check(
        self, auth_client, agent, expired_request, db
    ):
        """When agent polls an expired request, hold should be released."""
        resp = await auth_client.get(
            f"/api/v1/agent-api/requests/{expired_request.id}",
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "expired"

        result = await db.execute(select(Agent).where(Agent.id == agent.id))
        refreshed_agent = result.scalar_one()
        assert refreshed_agent.held == Decimal("0")

    async def test_approve_expired_releases_hold(
        self, auth_client, agent, expired_request, db
    ):
        """Approving an expired request should release hold and return error."""
        resp = await auth_client.post(f"/api/v1/requests/{expired_request.id}/approve")
        assert resp.status_code == 400
        assert "expired" in resp.json()["detail"].lower()

        result = await db.execute(select(Agent).where(Agent.id == agent.id))
        refreshed_agent = result.scalar_one()
        assert refreshed_agent.held == Decimal("0")
        assert refreshed_agent.spent == Decimal("0")


class TestHoldAffectsBudgetCheck:
    """Held funds should reduce available budget for subsequent requests."""

    async def test_held_funds_reduce_budget(self, auth_client, agent, db):
        # Agent budget: 10000, policy: per_request_limit 2000
        # Set agent.held to 9500 (simulating pending requests)
        agent.held = Decimal("9500")
        await db.commit()

        # This 600 request should fail budget check: 10000 - 0 - 9500 = 500 < 600
        resp = await auth_client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": 600,
                "category": "groceries",
                "merchant_name": "Store",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "rejected"
        # Verify it was the budget check that failed
        checks = data["policy_check"]["checks"]
        budget_check = [c for c in checks if c["rule"] == "budget"]
        assert budget_check[0]["result"] == "fail"


class TestBudgetResponseIncludesHeld:
    """GET /budget should include held amount."""

    async def test_budget_response_has_held(self, auth_client, agent, db):
        agent.held = Decimal("500")
        await db.commit()

        resp = await auth_client.get(
            "/api/v1/agent-api/budget",
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "held" in data
        assert Decimal(data["held"]) == Decimal("500")
        assert Decimal(data["remaining"]) == Decimal("9500")  # 10000 - 0 - 500


class TestConfigurableTimeout:
    """request_expiry_minutes setting on account."""

    async def test_read_expiry_setting(self, auth_client, account):
        resp = await auth_client.get("/api/v1/me")
        assert resp.status_code == 200
        assert resp.json()["request_expiry_minutes"] == 30  # default

    async def test_update_expiry_setting(self, auth_client, account):
        resp = await auth_client.put("/api/v1/me", json={"request_expiry_minutes": 60})
        assert resp.status_code == 200
        assert resp.json()["request_expiry_minutes"] == 60

    async def test_expiry_min_validation(self, auth_client, account):
        resp = await auth_client.put("/api/v1/me", json={"request_expiry_minutes": 2})
        assert resp.status_code == 422  # validation error

    async def test_expiry_max_validation(self, auth_client, account):
        resp = await auth_client.put(
            "/api/v1/me", json={"request_expiry_minutes": 2000}
        )
        assert resp.status_code == 422

    async def test_custom_expiry_used_for_pending(
        self, auth_client, agent, account, db
    ):
        """Pending request should use account's configured timeout."""
        account.request_expiry_minutes = 120
        await db.commit()

        resp = await auth_client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": 200,
                "category": "food_delivery",
                "merchant_name": "Uber Eats",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"

        # Verify the expires_at is ~120 minutes from now
        req_result = await db.execute(
            select(PurchaseRequest).where(PurchaseRequest.id == data["request_id"])
        )
        req = req_result.scalar_one()
        expected_expiry = utcnow() + timedelta(minutes=120)
        # Allow 30 second tolerance
        delta = abs((req.expires_at - expected_expiry).total_seconds())
        assert delta < 30
