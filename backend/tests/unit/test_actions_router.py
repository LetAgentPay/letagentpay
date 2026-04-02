"""Tests for action tokens router (HTML responses)."""

import json

from app.services.action_tokens import _PREFIX


class TestActionTokenRouter:
    """Test GET /api/v1/requests/action?token=... endpoint."""

    async def test_approve_returns_html_success(
        self, client, db, mock_redis, pending_request, agent, account
    ):
        token_data = json.dumps(
            {
                "account_id": account.id,
                "request_id": pending_request.id,
                "action": "approve",
                "paired_key": f"{_PREFIX}act_paired",
            }
        )
        mock_redis._store[f"{_PREFIX}act_approve"] = token_data

        resp = await client.get(
            "/api/v1/requests/action", params={"token": "act_approve"}
        )

        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Request Approved" in resp.text
        assert "&#10003;" in resp.text  # checkmark icon

    async def test_reject_returns_html_success(
        self, client, db, mock_redis, pending_request, agent, account
    ):
        token_data = json.dumps(
            {
                "account_id": account.id,
                "request_id": pending_request.id,
                "action": "reject",
                "paired_key": f"{_PREFIX}act_paired",
            }
        )
        mock_redis._store[f"{_PREFIX}act_reject"] = token_data

        resp = await client.get(
            "/api/v1/requests/action", params={"token": "act_reject"}
        )

        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Request Rejected" in resp.text
        assert "&#10003;" in resp.text

    async def test_invalid_token_returns_400_html(self, client, db, mock_redis):
        resp = await client.get(
            "/api/v1/requests/action", params={"token": "act_nonexistent"}
        )

        assert resp.status_code == 400
        assert "text/html" in resp.headers["content-type"]
        assert "Action Failed" in resp.text
        assert "&#10007;" in resp.text  # cross icon
        assert "invalid or has already been used" in resp.text

    async def test_expired_request_returns_400_html(
        self, client, db, mock_redis, expired_request, agent, account
    ):
        token_data = json.dumps(
            {
                "account_id": account.id,
                "request_id": expired_request.id,
                "action": "approve",
                "paired_key": f"{_PREFIX}act_paired",
            }
        )
        mock_redis._store[f"{_PREFIX}act_expired"] = token_data

        resp = await client.get(
            "/api/v1/requests/action", params={"token": "act_expired"}
        )

        assert resp.status_code == 400
        assert "Action Failed" in resp.text
        assert "expired" in resp.text

    async def test_already_approved_returns_400_html(
        self, client, db, mock_redis, pending_request, agent, account
    ):
        pending_request.status = "approved"
        await db.commit()

        token_data = json.dumps(
            {
                "account_id": account.id,
                "request_id": pending_request.id,
                "action": "approve",
                "paired_key": f"{_PREFIX}act_paired",
            }
        )
        mock_redis._store[f"{_PREFIX}act_double"] = token_data

        resp = await client.get(
            "/api/v1/requests/action", params={"token": "act_double"}
        )

        assert resp.status_code == 400
        assert "Action Failed" in resp.text
        assert "already been approved" in resp.text

    async def test_missing_token_param_returns_422(self, client):
        resp = await client.get("/api/v1/requests/action")
        assert resp.status_code == 422

    async def test_html_does_not_contain_raw_user_input(self, client, db, mock_redis):
        """Verify that the token value is not reflected in HTML (XSS prevention)."""
        xss_token = '<script>alert("xss")</script>'
        resp = await client.get("/api/v1/requests/action", params={"token": xss_token})

        assert "<script>" not in resp.text

    async def test_dashboard_link_present(
        self, client, db, mock_redis, pending_request, agent, account
    ):
        token_data = json.dumps(
            {
                "account_id": account.id,
                "request_id": pending_request.id,
                "action": "approve",
                "paired_key": f"{_PREFIX}act_paired",
            }
        )
        mock_redis._store[f"{_PREFIX}act_link"] = token_data

        resp = await client.get("/api/v1/requests/action", params={"token": "act_link"})

        assert "/dashboard" in resp.text
        assert "Open Dashboard" in resp.text
