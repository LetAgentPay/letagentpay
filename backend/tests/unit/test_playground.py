"""Tests for the playground (public demo) endpoints."""

from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, Agent
from app.services.playground import PLAYGROUND_POLICY_PRESETS

# Use first preset for deterministic tests
_TEST_PRESET = PLAYGROUND_POLICY_PRESETS[0]


class TestPlaygroundSession:
    """POST /api/v1/playground/session"""

    async def test_create_session_disabled(self, client: AsyncClient):
        """Returns 404 when playground is disabled."""
        with patch("app.routers.playground.settings") as mock_settings:
            mock_settings.playground_enabled = False
            resp = await client.post("/api/v1/playground/session")
        assert resp.status_code == 404

    async def test_create_session_enabled(
        self, client: AsyncClient, db: AsyncSession, mock_redis
    ):
        """Creates a session with a temporary account + agent."""
        with patch("app.routers.playground.settings") as mock_settings:
            mock_settings.playground_enabled = True
            mock_settings.playground_session_ttl_minutes = 15
            mock_settings.playground_max_requests = 20

            with (
                patch("app.services.playground.settings", mock_settings),
                patch(
                    "app.services.playground._pick_random_preset",
                    return_value=_TEST_PRESET,
                ),
            ):
                resp = await client.post("/api/v1/playground/session")

        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert "agent_token" in data
        assert data["agent_token"].startswith("agt_")
        assert float(data["budget"]) == _TEST_PRESET["budget"]
        assert data["agent_name"] == _TEST_PRESET["name"]
        assert data["currency"] == "USD"
        assert data["policy"]["auto_approve"]["enabled"] is True
        assert data["expires_in"] == 900  # 15 * 60
        assert data["max_requests"] == 20

        # Verify DB records created
        result = await db.execute(
            select(Agent).where(Agent.token == data["agent_token"])
        )
        agent = result.scalar_one()
        assert agent.is_sandbox is True
        assert agent.name == _TEST_PRESET["name"]
        assert float(agent.budget) == _TEST_PRESET["budget"]

        # Verify account created
        result = await db.execute(select(Account).where(Account.id == agent.account_id))
        account = result.scalar_one()
        assert "playground.letagentpay.internal" in account.email

    async def test_session_agent_works_with_agent_api(
        self, client: AsyncClient, db: AsyncSession, mock_redis
    ):
        """The playground agent token can be used with standard agent API."""
        with patch("app.routers.playground.settings") as mock_settings:
            mock_settings.playground_enabled = True
            mock_settings.playground_session_ttl_minutes = 15
            mock_settings.playground_max_requests = 20

            with (
                patch("app.services.playground.settings", mock_settings),
                patch(
                    "app.services.playground._pick_random_preset",
                    return_value=_TEST_PRESET,
                ),
            ):
                resp = await client.post("/api/v1/playground/session")

        token = resp.json()["agent_token"]

        # Use the token to get budget
        budget_resp = await client.get(
            "/api/v1/agent-api/budget",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert budget_resp.status_code == 200
        budget_data = budget_resp.json()
        assert float(budget_data["budget"]) == _TEST_PRESET["budget"]

        # Use the token to get categories
        cat_resp = await client.get(
            "/api/v1/agent-api/categories",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cat_resp.status_code == 200
        assert "categories" in cat_resp.json()

    async def test_rate_limit(self, client: AsyncClient, db: AsyncSession, mock_redis):
        """Rate-limits sessions per IP."""
        with patch("app.routers.playground.settings") as mock_settings:
            mock_settings.playground_enabled = True
            mock_settings.playground_session_ttl_minutes = 15
            mock_settings.playground_max_requests = 20

            with patch("app.services.playground.settings", mock_settings):
                # Create 3 sessions (limit)
                for _ in range(3):
                    resp = await client.post("/api/v1/playground/session")
                    assert resp.status_code == 200

                # 4th should be rate-limited
                resp = await client.post("/api/v1/playground/session")
                assert resp.status_code == 429


class TestPlaygroundSessionGet:
    """GET /api/v1/playground/session/{session_id}"""

    async def test_get_nonexistent_session(self, client: AsyncClient, mock_redis):
        """Returns 404 for unknown session."""
        with patch("app.routers.playground.settings") as mock_settings:
            mock_settings.playground_enabled = True

            resp = await client.get("/api/v1/playground/session/nonexistent-id")

        assert resp.status_code == 404

    async def test_get_active_session(
        self, client: AsyncClient, db: AsyncSession, mock_redis
    ):
        """Returns session info for an active session."""
        with patch("app.routers.playground.settings") as mock_settings:
            mock_settings.playground_enabled = True
            mock_settings.playground_session_ttl_minutes = 15
            mock_settings.playground_max_requests = 20

            with (
                patch("app.services.playground.settings", mock_settings),
                patch(
                    "app.services.playground._pick_random_preset",
                    return_value=_TEST_PRESET,
                ),
            ):
                create_resp = await client.post("/api/v1/playground/session")
                session_id = create_resp.json()["session_id"]

                resp = await client.get(f"/api/v1/playground/session/{session_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert "agent_token" in data
