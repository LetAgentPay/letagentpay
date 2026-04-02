"""Tests for Telegram bot service."""

import secrets
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select

from app.models import NotificationChannel
from app.services.telegram import (
    _escape_md,
    get_bot_username,
    handle_telegram_update,
    send_telegram_notification,
)


class TestEscapeMarkdown:
    def test_escapes_special_chars(self):
        assert _escape_md("Hello *world*!") == "Hello \\*world\\*\\!"

    def test_plain_text_unchanged(self):
        assert _escape_md("Hello world") == "Hello world"

    def test_escapes_all_specials(self):
        for ch in "_*[]()~`>#+-=|{}.!":
            assert f"\\{ch}" in _escape_md(ch)


class TestGetBotUsername:
    @patch("app.services.telegram.settings")
    async def test_no_token_returns_none(self, mock_settings):
        mock_settings.telegram_bot_token = ""
        result = await get_bot_username()
        assert result is None

    @patch("app.services.telegram.settings")
    async def test_returns_username(self, mock_settings):
        mock_settings.telegram_bot_token = "123:test"

        import app.services.telegram as tg_mod

        tg_mod._bot_username = None

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"result": {"username": "test_bot"}}
        mock_resp.raise_for_status = lambda: None

        with patch("app.services.telegram.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_bot_username()
            assert result == "test_bot"


class TestHandleTelegramUpdate:
    @patch("app.services.telegram._send_message", new_callable=AsyncMock)
    async def test_start_without_token(self, mock_send, db):
        update = {
            "message": {
                "chat": {"id": 12345},
                "text": "/start",
            }
        }
        await handle_telegram_update(update, db)
        mock_send.assert_called_once()
        # Check that "Welcome" is in the text kwarg
        _, kwargs = mock_send.call_args
        assert "Welcome" in kwargs.get("text", "")

    @patch("app.services.telegram._send_message", new_callable=AsyncMock)
    async def test_start_with_valid_token(self, mock_send, db, account):
        redis = AsyncMock()
        redis.getdel = AsyncMock(return_value=account.id)

        with patch("app.redis.get_redis", return_value=redis):
            update = {
                "message": {
                    "chat": {"id": 12345, "username": "testuser"},
                    "text": "/start valid_token",
                }
            }
            await handle_telegram_update(update, db)

        # Check that notification channel was created
        result = await db.execute(
            select(NotificationChannel).where(
                NotificationChannel.account_id == account.id,
                NotificationChannel.channel_type == "telegram",
            )
        )
        ch = result.scalar_one_or_none()
        assert ch is not None
        assert ch.config["chat_id"] == 12345
        assert ch.config["username"] == "testuser"
        assert ch.verified_at is not None

    @patch("app.services.telegram._send_message", new_callable=AsyncMock)
    async def test_start_with_expired_token(self, mock_send, db):
        redis = AsyncMock()
        redis.getdel = AsyncMock(return_value=None)

        with patch("app.redis.get_redis", return_value=redis):
            update = {
                "message": {
                    "chat": {"id": 12345},
                    "text": "/start expired_token",
                }
            }
            await handle_telegram_update(update, db)

        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args
        text = kwargs.get("text", "")
        assert "expired" in text.lower() or "invalid" in text.lower()

    @patch("app.services.telegram._send_message", new_callable=AsyncMock)
    async def test_relink_updates_existing_channel(self, mock_send, db, account):
        """Re-linking from a different Telegram account updates existing channel."""
        redis = AsyncMock()
        redis.getdel = AsyncMock(return_value=account.id)

        # First link
        with patch("app.redis.get_redis", return_value=redis):
            update1 = {
                "message": {
                    "chat": {"id": 11111, "username": "old_user"},
                    "text": "/start token1",
                }
            }
            await handle_telegram_update(update1, db)

        redis.getdel = AsyncMock(return_value=account.id)

        # Re-link with different chat
        with patch("app.redis.get_redis", return_value=redis):
            update2 = {
                "message": {
                    "chat": {"id": 22222, "username": "new_user"},
                    "text": "/start token2",
                }
            }
            await handle_telegram_update(update2, db)

        # Should have exactly one channel, updated
        result = await db.execute(
            select(NotificationChannel).where(
                NotificationChannel.account_id == account.id,
                NotificationChannel.channel_type == "telegram",
            )
        )
        channels = result.scalars().all()
        assert len(channels) == 1
        assert channels[0].config["chat_id"] == 22222
        assert channels[0].config["username"] == "new_user"

    @patch("app.services.telegram._edit_message", new_callable=AsyncMock)
    @patch("app.services.telegram._answer_callback", new_callable=AsyncMock)
    @patch("app.services.action_tokens.execute_action_token")
    async def test_callback_approve(self, mock_execute, mock_answer, mock_edit, db):
        from app.services.action_tokens import ActionResult

        mock_execute.return_value = ActionResult(
            success=True,
            action="approve",
            request_id="req-1",
            status="approved",
            message="Request approved successfully.",
        )

        update = {
            "callback_query": {
                "id": "cb-1",
                "data": "approve:act_test_token",
                "message": {
                    "chat": {"id": 12345},
                    "message_id": 100,
                    "text": "Test notification",
                },
            }
        }
        await handle_telegram_update(update, db)

        mock_answer.assert_called_once()
        mock_edit.assert_called_once()


class TestCallbackDataLimit:
    """Telegram limits callback_data to 64 bytes."""

    _TG_CALLBACK_LIMIT = 64

    def test_action_token_callback_data_fits_limit(self):
        """Verify that callback_data with real token lengths stays under 64 bytes."""
        # Reproduce exact token generation from action_tokens.py
        token = f"act_{secrets.token_urlsafe(32)}"

        approve_cb = f"approve:{token}"
        reject_cb = f"reject:{token}"

        assert len(approve_cb.encode()) <= self._TG_CALLBACK_LIMIT, (
            f"approve callback_data is {len(approve_cb.encode())} bytes, "
            f"exceeds {self._TG_CALLBACK_LIMIT} limit"
        )
        assert len(reject_cb.encode()) <= self._TG_CALLBACK_LIMIT, (
            f"reject callback_data is {len(reject_cb.encode())} bytes, "
            f"exceeds {self._TG_CALLBACK_LIMIT} limit"
        )

    def test_callback_data_worst_case(self):
        """Test with 100 random tokens to cover base64url length variance."""
        for _ in range(100):
            token = f"act_{secrets.token_urlsafe(32)}"
            cb = f"approve:{token}"
            assert (
                len(cb.encode()) <= self._TG_CALLBACK_LIMIT
            ), f"callback_data '{cb}' is {len(cb.encode())} bytes"

    @patch("app.services.telegram._send_message", new_callable=AsyncMock)
    @patch("app.services.telegram.settings")
    async def test_send_notification_logs_error_on_overflow(
        self, mock_settings, mock_send
    ):
        """If tokens somehow exceed limit, error is logged."""
        mock_settings.telegram_bot_token = "123:test"

        # Create artificially long tokens that exceed 64 bytes
        long_token = "act_" + "A" * 60  # approve:act_AAA... = 72 bytes

        event = MagicMock()
        event.agent_name = "Bot"
        event.amount = "100"
        event.currency = "USD"
        event.category = "food"
        event.merchant = ""
        event.agent_comment = ""

        tokens = MagicMock()
        tokens.approve = long_token
        tokens.reject = long_token

        with patch("app.services.telegram.logger") as mock_logger:
            await send_telegram_notification(123, event, tokens)
            mock_logger.error.assert_called_once()
            assert "exceeds" in mock_logger.error.call_args[0][0]
