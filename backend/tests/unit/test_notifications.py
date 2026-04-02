"""Tests for notification channels API."""

import uuid

from app.models import NotificationChannel
from app.utils import utcnow


class TestListChannels:
    async def test_empty_list(self, auth_client):
        resp = await auth_client.get("/api/v1/me/notifications/channels")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_lists_configured_channels(self, auth_client, db, account):
        ch = NotificationChannel(
            id=str(uuid.uuid4()),
            account_id=account.id,
            channel_type="email",
            is_enabled=True,
            priority=10,
            config={},
            verified_at=utcnow(),
            created_at=utcnow(),
        )
        db.add(ch)
        await db.commit()

        resp = await auth_client.get("/api/v1/me/notifications/channels")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["channel_type"] == "email"
        assert data[0]["is_enabled"] is True
        assert data[0]["verified"] is True


class TestUpdateChannel:
    async def test_toggle_channel(self, auth_client, db, account):
        ch = NotificationChannel(
            id=str(uuid.uuid4()),
            account_id=account.id,
            channel_type="email",
            is_enabled=True,
            priority=10,
            config={},
            verified_at=utcnow(),
            created_at=utcnow(),
        )
        db.add(ch)
        await db.commit()

        resp = await auth_client.put(
            "/api/v1/me/notifications/channels/email",
            json={"is_enabled": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_enabled"] is False

    async def test_update_nonexistent_channel(self, auth_client):
        resp = await auth_client.put(
            "/api/v1/me/notifications/channels/slack",
            json={"is_enabled": True},
        )
        assert resp.status_code == 404


class TestDisconnectChannel:
    async def test_disconnect_existing(self, auth_client, db, account):
        ch = NotificationChannel(
            id=str(uuid.uuid4()),
            account_id=account.id,
            channel_type="telegram",
            is_enabled=True,
            priority=0,
            config={"chat_id": 12345},
            verified_at=utcnow(),
            created_at=utcnow(),
        )
        db.add(ch)
        await db.commit()

        resp = await auth_client.delete("/api/v1/me/notifications/channels/telegram")
        assert resp.status_code == 200

        # Verify it's gone
        resp = await auth_client.get("/api/v1/me/notifications/channels")
        assert resp.json() == []

    async def test_disconnect_nonexistent(self, auth_client):
        resp = await auth_client.delete("/api/v1/me/notifications/channels/telegram")
        assert resp.status_code == 404


class TestEnableEmailChannel:
    async def test_enable_creates_channel(self, auth_client, db, account):
        resp = await auth_client.post("/api/v1/me/notifications/channels/email/enable")
        assert resp.status_code == 200
        data = resp.json()
        assert data["channel_type"] == "email"
        assert data["is_enabled"] is True
        assert data["verified"] is True

    async def test_enable_idempotent(self, auth_client, db, account):
        # Create first
        await auth_client.post("/api/v1/me/notifications/channels/email/enable")
        # Enable again
        resp = await auth_client.post("/api/v1/me/notifications/channels/email/enable")
        assert resp.status_code == 200
        assert resp.json()["is_enabled"] is True
