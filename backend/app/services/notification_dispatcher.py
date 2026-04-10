import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session as session_factory
from app.models import NotificationChannel, NotificationLog
from app.services.action_tokens import ActionTokens, create_action_tokens
from app.services.email_notify import send_pending_request_email
from app.services.push import send_push_to_account
from app.utils import ensure_utc, utcnow

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_RETRY_DELAY_SECONDS = 3


@dataclass
class NotificationEvent:
    event_type: str  # "pending_request"
    request_id: str
    agent_name: str
    amount: str
    currency: str
    category: str
    expires_at: datetime | None = None
    account_expiry_minutes: int = 30
    merchant: str | None = None
    agent_comment: str | None = None


async def dispatch_notification(
    db: AsyncSession | None,
    redis: aioredis.Redis,
    account_id: str,
    event: NotificationEvent,
) -> None:
    """Fan out notification to all enabled channels for an account.

    When called from a background task (fire-and-forget), pass db=None
    and the function will create its own session.
    """
    # Use provided session or create a new one for background tasks
    if db is not None:
        return await _dispatch_notification_impl(db, redis, account_id, event)
    async with session_factory() as own_db:
        return await _dispatch_notification_impl(own_db, redis, account_id, event)


async def _dispatch_notification_impl(
    db: AsyncSession,
    redis: aioredis.Redis,
    account_id: str,
    event: NotificationEvent,
) -> None:
    # Check if account has any channels configured at all
    all_result = await db.execute(
        select(NotificationChannel.id)
        .where(NotificationChannel.account_id == account_id)
        .limit(1)
    )
    has_any_channels = all_result.scalar_one_or_none() is not None

    # Load enabled channels sorted by priority
    result = await db.execute(
        select(NotificationChannel)
        .where(
            NotificationChannel.account_id == account_id,
            NotificationChannel.is_enabled.is_(True),
        )
        .order_by(NotificationChannel.priority)
    )
    channels = list(result.scalars().all())

    # Generate action tokens once, shared across all channels.
    # Derive TTL from request expires_at when available, fall back to account setting.
    if event.expires_at:
        ttl = max(int((ensure_utc(event.expires_at) - utcnow()).total_seconds()), 60)
    else:
        ttl = event.account_expiry_minutes * 60
    action_tokens = await create_action_tokens(redis, account_id, event.request_id, ttl)

    if channels:
        # Dispatch to all configured channels in parallel
        tasks = []
        for ch in channels:
            handler = _HANDLERS.get(ch.channel_type)
            if handler:
                tasks.append(
                    _dispatch_one(db, handler, ch, account_id, event, action_tokens)
                )
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    elif has_any_channels:
        # Channels exist but all disabled — still send via fallback
        logger.warning(
            "All notification channels disabled for account %s, using fallback",
            account_id,
        )
        await _fallback_push_email(db, account_id, event, action_tokens)
    else:
        # No channels configured — fallback to legacy behavior (push → email)
        await _fallback_push_email(db, account_id, event, action_tokens)


async def _dispatch_one(
    db: AsyncSession,
    handler,
    channel: NotificationChannel,
    account_id: str,
    event: NotificationEvent,
    action_tokens: ActionTokens,
) -> None:
    """Dispatch to a single channel with retry and log the result."""
    status = "sent"
    error = None
    last_exc = None

    for attempt in range(_MAX_RETRIES + 1):
        try:
            await handler(db, channel, account_id, event, action_tokens)
            last_exc = None
            break
        except Exception as e:
            last_exc = e
            if attempt < _MAX_RETRIES:
                logger.warning(
                    "Notification attempt %d/%d failed for channel %s (account %s): %s, retrying",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    channel.channel_type,
                    account_id,
                    e,
                )
                await asyncio.sleep(_RETRY_DELAY_SECONDS)

    if last_exc:
        status = "failed"
        error = str(last_exc)[:500]
        logger.exception(
            "Notification failed after %d attempts for channel %s (account %s)",
            _MAX_RETRIES + 1,
            channel.channel_type,
            account_id,
        )

    # Log to a separate session to avoid interfering with the main flow
    try:
        async with session_factory() as log_db:
            log = NotificationLog(
                id=str(uuid.uuid4()),
                account_id=account_id,
                request_id=event.request_id,
                channel_type=channel.channel_type,
                event_type=event.event_type,
                status=status,
                error=error,
                created_at=utcnow(),
            )
            log_db.add(log)
            await log_db.commit()
    except Exception:
        logger.warning("Failed to log notification delivery")


async def _fallback_push_email(
    db: AsyncSession,
    account_id: str,
    event: NotificationEvent,
    action_tokens: ActionTokens,
) -> None:
    """Legacy fallback: try web push, then email if no push delivered."""
    push_body = f"{event.amount} {event.currency} — {event.category}"
    if event.agent_comment:
        push_body += f"\n{event.agent_comment}"

    push_count = await send_push_to_account(
        db,
        account_id,
        title=f"{event.agent_name}: new purchase request",
        body=push_body,
        data={"request_id": event.request_id},
    )

    if push_count == 0:
        await send_pending_request_email(
            db,
            account_id=account_id,
            agent_name=event.agent_name,
            amount=event.amount,
            currency=event.currency,
            category=event.category,
            merchant=event.merchant,
            agent_comment=event.agent_comment,
            request_id=event.request_id,
            action_tokens=action_tokens,
        )


# --- Channel handlers ---


async def _handle_web_push(
    db: AsyncSession,
    channel: NotificationChannel,
    account_id: str,
    event: NotificationEvent,
    action_tokens: ActionTokens,
) -> None:
    push_body = f"{event.amount} {event.currency} — {event.category}"
    if event.agent_comment:
        push_body += f"\n{event.agent_comment}"

    await send_push_to_account(
        db,
        account_id,
        title=f"{event.agent_name}: new purchase request",
        body=push_body,
        data={"request_id": event.request_id},
    )


async def _handle_email(
    db: AsyncSession,
    channel: NotificationChannel,
    account_id: str,
    event: NotificationEvent,
    action_tokens: ActionTokens,
) -> None:
    await send_pending_request_email(
        db,
        account_id=account_id,
        agent_name=event.agent_name,
        amount=event.amount,
        currency=event.currency,
        category=event.category,
        merchant=event.merchant,
        agent_comment=event.agent_comment,
        request_id=event.request_id,
        action_tokens=action_tokens,
    )


async def _handle_telegram(
    db: AsyncSession,
    channel: NotificationChannel,
    account_id: str,
    event: NotificationEvent,
    action_tokens: ActionTokens,
) -> None:
    from app.services.telegram import send_telegram_notification

    chat_id = channel.config.get("chat_id")
    if not chat_id:
        logger.warning("Telegram channel for account %s has no chat_id", account_id)
        return

    await send_telegram_notification(
        chat_id=chat_id,
        event=event,
        action_tokens=action_tokens,
    )


_HANDLERS: dict[str, object] = {
    "web_push": _handle_web_push,
    "email": _handle_email,
    "telegram": _handle_telegram,
}
