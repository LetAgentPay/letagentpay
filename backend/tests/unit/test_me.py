class TestGetProfile:
    async def test_get_profile(self, auth_client, account):
        resp = await auth_client.get("/api/v1/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == account.email
        assert data["currency"] == "USD"
        assert data["timezone"] == "America/New_York"
        assert data["plan"] == "free"

    async def test_get_profile_unauthorized(self, client):
        resp = await client.get("/api/v1/me")
        assert resp.status_code == 401

    async def test_get_profile_invalid_jwt(self, client):
        resp = await client.get("/api/v1/me", cookies={"access_token": "garbage"})
        assert resp.status_code == 401


class TestUpdateProfile:
    async def test_update_name(self, auth_client, account):
        resp = await auth_client.put("/api/v1/me", json={"name": "Max"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Max"

    async def test_update_timezone(self, auth_client, account):
        resp = await auth_client.put("/api/v1/me", json={"timezone": "Europe/Moscow"})
        assert resp.status_code == 200
        assert resp.json()["timezone"] == "Europe/Moscow"

    async def test_update_partial(self, auth_client, account):
        resp = await auth_client.put("/api/v1/me", json={"currency": "EUR"})
        assert resp.status_code == 200
        assert resp.json()["currency"] == "EUR"
        assert resp.json()["email"] == account.email  # unchanged
