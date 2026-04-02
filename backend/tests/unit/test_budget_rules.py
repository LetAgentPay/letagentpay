from decimal import Decimal


class TestBudgetRuleCRUD:
    """Budget rules CRUD endpoints."""

    async def test_create_budget_rule(self, auth_client, account):
        resp = await auth_client.post(
            "/api/v1/me/budget/rules",
            json={
                "name": "Weekday limit",
                "limit_type": "daily",
                "limit_amount": "150.00",
                "priority": 1,
                "days_of_week": [0, 1, 2, 3, 4],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Weekday limit"
        assert data["limit_type"] == "daily"
        assert Decimal(data["limit_amount"]) == Decimal("150.00")
        assert data["days_of_week"] == [0, 1, 2, 3, 4]
        assert data["is_active"] is True
        assert data["priority"] == 1

    async def test_create_total_rule_with_window(self, auth_client, account):
        resp = await auth_client.post(
            "/api/v1/me/budget/rules",
            json={
                "name": "Flight MAD-JFK",
                "limit_type": "total",
                "limit_amount": "100.00",
                "priority": 10,
                "start_at": "2026-03-20T10:00:00",
                "end_at": "2026-03-20T20:00:00",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["limit_type"] == "total"
        assert data["start_at"] is not None
        assert data["end_at"] is not None

    async def test_create_rule_invalid_days(self, auth_client, account):
        resp = await auth_client.post(
            "/api/v1/me/budget/rules",
            json={
                "name": "Bad rule",
                "limit_type": "daily",
                "limit_amount": "100.00",
                "days_of_week": [0, 7],
            },
        )
        assert resp.status_code == 400
        assert "days_of_week" in resp.json()["detail"]

    async def test_create_rule_start_after_end(self, auth_client, account):
        resp = await auth_client.post(
            "/api/v1/me/budget/rules",
            json={
                "name": "Bad window",
                "limit_type": "total",
                "limit_amount": "100.00",
                "start_at": "2026-03-20T20:00:00",
                "end_at": "2026-03-20T10:00:00",
            },
        )
        assert resp.status_code == 400

    async def test_list_budget_rules(self, auth_client, account, budget_rule_daily):
        resp = await auth_client.get("/api/v1/me/budget/rules")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(r["name"] == "Daily limit" for r in data)

    async def test_update_budget_rule(self, auth_client, account, budget_rule_daily):
        resp = await auth_client.put(
            f"/api/v1/me/budget/rules/{budget_rule_daily.id}",
            json={"limit_amount": "300.00", "is_active": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert Decimal(data["limit_amount"]) == Decimal("300.00")
        assert data["is_active"] is False

    async def test_update_nonexistent_rule(self, auth_client, account):
        resp = await auth_client.put(
            "/api/v1/me/budget/rules/nonexistent-id",
            json={"name": "New name"},
        )
        assert resp.status_code == 404

    async def test_delete_budget_rule(self, auth_client, account, budget_rule_daily):
        resp = await auth_client.delete(
            f"/api/v1/me/budget/rules/{budget_rule_daily.id}",
        )
        assert resp.status_code == 204

        # Verify deleted
        resp2 = await auth_client.get("/api/v1/me/budget/rules")
        assert resp2.status_code == 200
        assert not any(r["id"] == budget_rule_daily.id for r in resp2.json())

    async def test_delete_nonexistent_rule(self, auth_client, account):
        resp = await auth_client.delete(
            "/api/v1/me/budget/rules/nonexistent-id",
        )
        assert resp.status_code == 404

    async def test_unauthorized(self, client):
        resp = await client.get("/api/v1/me/budget/rules")
        assert resp.status_code == 401


class TestAccountBudget:
    """GET /api/v1/me/budget — account budget overview."""

    async def test_get_account_budget(self, auth_client, account, budget_rule_daily):
        resp = await auth_client.get("/api/v1/me/budget")
        assert resp.status_code == 200
        data = resp.json()
        assert "account_spent" in data
        assert "currency" in data
        assert "daily_spent" in data
        assert "weekly_spent" in data
        assert "monthly_spent" in data
        assert "rules" in data
        assert len(data["rules"]) >= 1

    async def test_get_account_budget_empty(self, auth_client, account):
        resp = await auth_client.get("/api/v1/me/budget")
        assert resp.status_code == 200
        data = resp.json()
        assert data["rules"] == []
        assert Decimal(data["account_spent"]) == Decimal("0")


class TestAccountBudgetEnforcement:
    """Account-level budget enforcement in purchase flow."""

    async def test_rejected_by_account_daily_limit(
        self, client, agent, budget_rule_daily, mock_redis
    ):
        """Request exceeding account daily budget should be rejected."""
        # Set daily spent to 150 in Redis (rule limit is 200)
        tz = (
            agent.account.timezone
            if hasattr(agent, "account") and agent.account
            else "America/New_York"
        )
        from datetime import datetime
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo(tz))
        daily_key = (
            f"acct_spent:{agent.account_id}:USD:daily:{now.strftime('%Y-%m-%d')}"
        )
        mock_redis._store[daily_key] = "15000"  # 150.00 in subunits (cents)

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
        assert data["status"] == "rejected"
        assert data["policy_check"]["passed"] is False
        # Should contain an account_budget check that failed
        checks = data["policy_check"]["checks"]
        acct_checks = [c for c in checks if c["rule"].startswith("account_budget:")]
        assert len(acct_checks) >= 1
        assert any(c["result"] == "fail" for c in acct_checks)

    async def test_passes_account_budget(self, client, agent, budget_rule_daily):
        """Request within account daily budget should pass."""
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "50.00",
                "category": "groceries",
                "merchant_name": "Store",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        # Should not be rejected by account budget
        assert data["status"] in ("auto_approved", "pending")


class TestCurrencyValidation:
    """Currency mismatch validation in purchase flow."""

    async def test_currency_mismatch_rejected(self, client, agent):
        """Request with wrong currency should be rejected."""
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "100.00",
                "currency": "EUR",
                "category": "groceries",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 400
        assert "Currency mismatch" in resp.json()["detail"]

    async def test_currency_match_passes(self, client, agent):
        """Request with correct currency should work."""
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "100.00",
                "currency": "USD",
                "category": "groceries",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201

    async def test_no_currency_defaults(self, client, agent):
        """Request without currency should default to account currency."""
        resp = await client.post(
            "/api/v1/agent-api/requests",
            json={
                "amount": "100.00",
                "category": "groceries",
            },
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data.get("currency") == "USD"
