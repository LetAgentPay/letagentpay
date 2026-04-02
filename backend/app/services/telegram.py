import asyncio
import json
import logging
import uuid

import httpx
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import NotificationChannel
from app.utils import utcnow

logger = logging.getLogger(__name__)

_bot_username: str | None = None
_API_BASE = "https://api.telegram.org/bot"


class TelegramAPIError(Exception):
    """Raised when a Telegram API call fails."""


async def get_bot_username() -> str | None:
    """Get the bot username, fetching from Telegram API if needed."""
    global _bot_username
    if _bot_username:
        return _bot_username

    if not settings.telegram_bot_token:
        return None

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_API_BASE}{settings.telegram_bot_token}/getMe",
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            _bot_username = data["result"]["username"]
            return _bot_username
    except Exception:
        logger.exception("Failed to get Telegram bot username")
        return None


async def setup_webhook() -> None:
    """Register Telegram webhook on app startup. Called from lifespan."""
    if not settings.telegram_bot_token:
        return

    webhook_url = f"{settings.frontend_url}/api/v1/webhooks/telegram"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_API_BASE}{settings.telegram_bot_token}/setWebhook",
                json={
                    "url": webhook_url,
                    "allowed_updates": ["message", "callback_query"],
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("ok"):
                logger.info("Telegram webhook set: %s", webhook_url)
            else:
                logger.warning("Telegram webhook setup response: %s", data)
    except Exception:
        logger.exception("Failed to set Telegram webhook")

    # Also fetch bot username on startup
    await get_bot_username()


async def start_polling() -> None:
    """Long polling fallback for local development (no webhook)."""
    if not settings.telegram_bot_token:
        return

    # Delete any existing webhook so getUpdates works
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{_API_BASE}{settings.telegram_bot_token}/deleteWebhook",
                timeout=10,
            )
    except Exception:
        pass

    await get_bot_username()
    logger.info("Telegram bot polling started (dev mode)")

    offset = 0
    while True:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{_API_BASE}{settings.telegram_bot_token}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                    timeout=35,
                )
                resp.raise_for_status()
                data = resp.json()

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                try:
                    from app.database import async_session

                    async with async_session() as db:
                        await handle_telegram_update(update, db)
                except Exception:
                    logger.exception(
                        "Error processing Telegram update %s", update.get("update_id")
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Telegram polling error, retrying in 5s")
            await asyncio.sleep(5)


async def send_telegram_notification(
    chat_id: int,
    event,
    action_tokens,
) -> None:
    """Send a notification message with inline approve/reject buttons."""
    if not settings.telegram_bot_token:
        return

    # Build message text
    lines = [
        f"🔔 *{_escape_md(event.agent_name)}*: new purchase request",
        "",
        f"💰 Amount: {_escape_md(event.amount)} {_escape_md(event.currency)}",
        f"📁 Category: {_escape_md(event.category)}",
    ]
    if event.merchant:
        lines.append(f"🏪 Merchant: {_escape_md(event.merchant)}")
    if event.agent_comment:
        lines.append(f"💬 {_escape_md(event.agent_comment)}")

    text = "\n".join(lines)

    # Inline keyboard with approve/reject buttons
    # Telegram limits callback_data to 64 bytes
    _TG_CALLBACK_LIMIT = 64
    approve_cb = f"approve:{action_tokens.approve}"
    reject_cb = f"reject:{action_tokens.reject}"

    if (
        len(approve_cb.encode()) > _TG_CALLBACK_LIMIT
        or len(reject_cb.encode()) > _TG_CALLBACK_LIMIT
    ):
        logger.error(
            "Telegram callback_data exceeds %d bytes (approve=%d, reject=%d), "
            "buttons will not work",
            _TG_CALLBACK_LIMIT,
            len(approve_cb.encode()),
            len(reject_cb.encode()),
        )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": approve_cb},
                {"text": "❌ Reject", "callback_data": reject_cb},
            ]
        ]
    }

    await _send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="MarkdownV2",
        reply_markup=keyboard,
        raise_on_error=True,
    )


async def send_admin_notification(text: str) -> None:
    """Send a plain-text message to the admin monitoring chat."""
    if not settings.telegram_bot_token or not settings.telegram_admin_chat_id:
        return

    await _send_message(
        chat_id=int(settings.telegram_admin_chat_id),
        text=text,
    )


async def handle_telegram_update(update: dict, db: AsyncSession) -> None:
    """Process an incoming Telegram webhook update."""
    if "callback_query" in update:
        await _handle_callback(update["callback_query"], db)
    elif "message" in update:
        await _handle_message(update["message"], db)


async def _handle_message(message: dict, db: AsyncSession) -> None:
    """Handle incoming messages (primarily /start for account linking)."""
    text = message.get("text", "")
    chat_id = message["chat"]["id"]

    if text.startswith("/start "):
        link_token = text[7:].strip()
        await _link_account(chat_id, message["chat"], link_token, db)
    elif text == "/start":
        await _send_message(
            chat_id=chat_id,
            text=(
                "Welcome to LetAgentPay!\n\n"
                "To connect your account, use the link from your "
                "LetAgentPay dashboard (Settings → Notifications → Connect Telegram)."
            ),
        )
    elif text == "/help":
        await _send_message(
            chat_id=chat_id,
            text=(
                "LetAgentPay Telegram Bot\n\n"
                "I send you notifications when your AI agents make purchase requests. "
                "You can approve or reject them directly from here.\n\n"
                "Connect your account from the LetAgentPay dashboard."
            ),
        )


async def _link_account(
    chat_id: int,
    chat: dict,
    link_token: str,
    db: AsyncSession,
) -> None:
    """Link a Telegram chat to a LetAgentPay account using a link token."""
    from app.redis import get_redis

    redis = get_redis()
    key = f"tg_link:{link_token}"
    account_id = await redis.getdel(key)

    if not account_id:
        await _send_message(
            chat_id=chat_id,
            text="Link expired or invalid. Please generate a new link from your dashboard (Settings → Notifications → Connect).",
        )
        return

    username = chat.get("username", "")
    now = utcnow()
    config = {"chat_id": chat_id, "username": username}

    # Atomic update-or-insert: try update first, insert only if no row exists.
    # This avoids race conditions between concurrent Telegram callbacks.
    result = await db.execute(
        update(NotificationChannel)
        .where(
            NotificationChannel.account_id == account_id,
            NotificationChannel.channel_type == "telegram",
        )
        .values(config=config, is_enabled=True, verified_at=now)
    )

    if result.rowcount == 0:  # type: ignore[attr-defined]
        try:
            ch = NotificationChannel(
                id=str(uuid.uuid4()),
                account_id=account_id,
                channel_type="telegram",
                is_enabled=True,
                priority=0,
                config=config,
                verified_at=now,
                created_at=now,
            )
            db.add(ch)
            await db.flush()
        except IntegrityError:
            # Concurrent insert won the race — update the existing row
            await db.rollback()
            await db.execute(
                update(NotificationChannel)
                .where(
                    NotificationChannel.account_id == account_id,
                    NotificationChannel.channel_type == "telegram",
                )
                .values(config=config, is_enabled=True, verified_at=now)
            )

    await db.commit()

    await _send_message(
        chat_id=chat_id,
        text=(
            "✅ Account connected!\n\n"
            "From now on, when your AI agents request a purchase, "
            "you'll get a notification right here with Approve and Reject buttons.\n\n"
            "No need to open the dashboard — just tap a button to respond instantly."
        ),
    )
    logger.info("Telegram linked: chat_id=%s, account=%s", chat_id, account_id)


async def _handle_callback(callback_query: dict, db: AsyncSession) -> None:
    """Handle inline button presses (approve/reject)."""
    from app.services.action_tokens import execute_action_token

    callback_id = callback_query["id"]
    data = callback_query.get("data", "")
    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]

    if ":" not in data:
        await _answer_callback(callback_id, "Invalid action")
        return

    action, token = data.split(":", 1)
    result = await execute_action_token(db, token)

    if result.success:
        status_text = "✅ Approved" if action == "approve" else "❌ Rejected"
        await _answer_callback(callback_id, status_text)
        # Update the message to show the result and remove buttons
        original_text = callback_query["message"].get("text", "")
        await _edit_message(
            chat_id=chat_id,
            message_id=message_id,
            text=f"{_escape_md(original_text)}\n\n*{status_text}*",
            parse_mode="MarkdownV2",
        )
    else:
        await _answer_callback(callback_id, result.message)
        # Update message to show failure
        original_text = callback_query["message"].get("text", "")
        await _edit_message(
            chat_id=chat_id,
            message_id=message_id,
            text=f"{_escape_md(original_text)}\n\n⚠️ {_escape_md(result.message)}",
            parse_mode="MarkdownV2",
        )


# --- Telegram API helpers ---


async def _send_message(
    chat_id: int,
    text: str,
    parse_mode: str | None = None,
    reply_markup: dict | None = None,
    *,
    raise_on_error: bool = False,
) -> dict | None:
    payload: dict = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    return await _api_call("sendMessage", payload, raise_on_error=raise_on_error)


async def _edit_message(
    chat_id: int,
    message_id: int,
    text: str,
    parse_mode: str | None = None,
) -> dict | None:
    payload: dict = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    return await _api_call("editMessageText", payload)


async def _answer_callback(callback_query_id: str, text: str) -> dict | None:
    return await _api_call(
        "answerCallbackQuery",
        {"callback_query_id": callback_query_id, "text": text},
    )


async def _api_call(
    method: str, payload: dict, *, raise_on_error: bool = False
) -> dict | None:
    if not settings.telegram_bot_token:
        return None

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_API_BASE}{settings.telegram_bot_token}/{method}",
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.exception("Telegram API call %s failed", method)
        if raise_on_error:
            raise TelegramAPIError(f"Telegram {method} failed: {e}") from e
        return None


def _escape_md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"_*[]()~`>#+-=|{}.!"
    result = ""
    for ch in text:
        if ch in special:
            result += f"\\{ch}"
        else:
            result += ch
    return result
