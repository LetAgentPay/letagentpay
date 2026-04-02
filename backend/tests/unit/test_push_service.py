"""Tests for push notification service."""

from unittest.mock import MagicMock, patch

from app.services.push import send_push_to_account


class TestSendPushToAccount:
    @patch("app.services.push.settings")
    async def test_no_subscriptions(self, mock_settings, db, account):
        mock_settings.vapid_private_key = "test-key"
        result = await send_push_to_account(db, account.id, "Title", "Body")
        assert result == 0

    @patch("app.services.push.settings")
    async def test_no_vapid_key(self, mock_settings, db, account):
        mock_settings.vapid_private_key = ""
        result = await send_push_to_account(db, account.id, "Title", "Body")
        assert result == 0

    @patch("app.services.push.settings")
    @patch("app.services.push.webpush")
    async def test_successful_delivery(self, mock_webpush, mock_settings, db, account):
        mock_settings.vapid_private_key = "test-key"
        mock_settings.vapid_contact_email = "test@example.com"

        from app.models import PushSubscription

        sub = PushSubscription(
            account_id=account.id,
            endpoint="https://push.example.com/sub/1",
            p256dh="test-p256dh",
            auth="test-auth",
        )
        db.add(sub)
        await db.commit()

        result = await send_push_to_account(db, account.id, "Title", "Body")
        assert result == 1
        mock_webpush.assert_called_once()

    @patch("app.services.push.settings")
    @patch("app.services.push.webpush")
    async def test_expired_subscription_removed(
        self, mock_webpush, mock_settings, db, account
    ):
        from pywebpush import WebPushException

        mock_settings.vapid_private_key = "test-key"
        mock_settings.vapid_contact_email = "test@example.com"

        response_mock = MagicMock()
        response_mock.status_code = 410
        mock_webpush.side_effect = WebPushException("Gone", response=response_mock)

        from app.models import PushSubscription

        sub = PushSubscription(
            account_id=account.id,
            endpoint="https://push.example.com/sub/expired",
            p256dh="test-p256dh",
            auth="test-auth",
        )
        db.add(sub)
        await db.commit()

        result = await send_push_to_account(db, account.id, "Title", "Body")
        assert result == 0

        from sqlalchemy import select

        check = await db.execute(
            select(PushSubscription).where(
                PushSubscription.endpoint == "https://push.example.com/sub/expired"
            )
        )
        assert check.scalar_one_or_none() is None
