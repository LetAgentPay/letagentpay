from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_account
from app.models import Account, PushSubscription
from app.schemas import PushSubscribeRequest

router = APIRouter(prefix="/api/v1/push", tags=["push"])


@router.get("/vapid-key")
async def get_vapid_key():
    key = settings.vapid_public_key
    if not key:
        raise HTTPException(status_code=404, detail="Push notifications not configured")
    return {"vapid_public_key": key}


@router.post("/subscribe", status_code=201)
async def subscribe(
    body: PushSubscribeRequest,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    # Upsert: if endpoint already exists, update keys
    result = await db.execute(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.account_id = account.id
        existing.p256dh = body.p256dh
        existing.auth = body.auth
    else:
        # Remove stale subscriptions for this account that share the same
        # FCM origin — when a browser re-subscribes the endpoint changes,
        # leaving orphaned rows that always return 410.
        from urllib.parse import urlparse

        new_origin = urlparse(body.endpoint).netloc
        stale = await db.execute(
            select(PushSubscription).where(
                PushSubscription.account_id == account.id,
                PushSubscription.endpoint != body.endpoint,
            )
        )
        for old_sub in stale.scalars().all():
            if urlparse(old_sub.endpoint).netloc == new_origin:
                await db.delete(old_sub)

        sub = PushSubscription(
            account_id=account.id,
            endpoint=body.endpoint,
            p256dh=body.p256dh,
            auth=body.auth,
        )
        db.add(sub)

    await db.commit()
    return {"message": "Subscribed"}


@router.delete("/subscribe")
async def unsubscribe(
    body: PushSubscribeRequest,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        delete(PushSubscription).where(
            PushSubscription.endpoint == body.endpoint,
            PushSubscription.account_id == account.id,
        )
    )
    if result.rowcount == 0:  # type: ignore[attr-defined]
        raise HTTPException(status_code=404, detail="Subscription not found")

    await db.commit()
    return {"message": "Unsubscribed"}
