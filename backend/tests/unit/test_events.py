class TestAgentEvents:
    """GET /api/v1/agents/{agent_id}/events (SSE)"""

    async def test_events_agent_not_found(self, auth_client):
        resp = await auth_client.get(
            "/api/v1/agents/nonexistent-id/events",
        )
        assert resp.status_code == 404

    async def test_events_unauthorized(self, client, agent):
        resp = await client.get(f"/api/v1/agents/{agent.id}/events")
        assert resp.status_code == 401
