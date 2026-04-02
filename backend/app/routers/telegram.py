import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.telegram import handle_telegram_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["telegram"])


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive incoming updates from Telegram Bot API."""
    if not settings.telegram_bot_token:
        return {"ok": True}

    try:
        update = await request.json()
    except Exception:
        logger.warning("Invalid Telegram webhook payload")
        return {"ok": True}

    try:
        await handle_telegram_update(update, db)
    except Exception:
        logger.exception("Error handling Telegram update")

    # Always return 200 to prevent Telegram from retrying
    return {"ok": True}
