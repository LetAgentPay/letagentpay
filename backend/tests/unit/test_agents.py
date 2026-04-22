from decimal import Decimal


class TestCreateAgent:
    async def test_create_agent(self, auth_client, account):
        resp = await auth_client.post(
            "/api/v1/agents",
            json={"name": "Shopper", "description": "Grocery agent"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Shopper"
        assert data["status"] == "active"
        assert data["budget"] == "0.00"
        assert data["token"].startswith("agt_")

    async def test_create_second_agent(self, auth_client, account, agent):
        resp = await auth_client.post(
            "/api/v1/agents",
            json={"name": "Second Agent"},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Second Agent"

    async def test_create_agent_unauthorized(self, client):
        resp = await client.post("/api/v1/agents", json={"name": "X"})
        assert resp.status_code == 401

    async def test_create_agent_empty_name(self, auth_client, account):
        resp = await auth_client.post("/api/v1/agents", json={"name": ""})
        assert resp.status_code == 422


class TestListAgents:
    async def test_list_agents(self, auth_client, account, agent):
        resp = await auth_client.get("/api/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["agents"]) >= 1
        assert data["agents"][0]["id"] == agent.id

    async def test_list_agents_empty(self, auth_client, account):
        resp = await auth_client.get("/api/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["agents"]) == 0

    async def test_list_agents_unauthorized(self, client):
        resp = await client.get("/api/v1/agents")
        assert resp.status_code == 401


class TestMultipleAgents:
    async def test_create_multiple_agents_same_account(self, auth_client, account):
        """Can create multiple agents on the same account."""
        resp1 = await auth_client.post(
            "/api/v1/agents",
            json={"name": "Agent One", "description": "First agent"},
        )
        assert resp1.status_code == 201

        resp2 = await auth_client.post(
            "/api/v1/agents",
            json={"name": "Agent Two", "description": "Second agent"},
        )
        assert resp2.status_code == 201

        resp3 = await auth_client.post(
            "/api/v1/agents",
            json={"name": "Agent Three"},
        )
        assert resp3.status_code == 201

        # All three should appear in list
        list_resp = await auth_client.get("/api/v1/agents")
        assert list_resp.status_code == 200
        agents = list_resp.json()["agents"]
        assert len(agents) == 3
        names = [a["name"] for a in agents]
        assert "Agent One" in names
        assert "Agent Two" in names
        assert "Agent Three" in names

    async def test_list_agents_ordered_by_created_at(self, auth_client, account):
        """List agents returns results ordered by created_at ascending."""
        names = ["Alpha", "Beta", "Gamma"]
        for name in names:
            resp = await auth_client.post(
                "/api/v1/agents",
                json={"name": name},
            )
            assert resp.status_code == 201

        list_resp = await auth_client.get("/api/v1/agents")
        assert list_resp.status_code == 200
        agents = list_resp.json()["agents"]
        returned_names = [a["name"] for a in agents]
        assert returned_names == names


class TestGetAgent:
    async def test_get_agent(self, auth_client, account, agent):
        resp = await auth_client.get(f"/api/v1/agents/{agent.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == agent.id
        assert resp.json()["name"] == agent.name

    async def test_get_agent_not_found(self, auth_client, account):
        resp = await auth_client.get("/api/v1/agents/nonexistent-id")
        assert resp.status_code == 404


class TestUpdateAgent:
    async def test_rename_agent(self, auth_client, account, agent):
        resp = await auth_client.patch(
            f"/api/v1/agents/{agent.id}",
            json={"name": "New Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    async def test_update_description(self, auth_client, account, agent):
        resp = await auth_client.patch(
            f"/api/v1/agents/{agent.id}",
            json={"description": "Updated desc"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated desc"

    async def test_rename_empty_rejected(self, auth_client, account, agent):
        resp = await auth_client.patch(
            f"/api/v1/agents/{agent.id}",
            json={"name": ""},
        )
        assert resp.status_code == 422

    async def test_rename_duplicate_rejected(self, auth_client, account, agent):
        await auth_client.post("/api/v1/agents", json={"name": "Other Agent"})
        resp = await auth_client.patch(
            f"/api/v1/agents/{agent.id}",
            json={"name": "Other Agent"},
        )
        assert resp.status_code == 409


class TestUniqueNames:
    async def test_create_duplicate_name_rejected(self, auth_client, account):
        resp1 = await auth_client.post("/api/v1/agents", json={"name": "My Agent"})
        assert resp1.status_code == 201
        resp2 = await auth_client.post("/api/v1/agents", json={"name": "My Agent"})
        assert resp2.status_code == 409

    async def test_same_name_allowed_sandbox_vs_production(self, auth_client, account):
        resp1 = await auth_client.post(
            "/api/v1/agents", json={"name": "Agent X", "is_sandbox": False}
        )
        assert resp1.status_code == 201
        resp2 = await auth_client.post(
            "/api/v1/agents", json={"name": "Agent X", "is_sandbox": True}
        )
        assert resp2.status_code == 201

    async def test_archived_name_can_be_reused(self, auth_client, account):
        resp1 = await auth_client.post("/api/v1/agents", json={"name": "Reusable"})
        assert resp1.status_code == 201
        agent_id = resp1.json()["id"]
        await auth_client.post(f"/api/v1/agents/{agent_id}/archive")
        resp2 = await auth_client.post("/api/v1/agents", json={"name": "Reusable"})
        assert resp2.status_code == 201


class TestPauseResume:
    async def test_pause_agent(self, auth_client, account, agent):
        resp = await auth_client.post(f"/api/v1/agents/{agent.id}/pause")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    async def test_resume_agent(self, auth_client, account, agent):
        await auth_client.post(f"/api/v1/agents/{agent.id}/pause")
        resp = await auth_client.post(f"/api/v1/agents/{agent.id}/resume")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"


class TestArchive:
    async def test_archive_agent(self, auth_client, account, agent):
        resp = await auth_client.post(f"/api/v1/agents/{agent.id}/archive")
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"

    async def test_archive_already_archived(self, auth_client, account, agent):
        await auth_client.post(f"/api/v1/agents/{agent.id}/archive")
        resp = await auth_client.post(f"/api/v1/agents/{agent.id}/archive")
        assert resp.status_code == 400

    async def test_restore_agent(self, auth_client, account, agent):
        await auth_client.post(f"/api/v1/agents/{agent.id}/archive")
        resp = await auth_client.post(f"/api/v1/agents/{agent.id}/restore")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    async def test_restore_not_archived(self, auth_client, account, agent):
        resp = await auth_client.post(f"/api/v1/agents/{agent.id}/restore")
        assert resp.status_code == 400

    async def test_archived_hidden_from_list(self, auth_client, account, agent):
        await auth_client.post(f"/api/v1/agents/{agent.id}/archive")
        resp = await auth_client.get("/api/v1/agents")
        assert resp.status_code == 200
        ids = [a["id"] for a in resp.json()["agents"]]
        assert agent.id not in ids

    async def test_archived_shown_with_flag(self, auth_client, account, agent):
        await auth_client.post(f"/api/v1/agents/{agent.id}/archive")
        resp = await auth_client.get("/api/v1/agents?include_archived=true")
        assert resp.status_code == 200
        ids = [a["id"] for a in resp.json()["agents"]]
        assert agent.id in ids


class TestBudget:
    async def test_topup_budget(self, auth_client, account, agent):
        # Agent fixture has budget=10000
        resp = await auth_client.post(
            f"/api/v1/agents/{agent.id}/budget",
            json={"amount": "100.00"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Additive: 10000 + 100 = 10100
        assert Decimal(data["budget"]) == Decimal("10100.00")
        assert Decimal(data["remaining"]) == Decimal(data["budget"]) - Decimal(
            data["spent"]
        )

    async def test_topup_budget_cumulative(self, auth_client, account, agent):
        resp1 = await auth_client.post(
            f"/api/v1/agents/{agent.id}/budget",
            json={"amount": "100.00"},
        )
        budget_after_first = Decimal(resp1.json()["budget"])
        resp = await auth_client.post(
            f"/api/v1/agents/{agent.id}/budget",
            json={"amount": "50.00"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert Decimal(data["budget"]) == budget_after_first + Decimal("50.00")

    async def test_withdraw_budget(self, auth_client, account, agent):
        # Agent has budget=10000, spent=0 → remaining=10000
        resp = await auth_client.post(
            f"/api/v1/agents/{agent.id}/budget",
            json={"amount": "-50.00"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert Decimal(data["budget"]) == Decimal("9950.00")

    async def test_withdraw_exceeds_remaining(self, auth_client, account, agent):
        # Agent has budget=10000, remaining=10000
        resp = await auth_client.post(
            f"/api/v1/agents/{agent.id}/budget",
            json={"amount": "-20000.00"},
        )
        assert resp.status_code == 400

    async def test_zero_amount_rejected(self, auth_client, account, agent):
        resp = await auth_client.post(
            f"/api/v1/agents/{agent.id}/budget",
            json={"amount": "0"},
        )
        assert resp.status_code == 422

    async def test_agent_response_includes_remaining(self, auth_client, account, agent):
        resp = await auth_client.get(f"/api/v1/agents/{agent.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "remaining" in data
        assert Decimal(data["remaining"]) == Decimal("10000.00")


class TestAutoReplenish:
    async def test_set_auto_replenish(self, auth_client, account, agent):
        resp = await auth_client.put(
            f"/api/v1/agents/{agent.id}/auto-replenish",
            json={"threshold": "10.00", "amount": "50.00"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True
        assert Decimal(data["threshold"]) == Decimal("10.00")
        assert Decimal(data["amount"]) == Decimal("50.00")
        assert data["max_budget"] is None

    async def test_set_auto_replenish_with_cap(self, auth_client, account, agent):
        resp = await auth_client.put(
            f"/api/v1/agents/{agent.id}/auto-replenish",
            json={"threshold": "10.00", "amount": "50.00", "max_budget": "500.00"},
        )
        assert resp.status_code == 200
        assert Decimal(resp.json()["max_budget"]) == Decimal("500.00")

    async def test_disable_auto_replenish(self, auth_client, account, agent):
        await auth_client.put(
            f"/api/v1/agents/{agent.id}/auto-replenish",
            json={"threshold": "10.00", "amount": "50.00"},
        )
        resp = await auth_client.delete(
            f"/api/v1/agents/{agent.id}/auto-replenish",
        )
        assert resp.status_code == 200
        # Verify it's disabled in agent response
        agent_resp = await auth_client.get(f"/api/v1/agents/{agent.id}")
        assert agent_resp.json()["auto_replenish"] is None

    async def test_auto_replenish_shown_in_agent_response(
        self, auth_client, account, agent
    ):
        await auth_client.put(
            f"/api/v1/agents/{agent.id}/auto-replenish",
            json={"threshold": "5.00", "amount": "25.00"},
        )
        resp = await auth_client.get(f"/api/v1/agents/{agent.id}")
        data = resp.json()
        assert data["auto_replenish"] is not None
        assert data["auto_replenish"]["enabled"] is True


class TestRegenerateToken:
    async def test_regenerate_token(self, auth_client, account, agent):
        old_token = agent.token
        resp = await auth_client.post(
            f"/api/v1/agents/{agent.id}/regenerate-token",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["token"].startswith("agt_")
        assert data["token"] != old_token

    async def test_regenerate_token_invalidates_old(
        self, auth_client, client, account, agent
    ):
        old_token = agent.token
        # Regenerate
        resp = await auth_client.post(
            f"/api/v1/agents/{agent.id}/regenerate-token",
        )
        new_token = resp.json()["token"]

        # Old token should not work
        resp_old = await client.get(
            "/api/v1/agent-api/budget",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert resp_old.status_code == 401

        # New token should work
        resp_new = await client.get(
            "/api/v1/agent-api/budget",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        assert resp_new.status_code == 200

    async def test_regenerate_token_unauthorized(self, client, agent):
        resp = await client.post(
            f"/api/v1/agents/{agent.id}/regenerate-token",
        )
        assert resp.status_code == 401

    async def test_regenerate_token_not_found(self, auth_client, account):
        resp = await auth_client.post(
            "/api/v1/agents/nonexistent-id/regenerate-token",
        )
        assert resp.status_code == 404

    async def test_token_masked_in_get(self, auth_client, account, agent):
        """GET agent should return masked token, not plaintext."""
        resp = await auth_client.get(f"/api/v1/agents/{agent.id}")
        assert resp.status_code == 200
        assert resp.json()["token"] == "agt_••••••••••••"

    async def test_token_shown_on_create(self, auth_client, account):
        """POST create agent should return real token (show once)."""
        resp = await auth_client.post(
            "/api/v1/agents",
            json={"name": "Token Visible Agent"},
        )
        assert resp.status_code == 201
        token = resp.json()["token"]
        assert token.startswith("agt_")
        assert token != "agt_••••••••••••"
