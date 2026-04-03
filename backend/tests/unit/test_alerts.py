"""Tests for Telegram monitoring alerts (health, auth, unhandled exceptions)."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import settings
from tests.conftest import make_jwt


def _mock_healthy_session():
    """Create a mock async_session that simulates successful DB connection."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_factory = MagicMock(return_value=mock_ctx)
    return mock_factory


def _mock_failing_session():
    """Create a mock async_session that simulates DB connection failure."""
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(side_effect=ConnectionError("connection refused"))
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_factory = MagicMock(return_value=mock_ctx)
    return mock_factory


class TestHealthAlerts:
    async def test_healthy_does_not_alert(self, client):
        with (
            patch(
                "app.main.send_alert_notification", new_callable=AsyncMock
            ) as mock_alert,
            patch("app.database.async_session", _mock_healthy_session()),
        ):
            resp = await client.get("/health")

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        mock_alert.assert_not_called()

    async def test_postgres_failure_sends_alert(self, client):
        with (
            patch(
                "app.main.send_alert_notification", new_callable=AsyncMock
            ) as mock_alert,
            patch("app.main._health_alert_cooldown", {}),
            patch("app.database.async_session", _mock_failing_session()),
        ):
            resp = await client.get("/health")

        assert resp.status_code == 503
        assert resp.json()["checks"]["postgres"].startswith("error:")
        mock_alert.assert_called_once()
        assert "postgres" in mock_alert.call_args[0][0].lower()

    async def test_redis_failure_sends_alert(self, client, mock_redis):
        mock_redis.ping = AsyncMock(side_effect=ConnectionError("connection refused"))

        with (
            patch(
                "app.main.send_alert_notification", new_callable=AsyncMock
            ) as mock_alert,
            patch("app.main._health_alert_cooldown", {}),
            patch("app.database.async_session", _mock_healthy_session()),
        ):
            resp = await client.get("/health")

        assert resp.status_code == 503
        assert resp.json()["checks"]["redis"].startswith("error:")
        mock_alert.assert_called_once()
        assert "redis" in mock_alert.call_args[0][0].lower()

    async def test_cooldown_prevents_repeated_alerts(self, client, mock_redis):
        mock_redis.ping = AsyncMock(side_effect=ConnectionError("down"))

        cooldown = {"redis": time.monotonic()}

        with (
            patch(
                "app.main.send_alert_notification", new_callable=AsyncMock
            ) as mock_alert,
            patch("app.main._health_alert_cooldown", cooldown),
            patch("app.database.async_session", _mock_healthy_session()),
        ):
            await client.get("/health")

        mock_alert.assert_not_called()

    async def test_cooldown_allows_alert_after_interval(self, client, mock_redis):
        mock_redis.ping = AsyncMock(side_effect=ConnectionError("down"))

        cooldown = {"redis": time.monotonic() - 360}

        with (
            patch(
                "app.main.send_alert_notification", new_callable=AsyncMock
            ) as mock_alert,
            patch("app.main._health_alert_cooldown", cooldown),
            patch("app.database.async_session", _mock_healthy_session()),
        ):
            await client.get("/health")

        mock_alert.assert_called_once()

    async def test_both_services_down_sends_two_alerts(self, client, mock_redis):
        mock_redis.ping = AsyncMock(side_effect=ConnectionError("redis down"))

        with (
            patch(
                "app.main.send_alert_notification", new_callable=AsyncMock
            ) as mock_alert,
            patch("app.main._health_alert_cooldown", {}),
            patch("app.database.async_session", _mock_failing_session()),
        ):
            resp = await client.get("/health")

        assert resp.status_code == 503
        assert mock_alert.call_count == 2
        alert_texts = [call[0][0].lower() for call in mock_alert.call_args_list]
        assert any("postgres" in t for t in alert_texts)
        assert any("redis" in t for t in alert_texts)


class TestAuthAlerts:
    async def test_invalid_jwt_sends_alert(self, client):
        client.cookies.set("access_token", "invalid.jwt.token")

        with patch("app.dependencies._fire_auth_alert") as mock_alert:
            resp = await client.get("/api/v1/me")

        assert resp.status_code == 401
        mock_alert.assert_called_once()
        assert "Invalid JWT" in mock_alert.call_args[0][0]
        client.cookies.clear()

    async def test_missing_account_sends_alert(self, client):
        token = make_jwt("nonexistent-account-id")
        client.cookies.set("access_token", token)

        with patch("app.dependencies._fire_auth_alert") as mock_alert:
            resp = await client.get("/api/v1/me")

        assert resp.status_code == 401
        mock_alert.assert_called_once()
        assert "missing account" in mock_alert.call_args[0][0]
        client.cookies.clear()

    async def test_invalid_agent_token_sends_alert(self, client):
        with patch("app.dependencies._fire_auth_alert") as mock_alert:
            resp = await client.post(
                "/api/v1/agent-api/requests",
                headers={"Authorization": "Bearer agt_invalid_token_12345"},
                json={
                    "amount": 100,
                    "currency": "USD",
                    "category": "test",
                    "description": "test",
                },
            )

        assert resp.status_code == 401
        mock_alert.assert_called_once()
        alert_text = mock_alert.call_args[0][0]
        assert "Invalid agent token" in alert_text
        assert "agt_inva..." in alert_text

    async def test_valid_jwt_does_not_alert(self, auth_client):
        with patch("app.dependencies._fire_auth_alert") as mock_alert:
            resp = await auth_client.get("/api/v1/me")

        assert resp.status_code == 200
        mock_alert.assert_not_called()

    async def test_valid_agent_token_does_not_alert(self, client, agent):
        with patch("app.dependencies._fire_auth_alert") as mock_alert:
            resp = await client.post(
                "/api/v1/agent-api/requests",
                headers={"Authorization": f"Bearer {agent.token}"},
                json={
                    "amount": 10,
                    "currency": "USD",
                    "category": "groceries",
                    "description": "test",
                },
            )

        assert resp.status_code == 201
        mock_alert.assert_not_called()

    async def test_password_login_failure_sends_alert(self, client):
        with (
            patch.object(settings, "self_hosted", True),
            patch.object(settings, "admin_password", "correct-pass"),
            patch("app.dependencies._fire_auth_alert") as mock_alert,
        ):
            resp = await client.post(
                "/api/v1/auth/login", json={"password": "wrong-pass"}
            )

        assert resp.status_code == 401
        mock_alert.assert_called_once()
        assert "Failed password login" in mock_alert.call_args[0][0]

    async def test_password_login_success_does_not_alert(self, client, db):
        with (
            patch.object(settings, "self_hosted", True),
            patch.object(settings, "admin_password", "correct-pass"),
            patch("app.dependencies._fire_auth_alert") as mock_alert,
        ):
            resp = await client.post(
                "/api/v1/auth/login", json={"password": "correct-pass"}
            )

        assert resp.status_code == 200
        mock_alert.assert_not_called()

    async def test_no_cookie_does_not_alert(self, client):
        """Missing cookie is normal (unauthenticated request), should not alert."""
        with patch("app.dependencies._fire_auth_alert") as mock_alert:
            resp = await client.get("/api/v1/me")

        assert resp.status_code == 401
        mock_alert.assert_not_called()


class TestUnhandledExceptionAlert:
    async def test_unhandled_exception_sends_alert(self, client, account):
        token = make_jwt(account.id, account.email)
        client.cookies.set("access_token", token)

        with (
            patch(
                "app.main.send_alert_notification", new_callable=AsyncMock
            ) as mock_alert,
            patch(
                "app.routers.me._account_response",
                side_effect=RuntimeError("unexpected crash"),
            ),
        ):
            resp = await client.get("/api/v1/me")

        assert resp.status_code == 500
        assert resp.json()["detail"] == "Internal server error"
        mock_alert.assert_called_once()
        alert_text = mock_alert.call_args[0][0]
        assert "Unhandled exception" in alert_text
        assert "RuntimeError" in alert_text
        assert "unexpected crash" in alert_text
        client.cookies.clear()
