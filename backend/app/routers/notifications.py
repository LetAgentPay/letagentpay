import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_account
from app.models import Account, NotificationChannel
from app.redis import get_redis
from app.utils import utcnow

router = APIRouter(prefix="/api/v1/me/notifications", tags=["notifications"])

_TG_LINK_PREFIX = "tg_link:"
_TG_LINK_TTL = 600  # 10 minutes


class ChannelOut(BaseModel):
    channel_type: str
    is_enabled: bool
    priority: int
    verified: bool
    config: dict


class ChannelUpdate(BaseModel):
    is_enabled: bool | None = None
    priority: int | None = None


@router.get("/channels")
async def list_channels(
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
) -> list[ChannelOut]:
    result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.account_id == account.id)
        .order_by(NotificationChannel.priority)
    )
    channels = result.scalars().all()
    return [
        ChannelOut(
            channel_type=ch.channel_type,
            is_enabled=ch.is_enabled,
            priority=ch.priority,
            verified=ch.verified_at is not None,
            config=(
                {
                    k: v
                    for k, v in ch.config.items()
                    if k in ("username",)  # only expose safe fields
                }
                if ch.config
                else {}
            ),
        )
        for ch in channels
    ]


@router.put("/channels/{channel_type}")
async def update_channel(
    channel_type: str,
    body: ChannelUpdate,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
) -> ChannelOut:
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.account_id == account.id,
            NotificationChannel.channel_type == channel_type,
        )
    )
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    if body.is_enabled is not None:
        ch.is_enabled = body.is_enabled
    if body.priority is not None:
        ch.priority = body.priority

    await db.commit()
    await db.refresh(ch)
    return ChannelOut(
        channel_type=ch.channel_type,
        is_enabled=ch.is_enabled,
        priority=ch.priority,
        verified=ch.verified_at is not None,
        config={},
    )


@router.delete("/channels/{channel_type}")
async def disconnect_channel(
    channel_type: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        delete(NotificationChannel).where(
            NotificationChannel.account_id == account.id,
            NotificationChannel.channel_type == channel_type,
        )
    )
    if result.rowcount == 0:  # type: ignore[attr-defined]
        raise HTTPException(status_code=404, detail="Channel not found")
    await db.commit()
    return {"message": "Channel disconnected"}


@router.post("/channels/telegram/link")
async def create_telegram_link(
    account: Account = Depends(get_current_account),
):
    """Generate a Telegram deep-link for account linking."""
    if not settings.telegram_bot_token:
        raise HTTPException(
            status_code=404, detail="Telegram integration is not configured"
        )

    redis = get_redis()
    link_token = secrets.token_urlsafe(24)
    await redis.setex(
        f"{_TG_LINK_PREFIX}{link_token}",
        _TG_LINK_TTL,
        account.id,
    )

    # Derive bot username from token (first part before ':')
    # In production, this should come from getMe, but token prefix works as a fallback
    # The actual bot username will be resolved by the Telegram service on startup
    from app.services.telegram import get_bot_username

    bot_username = await get_bot_username()
    if not bot_username:
        raise HTTPException(
            status_code=500, detail="Could not determine Telegram bot username"
        )

    return {
        "link_url": f"https://t.me/{bot_username}?start={link_token}",
        "expires_in": _TG_LINK_TTL,
    }


@router.post("/channels/email/enable")
async def enable_email_channel(
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
) -> ChannelOut:
    """Enable email notification channel (auto-verified since we know the email)."""
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.account_id == account.id,
            NotificationChannel.channel_type == "email",
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.is_enabled = True
        await db.commit()
        await db.refresh(existing)
        ch = existing
    else:
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
        await db.refresh(ch)

    return ChannelOut(
        channel_type=ch.channel_type,
        is_enabled=ch.is_enabled,
        priority=ch.priority,
        verified=ch.verified_at is not None,
        config={},
    )
