from decimal import Decimal

from app.models import PurchaseRequest
from app.utils import utcnow


class TestListRequests:
    """GET /api/v1/agents/{agent_id}/requests"""

    async def test_list_requests(self, auth_client, account, agent, pending_request):
        resp = await auth_client.get(
            f"/api/v1/agents/{agent.id}/requests",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["limit"] == 20
        assert data["offset"] == 0
        item = data["items"][0]
        assert "id" in item
        assert "amount" in item
        assert "status" in item

    async def test_list_requests_filter_by_status(
        self, auth_client, account, agent, pending_request
    ):
        resp = await auth_client.get(
            f"/api/v1/agents/{agent.id}/requests?status=pending",
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["status"] == "pending"

    async def test_list_requests_pagination(
        self, auth_client, account, agent, pending_request
    ):
        resp = await auth_client.get(
            f"/api/v1/agents/{agent.id}/requests?limit=1&offset=0",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 1
        assert data["offset"] == 0
        assert len(data["items"]) <= 1

    async def test_list_requests_agent_not_found(self, auth_client, account):
        resp = await auth_client.get(
            "/api/v1/agents/nonexistent-id/requests",
        )
        assert resp.status_code == 404

    async def test_list_requests_unauthorized(self, client, agent):
        resp = await client.get(f"/api/v1/agents/{agent.id}/requests")
        assert resp.status_code == 401

    async def test_list_requests_returns_new_fields(
        self, auth_client, account, agent, db
    ):
        """List requests includes agent_comment, actual_amount, receipt_url, completed_at."""
        now = utcnow()
        req = PurchaseRequest(
            agent_id=agent.id,
            amount=Decimal("250.00"),
            category="groceries",
            merchant="TestMart",
            description="Test purchase",
            agent_comment="Need this ASAP",
            status="completed",
            actual_amount=Decimal("245.00"),
            receipt_url="https://example.com/receipt/1",
            completed_at=now,
            policy_check={"passed": True, "checks": []},
            expires_at=now,
            created_at=now,
        )
        db.add(req)
        await db.commit()

        resp = await auth_client.get(f"/api/v1/agents/{agent.id}/requests")
        assert resp.status_code == 200
        items = resp.json()["items"]
        # Find our request
        item = next(i for i in items if i["id"] == req.id)
        assert item["agent_comment"] == "Need this ASAP"
        assert Decimal(item["actual_amount"]) == Decimal("245.00")
        assert item["receipt_url"] == "https://example.com/receipt/1"
        assert item["completed_at"] is not None


class TestGetRequest:
    """GET /api/v1/requests/{request_id}"""

    async def test_get_request(self, auth_client, account, agent, pending_request):
        resp = await auth_client.get(
            f"/api/v1/requests/{pending_request.id}",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == pending_request.id
        assert data["agent_id"] == agent.id
        assert Decimal(data["amount"]) == pending_request.amount
        assert data["status"] == "pending"
        assert data["policy_check"] is not None

    async def test_get_request_not_found(self, auth_client, account):
        resp = await auth_client.get(
            "/api/v1/requests/nonexistent-id",
        )
        assert resp.status_code == 404

    async def test_get_request_unauthorized(self, client, pending_request):
        resp = await client.get(f"/api/v1/requests/{pending_request.id}")
        assert resp.status_code == 401

    async def test_get_request_returns_new_fields(
        self, auth_client, account, agent, db
    ):
        """Get single request includes agent_comment, actual_amount, receipt_url, completed_at."""
        now = utcnow()
        req = PurchaseRequest(
            agent_id=agent.id,
            amount=Decimal("300.00"),
            category="groceries",
            merchant="BigStore",
            description="Bulk order",
            agent_comment="Weekly restock",
            status="completed",
            actual_amount=Decimal("295.50"),
            receipt_url="https://example.com/receipt/42",
            completed_at=now,
            policy_check={"passed": True, "checks": []},
            expires_at=now,
            created_at=now,
        )
        db.add(req)
        await db.commit()
        await db.refresh(req)

        resp = await auth_client.get(f"/api/v1/requests/{req.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_comment"] == "Weekly restock"
        assert Decimal(data["actual_amount"]) == Decimal("295.50")
        assert data["receipt_url"] == "https://example.com/receipt/42"
        assert data["completed_at"] is not None

    async def test_get_request_null_new_fields(
        self, auth_client, account, agent, pending_request
    ):
        """New fields are null when not set."""
        resp = await auth_client.get(f"/api/v1/requests/{pending_request.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_comment"] is None
        assert data["actual_amount"] is None
        assert data["receipt_url"] is None
        assert data["completed_at"] is None


class TestApproveRequest:
    """POST /api/v1/requests/{request_id}/approve"""

    async def test_approve_pending_request(
        self, auth_client, account, agent, pending_request
    ):
        resp = await auth_client.post(
            f"/api/v1/requests/{pending_request.id}/approve",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["request_id"] == pending_request.id
        assert "budget_remaining" in data

    async def test_approve_already_approved(
        self, auth_client, account, agent, pending_request
    ):
        """Approving an already-approved request should fail."""
        await auth_client.post(
            f"/api/v1/requests/{pending_request.id}/approve",
        )
        resp = await auth_client.post(
            f"/api/v1/requests/{pending_request.id}/approve",
        )
        assert resp.status_code == 400
        assert "already" in resp.json()["detail"]

    async def test_approve_expired_request(
        self, auth_client, account, agent, expired_request
    ):
        """Approving an expired request should fail with 400."""
        resp = await auth_client.post(
            f"/api/v1/requests/{expired_request.id}/approve",
        )
        assert resp.status_code == 400
        assert "expired" in resp.json()["detail"].lower()

    async def test_approve_not_found(self, auth_client, account):
        resp = await auth_client.post(
            "/api/v1/requests/nonexistent-id/approve",
        )
        assert resp.status_code == 404

    async def test_approve_unauthorized(self, client, pending_request):
        resp = await client.post(f"/api/v1/requests/{pending_request.id}/approve")
        assert resp.status_code == 401


class TestRejectRequest:
    """POST /api/v1/requests/{request_id}/reject"""

    async def test_reject_pending_request(
        self, auth_client, account, agent, pending_request
    ):
        resp = await auth_client.post(
            f"/api/v1/requests/{pending_request.id}/reject",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["request_id"] == pending_request.id

    async def test_reject_already_rejected(
        self, auth_client, account, agent, pending_request
    ):
        """Rejecting an already-rejected request should fail."""
        await auth_client.post(
            f"/api/v1/requests/{pending_request.id}/reject",
        )
        resp = await auth_client.post(
            f"/api/v1/requests/{pending_request.id}/reject",
        )
        assert resp.status_code == 400
        assert "already" in resp.json()["detail"]

    async def test_reject_not_found(self, auth_client, account):
        resp = await auth_client.post(
            "/api/v1/requests/nonexistent-id/reject",
        )
        assert resp.status_code == 404

    async def test_reject_unauthorized(self, client, pending_request):
        resp = await client.post(f"/api/v1/requests/{pending_request.id}/reject")
        assert resp.status_code == 401
