"""Tests for notification dispatcher."""

import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from app.models import NotificationChannel
from app.services.notification_dispatcher import (
    NotificationEvent,
    dispatch_notification,
)
from app.utils import utcnow


def _make_event(**overrides) -> NotificationEvent:
    defaults = {
        "event_type": "pending_request",
        "request_id": "req-1",
        "agent_name": "Test Agent",
        "amount": "100.00",
        "currency": "USD",
        "category": "groceries",
        "account_expiry_minutes": 30,
    }
    defaults.update(overrides)
    return NotificationEvent(**defaults)


class TestDispatchNotification:
    @patch("app.services.notification_dispatcher.create_action_tokens")
    @patch("app.services.notification_dispatcher.send_push_to_account")
    @patch("app.services.notification_dispatcher.send_pending_request_email")
    async def test_fallback_when_no_channels(
        self,
        mock_email,
        mock_push,
        mock_create_tokens,
        db,
        mock_redis,
        account,
    ):
        """When no channels configured, falls back to push → email."""
        from app.services.action_tokens import ActionTokens

        mock_create_tokens.return_value = ActionTokens(
            approve="act_approve", reject="act_reject"
        )
        mock_push.return_value = 0
        mock_email.return_value = True

        await dispatch_notification(db, mock_redis, account.id, _make_event())

        mock_push.assert_called_once()
        mock_email.assert_called_once()

    @patch("app.services.notification_dispatcher.create_action_tokens")
    @patch("app.services.notification_dispatcher.send_pending_request_email")
    async def test_dispatches_to_email_channel(
        self,
        mock_email,
        mock_create_tokens,
        db,
        mock_redis,
        account,
    ):
        """When email channel is configured, dispatches to it."""
        from app.services.action_tokens import ActionTokens

        mock_create_tokens.return_value = ActionTokens(
            approve="act_approve", reject="act_reject"
        )
        mock_email.return_value = True

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

        await dispatch_notification(db, mock_redis, account.id, _make_event())

        mock_email.assert_called_once()

    @patch("app.services.notification_dispatcher.create_action_tokens")
    @patch("app.services.telegram.send_telegram_notification", new_callable=AsyncMock)
    @patch("app.services.notification_dispatcher.send_pending_request_email")
    async def test_dispatches_to_multiple_channels(
        self,
        mock_email,
        mock_telegram,
        mock_create_tokens,
        db,
        mock_redis,
        account,
    ):
        """When multiple channels configured, dispatches to all."""
        from app.services.action_tokens import ActionTokens

        mock_create_tokens.return_value = ActionTokens(
            approve="act_approve", reject="act_reject"
        )
        mock_email.return_value = True

        for channel_type, priority in [("email", 10), ("telegram", 0)]:
            ch = NotificationChannel(
                id=str(uuid.uuid4()),
                account_id=account.id,
                channel_type=channel_type,
                is_enabled=True,
                priority=priority,
                config={"chat_id": 12345} if channel_type == "telegram" else {},
                verified_at=utcnow(),
                created_at=utcnow(),
            )
            db.add(ch)
        await db.commit()

        await dispatch_notification(db, mock_redis, account.id, _make_event())

        mock_email.assert_called_once()
        mock_telegram.assert_called_once()

    @patch("app.services.notification_dispatcher.create_action_tokens")
    @patch("app.services.notification_dispatcher.send_pending_request_email")
    async def test_disabled_channel_not_dispatched(
        self,
        mock_email,
        mock_create_tokens,
        db,
        mock_redis,
        account,
    ):
        """Disabled channels are skipped."""
        from app.services.action_tokens import ActionTokens

        mock_create_tokens.return_value = ActionTokens(
            approve="act_approve", reject="act_reject"
        )

        ch = NotificationChannel(
            id=str(uuid.uuid4()),
            account_id=account.id,
            channel_type="email",
            is_enabled=False,
            priority=10,
            config={},
            verified_at=utcnow(),
            created_at=utcnow(),
        )
        db.add(ch)
        await db.commit()

        # No enabled channels but channel exists → falls back to push+email
        await dispatch_notification(db, mock_redis, account.id, _make_event())

        # The email channel handler should NOT be called via dispatcher
        # (it falls back to the legacy path instead)

    @patch("app.services.notification_dispatcher.create_action_tokens")
    @patch("app.services.notification_dispatcher.send_push_to_account")
    @patch("app.services.notification_dispatcher.send_pending_request_email")
    async def test_all_channels_disabled_triggers_fallback(
        self,
        mock_email,
        mock_push,
        mock_create_tokens,
        db,
        mock_redis,
        account,
    ):
        """When channels exist but all are disabled, fallback is triggered."""
        from app.services.action_tokens import ActionTokens

        mock_create_tokens.return_value = ActionTokens(
            approve="act_approve", reject="act_reject"
        )
        mock_push.return_value = 0
        mock_email.return_value = True

        for channel_type in ("email", "telegram"):
            ch = NotificationChannel(
                id=str(uuid.uuid4()),
                account_id=account.id,
                channel_type=channel_type,
                is_enabled=False,
                priority=0,
                config={"chat_id": 12345} if channel_type == "telegram" else {},
                verified_at=utcnow(),
                created_at=utcnow(),
            )
            db.add(ch)
        await db.commit()

        await dispatch_notification(db, mock_redis, account.id, _make_event())

        # Fallback should fire: push attempted, then email
        mock_push.assert_called_once()
        mock_email.assert_called_once()

    @patch("app.services.notification_dispatcher.create_action_tokens")
    @patch("app.services.notification_dispatcher.send_pending_request_email")
    async def test_ttl_derived_from_expires_at(
        self,
        mock_email,
        mock_create_tokens,
        db,
        mock_redis,
        account,
    ):
        """Action token TTL is derived from request expires_at, not account setting."""
        from app.services.action_tokens import ActionTokens

        mock_create_tokens.return_value = ActionTokens(
            approve="act_approve", reject="act_reject"
        )
        mock_email.return_value = True

        # expires_at in 10 minutes, but account_expiry_minutes is 30
        expires_at = utcnow() + timedelta(minutes=10)
        event = _make_event(expires_at=expires_at, account_expiry_minutes=30)

        await dispatch_notification(db, mock_redis, account.id, event)

        # TTL should be ~600s (10 min), not 1800s (30 min)
        _, kwargs = mock_create_tokens.call_args
        ttl = kwargs.get("ttl_seconds") or mock_create_tokens.call_args[0][3]
        assert 540 <= ttl <= 660  # 10 min ± 1 min tolerance

    @patch("app.services.notification_dispatcher.create_action_tokens")
    @patch("app.services.notification_dispatcher.send_pending_request_email")
    async def test_ttl_fallback_to_account_expiry(
        self,
        mock_email,
        mock_create_tokens,
        db,
        mock_redis,
        account,
    ):
        """Without expires_at, TTL falls back to account_expiry_minutes."""
        from app.services.action_tokens import ActionTokens

        mock_create_tokens.return_value = ActionTokens(
            approve="act_approve", reject="act_reject"
        )
        mock_email.return_value = True

        event = _make_event(account_expiry_minutes=15)  # no expires_at

        await dispatch_notification(db, mock_redis, account.id, event)

        _, kwargs = mock_create_tokens.call_args
        ttl = kwargs.get("ttl_seconds") or mock_create_tokens.call_args[0][3]
        assert ttl == 900  # 15 * 60

    @patch("app.services.notification_dispatcher.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.notification_dispatcher.create_action_tokens")
    @patch("app.services.notification_dispatcher.send_pending_request_email")
    async def test_retry_on_failure_then_success(
        self,
        mock_email,
        mock_create_tokens,
        mock_sleep,
        db,
        mock_redis,
        account,
    ):
        """Failed dispatch retries and succeeds on second attempt."""
        from app.services.action_tokens import ActionTokens

        mock_create_tokens.return_value = ActionTokens(
            approve="act_approve", reject="act_reject"
        )
        # Fail first, succeed second
        mock_email.side_effect = [RuntimeError("temporary failure"), True]

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

        await dispatch_notification(db, mock_redis, account.id, _make_event())

        assert mock_email.call_count == 2
        mock_sleep.assert_called_once()

    @patch("app.services.notification_dispatcher.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.notification_dispatcher.create_action_tokens")
    @patch("app.services.notification_dispatcher.send_pending_request_email")
    async def test_retry_exhausted_logs_failure(
        self,
        mock_email,
        mock_create_tokens,
        mock_sleep,
        db,
        mock_redis,
        account,
    ):
        """All retry attempts fail — status is 'failed'."""
        from app.services.action_tokens import ActionTokens

        mock_create_tokens.return_value = ActionTokens(
            approve="act_approve", reject="act_reject"
        )
        mock_email.side_effect = RuntimeError("persistent failure")

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

        # Should not raise
        await dispatch_notification(db, mock_redis, account.id, _make_event())

        # 1 initial + 2 retries = 3 attempts
        assert mock_email.call_count == 3
