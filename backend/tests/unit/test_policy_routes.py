from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_anthropic_key():
    """Ensure anthropic_api_key is set for all policy tests."""
    with patch("app.routers.policy.settings.anthropic_api_key", "sk-ant-test"):
        yield


class TestGetPolicy:
    """GET /api/v1/agents/{agent_id}/policy"""

    async def test_get_policy(self, auth_client, account, agent):
        resp = await auth_client.get(
            f"/api/v1/agents/{agent.id}/policy",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["policy"] == agent.policy
        assert data["policy_text"] == agent.policy_text

    async def test_get_policy_agent_not_found(self, auth_client, account):
        resp = await auth_client.get(
            "/api/v1/agents/nonexistent-id/policy",
        )
        assert resp.status_code == 404

    async def test_get_policy_unauthorized(self, client, agent):
        resp = await client.get(f"/api/v1/agents/{agent.id}/policy")
        assert resp.status_code == 401


class TestAIPolicyPreview:
    """POST /api/v1/agents/{agent_id}/policy/ai"""

    async def test_ai_policy_preview(self, auth_client, account, agent):
        mock_result = {
            "policy": {
                "daily_limit": 1000,
                "allowed_categories": ["groceries", "food_delivery"],
                "auto_approve": {
                    "enabled": True,
                    "max_amount": 200,
                },
            },
            "explanation": "Daily limit of 1000 with auto-approve under 200",
        }
        with patch(
            "app.routers.policy.convert_text_to_policy",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = await auth_client.post(
                f"/api/v1/agents/{agent.id}/policy/ai",
                json={"message": "Set daily limit 1000, auto-approve under 200"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "policy_preview" in data
        assert data["policy_preview"]["daily_limit"] == 1000
        assert "explanation" in data
        assert "session_id" in data

    async def test_ai_policy_preview_with_chat_history(
        self, auth_client, account, agent
    ):
        mock_result = {
            "policy": {"daily_limit": 500},
            "explanation": "Updated daily limit",
        }
        with patch(
            "app.routers.policy.convert_text_to_policy",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = await auth_client.post(
                f"/api/v1/agents/{agent.id}/policy/ai",
                json={
                    "message": "Make it 500",
                    "chat_history": [
                        {"role": "user", "content": "Set daily limit 1000"},
                        {"role": "assistant", "content": "OK, daily limit set to 1000"},
                    ],
                },
            )
        assert resp.status_code == 200
        assert resp.json()["policy_preview"]["daily_limit"] == 500

    async def test_ai_policy_preview_ai_error(self, auth_client, account, agent):
        with patch(
            "app.routers.policy.convert_text_to_policy",
            new_callable=AsyncMock,
            side_effect=ValueError("AI service unavailable"),
        ):
            resp = await auth_client.post(
                f"/api/v1/agents/{agent.id}/policy/ai",
                json={"message": "Do something"},
            )
        assert resp.status_code == 422
        assert "AI could not generate policy" in resp.json()["detail"]

    async def test_ai_policy_preview_empty_message(self, auth_client, account, agent):
        resp = await auth_client.post(
            f"/api/v1/agents/{agent.id}/policy/ai",
            json={"message": ""},
        )
        assert resp.status_code == 422

    async def test_ai_policy_preview_unauthorized(self, client, agent):
        resp = await client.post(
            f"/api/v1/agents/{agent.id}/policy/ai",
            json={"message": "Set limit 100"},
        )
        assert resp.status_code == 401


class TestConfirmAIPolicy:
    """POST /api/v1/agents/{agent_id}/policy/ai/confirm"""

    async def test_confirm_ai_policy(self, auth_client, account, agent):
        """Create a policy preview first, then confirm it."""
        mock_result = {
            "policy": {
                "daily_limit": 800,
                "allowed_categories": ["groceries"],
            },
            "explanation": "Daily limit 800, groceries only",
        }
        with patch(
            "app.routers.policy.convert_text_to_policy",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            await auth_client.post(
                f"/api/v1/agents/{agent.id}/policy/ai",
                json={"message": "Daily limit 800, groceries only"},
            )

        resp = await auth_client.post(
            f"/api/v1/agents/{agent.id}/policy/ai/confirm",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Policy confirmed"
        assert data["policy"]["daily_limit"] == 800

    async def test_confirm_no_pending_policy(self, auth_client, account, agent):
        """Confirming without a prior preview should fail."""
        resp = await auth_client.post(
            f"/api/v1/agents/{agent.id}/policy/ai/confirm",
        )
        assert resp.status_code == 400
        assert "No pending policy" in resp.json()["detail"]

    async def test_confirm_unauthorized(self, client, agent):
        resp = await client.post(f"/api/v1/agents/{agent.id}/policy/ai/confirm")
        assert resp.status_code == 401


class TestUpdatePolicy:
    """PUT /api/v1/agents/{agent_id}/policy"""

    async def test_update_policy(self, auth_client, account, agent):
        new_policy = {
            "daily_limit": "3000",
            "per_request_limit": "1000",
            "allowed_categories": ["groceries", "electronics"],
        }
        resp = await auth_client.put(
            f"/api/v1/agents/{agent.id}/policy",
            json=new_policy,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Policy updated"
        assert data["policy"]["daily_limit"] == "3000"
        assert "electronics" in data["policy"]["allowed_categories"]

    async def test_update_policy_partial(self, auth_client, account, agent):
        """Updating with only some fields should work."""
        resp = await auth_client.put(
            f"/api/v1/agents/{agent.id}/policy",
            json={"daily_limit": "2000"},
        )
        assert resp.status_code == 200
        assert resp.json()["policy"]["daily_limit"] == "2000"

    async def test_update_policy_agent_not_found(self, auth_client, account):
        resp = await auth_client.put(
            "/api/v1/agents/nonexistent-id/policy",
            json={"daily_limit": "1000"},
        )
        assert resp.status_code == 404

    async def test_update_policy_unauthorized(self, client, agent):
        resp = await client.put(
            f"/api/v1/agents/{agent.id}/policy",
            json={"daily_limit": "1000"},
        )
        assert resp.status_code == 401
