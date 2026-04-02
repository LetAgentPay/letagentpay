"""Tests for push subscription endpoints."""

from unittest.mock import patch


class TestVapidKey:
    async def test_get_vapid_key(self, client):
        with patch("app.routers.push.settings") as mock_settings:
            mock_settings.vapid_public_key = "test-vapid-public-key-123"
            resp = await client.get("/api/v1/push/vapid-key")
        assert resp.status_code == 200
        assert resp.json()["vapid_public_key"] == "test-vapid-public-key-123"

    async def test_get_vapid_key_not_configured(self, client):
        with patch("app.routers.push.settings") as mock_settings:
            mock_settings.vapid_public_key = ""
            resp = await client.get("/api/v1/push/vapid-key")
        assert resp.status_code == 404


class TestSubscribe:
    async def test_subscribe(self, auth_client, account, db):
        resp = await auth_client.post(
            "/api/v1/push/subscribe",
            json={
                "endpoint": "https://push.example.com/sub/abc",
                "p256dh": "test-p256dh-key",
                "auth": "test-auth-key",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["message"] == "Subscribed"

        from sqlalchemy import select

        from app.models import PushSubscription

        result = await db.execute(
            select(PushSubscription).where(PushSubscription.account_id == account.id)
        )
        sub = result.scalar_one()
        assert sub.endpoint == "https://push.example.com/sub/abc"
        assert sub.p256dh == "test-p256dh-key"

    async def test_subscribe_upsert(self, auth_client, account, db):
        endpoint = "https://push.example.com/sub/dup"
        await auth_client.post(
            "/api/v1/push/subscribe",
            json={"endpoint": endpoint, "p256dh": "key1", "auth": "auth1"},
        )
        await auth_client.post(
            "/api/v1/push/subscribe",
            json={"endpoint": endpoint, "p256dh": "key2", "auth": "auth2"},
        )

        from sqlalchemy import select

        from app.models import PushSubscription

        result = await db.execute(
            select(PushSubscription).where(PushSubscription.endpoint == endpoint)
        )
        subs = result.scalars().all()
        assert len(subs) == 1
        assert subs[0].p256dh == "key2"

    async def test_subscribe_unauthorized(self, client):
        resp = await client.post(
            "/api/v1/push/subscribe",
            json={
                "endpoint": "https://push.example.com/sub/x",
                "p256dh": "k",
                "auth": "a",
            },
        )
        assert resp.status_code == 401


class TestUnsubscribe:
    async def test_unsubscribe(self, auth_client, account, db):
        endpoint = "https://push.example.com/sub/del"
        await auth_client.post(
            "/api/v1/push/subscribe",
            json={"endpoint": endpoint, "p256dh": "k", "auth": "a"},
        )
        resp = await auth_client.request(
            "DELETE",
            "/api/v1/push/subscribe",
            json={"endpoint": endpoint, "p256dh": "k", "auth": "a"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Unsubscribed"

    async def test_unsubscribe_not_found(self, auth_client, account):
        resp = await auth_client.request(
            "DELETE",
            "/api/v1/push/subscribe",
            json={
                "endpoint": "https://nonexistent.example.com",
                "p256dh": "k",
                "auth": "a",
            },
        )
        assert resp.status_code == 404
