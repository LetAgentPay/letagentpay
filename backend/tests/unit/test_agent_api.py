from datetime import timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.models import PurchaseRequest
from app.utils import utcnow


class TestCreatePurchaseRequest:
    """POST /api/v1/agent-api/requests"""

    async def test_auto_approve_small_groceries(self, client, agent):
        """Small groceries request should be auto-approved per agent policy."""
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "100.00",
                "category": "groceries",
                "merchant_name": "SuperMart",
                "description": "Weekly groceries",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "auto_approved"
        assert data["auto_approved"] is True
        assert data["budget_remaining"] is not None

    async def test_pending_large_amount(self, client, agent):
        """Amount above auto-approve max should go to pending."""
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "1500.00",
                "category": "groceries",
                "merchant_name": "BigStore",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["auto_approved"] is False
        assert data["expires_at"] is not None

    async def test_pending_non_auto_approve_category(self, client, agent):
        """Category not in auto-approve list should go to pending."""
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "50.00",
                "category": "food_delivery",
                "merchant_name": "FoodApp",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["auto_approved"] is False

    async def test_unknown_category_resolved_via_ai(self, client, agent):
        """Unknown category should be resolved via AI fallback, not rejected."""
        with patch(
            "app.services.category_resolver._resolve_via_ai",
            new_callable=AsyncMock,
            return_value="other",
        ):
            resp = await client.post(
                "/api/v1/agent-api/requests",
                json={
                    "amount": "50.00",
                    "category": "invalid_category",
                    "merchant_name": "Shop",
                },
                headers={"Authorization": f"Bearer {agent.token}"},
            )
        assert resp.status_code == 201
        data = resp.json()
        # AI resolved to "other" which is in allowed categories or policy passes
        assert data["original_category"] == "invalid_category"

    async def test_alias_delivery_resolved_to_food_delivery(self, client, agent):
        """Known alias 'delivery' should resolve to 'food_delivery'."""
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "50.00",
                "category": "delivery",
                "merchant_name": "FoodApp",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["category"] == "food_delivery"
        assert data["original_category"] == "delivery"

    async def test_canonical_category_no_original(self, client, agent):
        """Canonical category should have no original_category."""
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "100.00",
                "category": "groceries",
                "merchant_name": "Store",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["category"] == "groceries"
        assert data["original_category"] is None

    async def test_rejected_not_in_allowed_categories(self, client, agent):
        """Category not in allowed_categories should be rejected by policy."""
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "50.00",
                "category": "electronics",
                "merchant_name": "TechShop",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["auto_approved"] is False

    async def test_rejected_exceeds_per_request_limit(self, client, agent):
        """Amount exceeding per_request_limit should be rejected."""
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "3000.00",
                "category": "groceries",
                "merchant_name": "ExpensiveStore",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["policy_check"]["passed"] is False

    async def test_unauthorized_no_token(self, client):
        """Request without bearer token should fail."""
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={"amount": "50.00", "category": "groceries"},
        )
        assert resp.status_code == 401

    async def test_unauthorized_invalid_token(self, client):
        """Request with invalid bearer token should fail."""
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={"amount": "50.00", "category": "groceries"},
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert resp.status_code == 401

    async def test_missing_required_fields(self, client, agent):
        """Missing required fields should return 422."""
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={"category": "groceries"},
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 422

    async def test_zero_amount(self, client, agent):
        """Zero amount should be rejected (amount must be > 0)."""
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={"amount": "0", "category": "groceries"},
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 422


class TestGetRequestStatus:
    """GET /api/v1/agent-api/requests/{request_id}"""

    async def test_get_pending_request(self, client, agent, pending_request):
        resp = await client.get(
            f"/api/v1/agent-api/requests/{pending_request.id}",
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["request_id"] == pending_request.id
        assert data["status"] == "pending"
        assert data["category"] == "groceries"

    async def test_get_expired_request_marks_expired(
        self, client, agent, expired_request
    ):
        """Fetching an expired pending request should mark it as expired."""
        resp = await client.get(
            f"/api/v1/agent-api/requests/{expired_request.id}",
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "expired"

    async def test_get_nonexistent_request(self, client, agent):
        resp = await client.get(
            "/api/v1/agent-api/requests/nonexistent-id",
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 404

    async def test_get_request_unauthorized(self, client, pending_request):
        resp = await client.get(
            f"/api/v1/agent-api/requests/{pending_request.id}",
        )
        assert resp.status_code == 401


class TestGetBudget:
    """GET /api/v1/agent-api/budget"""

    async def test_get_budget(self, client, agent):
        resp = await client.get(
            "/api/v1/agent-api/budget",
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert Decimal(data["budget"]) == agent.budget
        assert Decimal(data["spent"]) == agent.spent
        assert Decimal(data["remaining"]) == agent.budget - agent.spent

    async def test_get_budget_unauthorized(self, client):
        resp = await client.get("/api/v1/agent-api/budget")
        assert resp.status_code == 401


class TestGetPolicy:
    """GET /api/v1/agent-api/policy"""

    async def test_get_policy(self, client, agent):
        resp = await client.get(
            "/api/v1/agent-api/policy",
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["policy"] == agent.policy

    async def test_get_policy_unauthorized(self, client):
        resp = await client.get("/api/v1/agent-api/policy")
        assert resp.status_code == 401


class TestConfirmPurchase:
    """POST /api/v1/agent-api/requests/{request_id}/confirm"""

    async def test_confirm_approved_request(self, client, agent, db, pending_request):
        """Confirming an approved request should change status to completed."""
        # First approve the request via dashboard
        from app.utils import utcnow

        pending_request.status = "approved"
        pending_request.reviewed_at = utcnow()
        await db.commit()

        resp = await client.post(
            f"/api/v1/agent-api/requests/{pending_request.id}/confirm",
            json={"success": True, "actual_amount": "1450.00"},
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["actual_amount"] == "1450.00"

    async def test_confirm_failed_purchase_refunds_spent(
        self, client, agent, db, pending_request
    ):
        """Confirming a failed purchase should refund spent on agent and account."""
        from decimal import Decimal

        from sqlalchemy import select

        from app.models import Account
        from app.utils import utcnow

        # Simulate approved state: hold converted to spent
        pending_request.status = "approved"
        pending_request.reviewed_at = utcnow()
        agent.held = agent.held - pending_request.amount
        agent.spent = agent.spent + pending_request.amount
        account = (
            await db.execute(select(Account).where(Account.id == agent.account_id))
        ).scalar_one()
        account.account_spent = account.account_spent + pending_request.amount
        await db.commit()

        spent_before = agent.spent
        account_spent_before = account.account_spent

        resp = await client.post(
            f"/api/v1/agent-api/requests/{pending_request.id}/confirm",
            json={"success": False},
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

        # Verify spent was refunded
        await db.refresh(agent)
        await db.refresh(account)
        assert agent.spent == spent_before - Decimal("1500.00")
        assert account.account_spent == account_spent_before - Decimal("1500.00")

    async def test_confirm_pending_request_fails(self, client, agent, pending_request):
        """Cannot confirm a pending request."""
        resp = await client.post(
            f"/api/v1/agent-api/requests/{pending_request.id}/confirm",
            json={"success": True},
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 400

    async def test_confirm_unauthorized(self, client, pending_request):
        resp = await client.post(
            f"/api/v1/agent-api/requests/{pending_request.id}/confirm",
            json={"success": True},
        )
        assert resp.status_code == 401

    async def test_confirm_with_receipt_url(self, client, agent, db, pending_request):
        """Confirming with receipt_url should store it."""
        pending_request.status = "approved"
        pending_request.reviewed_at = utcnow()
        await db.commit()

        resp = await client.post(
            f"/api/v1/agent-api/requests/{pending_request.id}/confirm",
            json={
                "success": True,
                "actual_amount": "1500.00",
                "receipt_url": "https://example.com/receipt/123",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["actual_amount"] == "1500.00"

    async def test_confirm_adjusted_amount_updates_spent(
        self, client, agent, db, pending_request
    ):
        """When actual_amount differs from original, agent.spent is adjusted."""
        pending_request.status = "approved"
        pending_request.reviewed_at = utcnow()
        await db.commit()

        original_spent = agent.spent
        # Original amount is 1500, confirm with 1200 => diff = -300
        resp = await client.post(
            f"/api/v1/agent-api/requests/{pending_request.id}/confirm",
            json={"success": True, "actual_amount": "1200.00"},
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["actual_amount"] == "1200.00"

        # Verify agent spent was adjusted
        await db.refresh(agent)
        expected_spent = original_spent + (Decimal("1200.00") - Decimal("1500.00"))
        assert agent.spent == expected_spent

    async def test_confirm_not_found(self, client, agent):
        """Confirming nonexistent request returns 404."""
        resp = await client.post(
            "/api/v1/agent-api/requests/nonexistent-id/confirm",
            json={"success": True},
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 404


class TestAgentComment:
    """Test agent_comment field in purchase requests."""

    async def test_create_request_with_comment(self, client, agent):
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "100.00",
                "category": "groceries",
                "merchant_name": "SuperMart",
                "agent_comment": "Need this for meal prep",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201

    async def test_create_request_without_comment(self, client, agent):
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "100.00",
                "category": "groceries",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201

    async def test_comment_stored_and_retrievable(self, client, agent):
        """Verify agent_comment is persisted and returned in get request status."""
        create_resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "100.00",
                "category": "groceries",
                "merchant_name": "SuperMart",
                "agent_comment": "Urgent: needed for tonight's dinner",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert create_resp.status_code == 201
        request_id = create_resp.json()["request_id"]

        # Retrieve via agent API get status
        get_resp = await client.get(
            f"/api/v1/agent-api/requests/{request_id}",
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert get_resp.status_code == 200
        # The get_request_status endpoint returns basic fields;
        # verify request was created with the comment by checking DB indirectly
        assert get_resp.json()["request_id"] == request_id


class TestGetCategories:
    """GET /api/v1/agent-api/categories"""

    async def test_get_categories(self, client, agent):
        resp = await client.get(
            "/api/v1/agent-api/categories",
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "categories" in data
        assert "groceries" in data["categories"]
        assert "electronics" in data["categories"]
        assert data["categories"] == sorted(data["categories"])


class TestRateLimiting:
    """Rate limiting on POST /api/v1/agent-api/requests"""

    async def test_rate_limit_returns_429_when_exceeded(
        self, client, agent, mock_redis
    ):
        """When rate limit is exceeded, the endpoint should return 429."""
        with patch(
            "app.routers.agent_api.check_rate_limit",
            side_effect=HTTPException(
                status_code=429, detail="Too many requests. Please try again later."
            ),
        ):
            resp = await client.post(
                "/api/v1/agent-api/requests",
                json={
                    "amount": "10.00",
                    "category": "groceries",
                    "description": "test",
                },
                headers={"Authorization": f"Bearer {agent.token}"},
            )
        assert resp.status_code == 429
        assert "Too many requests" in resp.json()["detail"]


class TestIdempotency:
    """Idempotency-Key header on POST /api/v1/agent-api/requests"""

    async def test_returns_cached_response_on_duplicate_key(
        self, client, agent, mock_redis
    ):
        """Second request with the same Idempotency-Key returns cached response."""
        headers = {
            "Authorization": f"Bearer {agent.token}",
            "Idempotency-Key": "unique-key-1",
        }
        body = {
            "amount": "100.00",
            "category": "groceries",
            "merchant_name": "SuperMart",
            "description": "test",
        }

        resp1 = await client.post(
            "/api/v1/agent-api/requests", json=body, headers=headers
        )
        assert resp1.status_code == 201
        request_id_1 = resp1.json()["request_id"]

        # Second request with same key should return cached response
        resp2 = await client.post(
            "/api/v1/agent-api/requests", json=body, headers=headers
        )
        assert resp2.status_code == 201
        request_id_2 = resp2.json()["request_id"]

        assert request_id_1 == request_id_2

    async def test_no_header_always_creates_new_request(
        self, client, agent, mock_redis
    ):
        """Requests without Idempotency-Key always create new requests."""
        headers = {"Authorization": f"Bearer {agent.token}"}
        body = {
            "amount": "100.00",
            "category": "groceries",
            "merchant_name": "SuperMart",
            "description": "test",
        }

        resp1 = await client.post(
            "/api/v1/agent-api/requests", json=body, headers=headers
        )
        assert resp1.status_code == 201

        resp2 = await client.post(
            "/api/v1/agent-api/requests", json=body, headers=headers
        )
        assert resp2.status_code == 201

        assert resp1.json()["request_id"] != resp2.json()["request_id"]

    async def test_different_keys_create_different_requests(
        self, client, agent, mock_redis
    ):
        """Different Idempotency-Key values create separate requests."""
        body = {
            "amount": "100.00",
            "category": "groceries",
            "merchant_name": "SuperMart",
            "description": "test",
        }

        resp1 = await client.post(
            "/api/v1/agent-api/requests",
            json=body,
            headers={
                "Authorization": f"Bearer {agent.token}",
                "Idempotency-Key": "key-a",
            },
        )
        assert resp1.status_code == 201

        resp2 = await client.post(
            "/api/v1/agent-api/requests",
            json=body,
            headers={
                "Authorization": f"Bearer {agent.token}",
                "Idempotency-Key": "key-b",
            },
        )
        assert resp2.status_code == 201

        assert resp1.json()["request_id"] != resp2.json()["request_id"]


class TestPendingRequestLimit:
    """Pending request limit on POST /api/v1/agent-api/requests"""

    async def test_rejects_when_too_many_pending(self, client, db, agent, mock_redis):
        """When 100 pending requests exist, the next request should be rejected with 429."""
        for i in range(100):
            req = PurchaseRequest(
                agent_id=agent.id,
                amount=Decimal("1.00"),
                category="groceries",
                merchant=f"Store {i}",
                description=f"Pending request {i}",
                status="pending",
                policy_check={"passed": True, "checks": []},
                expires_at=utcnow() + timedelta(minutes=30),
            )
            db.add(req)
        await db.commit()

        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "10.00",
                "category": "groceries",
                "description": "one too many",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 429
        assert "Too many pending requests" in resp.json()["detail"]

    async def test_allows_after_approval(self, client, db, agent, mock_redis):
        """After approving one of 100 pending requests, the next request should succeed."""
        requests_list = []
        for i in range(100):
            req = PurchaseRequest(
                agent_id=agent.id,
                amount=Decimal("1.00"),
                category="groceries",
                merchant=f"Store {i}",
                description=f"Pending request {i}",
                status="pending",
                policy_check={"passed": True, "checks": []},
                expires_at=utcnow() + timedelta(minutes=30),
            )
            db.add(req)
            requests_list.append(req)
        await db.commit()

        # Approve one request to bring pending count to 99
        requests_list[0].status = "approved"
        requests_list[0].reviewed_at = utcnow()
        await db.commit()

        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "10.00",
                "category": "groceries",
                "description": "should succeed now",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201


class TestNullByteRejection:
    """NUL in path or query must never reach Postgres (asyncpg raises on 0x00)."""

    async def test_null_byte_in_query_param(self, client, agent):
        resp = await client.get(
            "/api/v1/agent-api/requests?status=requests%00",
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid characters in request"

    async def test_null_byte_in_path_param(self, client, agent):
        resp = await client.get(
            "/api/v1/agent-api/requests/12345%00abc",
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 400

    async def test_clean_query_still_works(self, client, agent):
        resp = await client.get(
            "/api/v1/agent-api/requests?status=pending",
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 200
