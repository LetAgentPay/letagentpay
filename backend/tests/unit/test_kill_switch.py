class TestKillSwitch:
    async def test_toggle_kill_switch_on(self, auth_client, account):
        resp = await auth_client.post(
            "/api/v1/me/kill-switch",
            json={"paused": True},
        )
        assert resp.status_code == 200
        assert resp.json()["all_agents_paused"] is True

    async def test_toggle_kill_switch_off(self, auth_client, account):
        await auth_client.post(
            "/api/v1/me/kill-switch",
            json={"paused": True},
        )
        resp = await auth_client.post(
            "/api/v1/me/kill-switch",
            json={"paused": False},
        )
        assert resp.status_code == 200
        assert resp.json()["all_agents_paused"] is False

    async def test_kill_switch_blocks_purchase(self, auth_client, account, agent, db):
        account.all_agents_paused = True
        await db.commit()

        resp = await auth_client.post(
            "/api/v1/agent-api/requests",
            headers={"Authorization": f"Bearer {agent.token}"},
            json={
                "amount": "10.00",
                "category": "groceries",
                "description": "test",
            },
        )
        assert resp.status_code == 403
        assert "paused by account owner" in resp.json()["detail"]

    async def test_kill_switch_blocks_budget_query(
        self, auth_client, account, agent, db
    ):
        account.all_agents_paused = True
        await db.commit()

        resp = await auth_client.get(
            "/api/v1/agent-api/budget",
            headers={"Authorization": f"Bearer {agent.token}"},
        )
        assert resp.status_code == 403
        assert "paused by account owner" in resp.json()["detail"]

    async def test_kill_switch_off_allows_purchase(
        self, auth_client, account, agent, db
    ):
        account.all_agents_paused = True
        await db.commit()

        account.all_agents_paused = False
        await db.commit()

        resp = await auth_client.post(
            "/api/v1/agent-api/requests",
            headers={"Authorization": f"Bearer {agent.token}"},
            json={
                "amount": "10.00",
                "category": "groceries",
                "description": "test",
            },
        )
        assert resp.status_code in (200, 201)

    async def test_kill_switch_preserves_individual_status(
        self, auth_client, account, agent, db
    ):
        # Pause agent individually
        await auth_client.post(f"/api/v1/agents/{agent.id}/pause")

        # Toggle kill switch on then off
        await auth_client.post(
            "/api/v1/me/kill-switch",
            json={"paused": True},
        )
        await auth_client.post(
            "/api/v1/me/kill-switch",
            json={"paused": False},
        )

        # Agent should still be individually paused
        resp = await auth_client.get(f"/api/v1/agents/{agent.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    async def test_kill_switch_visible_in_profile(self, auth_client, account):
        resp = await auth_client.get("/api/v1/me")
        assert resp.status_code == 200
        assert resp.json()["all_agents_paused"] is False

        await auth_client.post(
            "/api/v1/me/kill-switch",
            json={"paused": True},
        )

        resp = await auth_client.get("/api/v1/me")
        assert resp.status_code == 200
        assert resp.json()["all_agents_paused"] is True

    async def test_kill_switch_unauthorized(self, client):
        resp = await client.post(
            "/api/v1/me/kill-switch",
            json={"paused": True},
        )
        assert resp.status_code == 401
