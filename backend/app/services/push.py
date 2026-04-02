import json
import logging
import re

from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import PushSubscription

logger = logging.getLogger(__name__)

# pywebpush does not pass `response=` to WebPushException,
# so e.response is always None.  Parse status from the message instead.
_STATUS_RE = re.compile(r"Push failed:\s*(\d{3})\s")


async def send_push_to_account(
    db: AsyncSession,
    account_id: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> int:
    """Send Web Push notification to all subscriptions of an account.

    Returns number of successfully delivered notifications.
    """
    result = await db.execute(
        select(PushSubscription).where(PushSubscription.account_id == account_id)
    )
    subscriptions = result.scalars().all()

    if not subscriptions or not settings.vapid_private_key:
        logger.warning(
            "Push skipped for account %s: subs=%d, vapid_key=%s",
            account_id,
            len(subscriptions) if subscriptions else 0,
            bool(settings.vapid_private_key),
        )
        return 0

    payload = json.dumps({"title": title, "body": body, "data": data or {}})
    delivered = 0

    for sub in subscriptions:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={
                    "sub": f"mailto:{settings.vapid_contact_email}",
                },
            )
            delivered += 1
        except WebPushException as e:
            status = None
            if e.response and hasattr(e.response, "status_code"):
                status = e.response.status_code
            else:
                m = _STATUS_RE.search(str(e))
                if m:
                    status = int(m.group(1))

            if status in (404, 410):
                await db.delete(sub)
                await db.commit()
                logger.info("Removed expired push subscription %s", sub.id)
            else:
                logger.warning("Push failed for subscription %s: %s", sub.id, e)

    return delivered
