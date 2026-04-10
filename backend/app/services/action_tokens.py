import json
import logging
import secrets
from dataclasses import dataclass

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import Agent, PurchaseRequest
from app.redis import get_redis
from app.services.request_actions import (
    approve_purchase_request,
    reject_purchase_request,
)
from app.utils import ensure_utc, utcnow

logger = logging.getLogger(__name__)

_PREFIX = "action_token:"

# Lua script: atomically get-and-delete token + delete paired token.
# Prevents race where both approve and reject tokens are consumed concurrently.
_CONSUME_TOKEN_SCRIPT = """
local data = redis.call('GET', KEYS[1])
if not data then return nil end
redis.call('DEL', KEYS[1])
local ok, parsed = pcall(cjson.decode, data)
if ok and parsed.paired_key then
    redis.call('DEL', parsed.paired_key)
end
return data
"""


@dataclass
class ActionTokens:
    approve: str
    reject: str


@dataclass
class ActionResult:
    success: bool
    action: str
    request_id: str
    status: str
    message: str


async def create_action_tokens(
    redis: aioredis.Redis,
    account_id: str,
    request_id: str,
    ttl_seconds: int,
) -> ActionTokens:
    """Generate one-time approve/reject tokens stored in Redis."""
    approve_token = f"act_{secrets.token_urlsafe(32)}"
    reject_token = f"act_{secrets.token_urlsafe(32)}"

    pipe = redis.pipeline()
    for token, action, paired in [
        (approve_token, "approve", reject_token),
        (reject_token, "reject", approve_token),
    ]:
        pipe.setex(
            f"{_PREFIX}{token}",
            ttl_seconds,
            json.dumps(
                {
                    "account_id": account_id,
                    "request_id": request_id,
                    "action": action,
                    "paired_key": f"{_PREFIX}{paired}",
                }
            ),
        )
    await pipe.execute()

    return ActionTokens(approve=approve_token, reject=reject_token)


async def execute_action_token(
    db: AsyncSession,
    token: str,
) -> ActionResult:
    """Consume a one-time action token and execute the approve/reject.

    Returns ActionResult with the outcome.
    """
    redis = get_redis()

    # Atomically consume token and invalidate its paired token (approve/reject)
    # via Lua script to prevent race condition where both are executed concurrently
    key = f"{_PREFIX}{token}"
    raw = await redis.eval(_CONSUME_TOKEN_SCRIPT, 1, key)  # type: ignore[misc]
    if not raw:
        return ActionResult(
            success=False,
            action="",
            request_id="",
            status="invalid",
            message="Token is invalid or has already been used.",
        )

    try:
        data = json.loads(raw)
        account_id = data["account_id"]
        request_id = data["request_id"]
        action = data["action"]
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Corrupt action token data for key %s: %s", key, e)
        return ActionResult(
            success=False,
            action="",
            request_id="",
            status="invalid",
            message="Token is invalid or has already been used.",
        )

    # Load and lock request to prevent concurrent approve/reject via dashboard
    result = await db.execute(
        select(PurchaseRequest)
        .options(joinedload(PurchaseRequest.agent).joinedload(Agent.account))
        .where(PurchaseRequest.id == request_id)
        .with_for_update(of=PurchaseRequest)
    )
    req = result.scalar_one_or_none()

    if not req or req.agent.account_id != account_id:
        return ActionResult(
            success=False,
            action=action,
            request_id=request_id,
            status="not_found",
            message="Request not found.",
        )

    if req.status != "pending":
        return ActionResult(
            success=False,
            action=action,
            request_id=request_id,
            status=req.status,
            message=f"Request has already been {req.status}.",
        )

    if ensure_utc(req.expires_at) < utcnow():
        return ActionResult(
            success=False,
            action=action,
            request_id=request_id,
            status="expired",
            message="Request has expired.",
        )

    if action == "approve":
        return await _execute_approve(db, redis, req, account_id)
    else:
        return await _execute_reject(db, redis, req, account_id)


async def _execute_approve(
    db: AsyncSession,
    redis: aioredis.Redis,
    req: PurchaseRequest,
    account_id: str,
) -> ActionResult:
    """Execute approve action via shared service."""
    await approve_purchase_request(db, redis, req, account_id)
    return ActionResult(
        success=True,
        action="approve",
        request_id=req.id,
        status="approved",
        message="Request approved successfully.",
    )


async def _execute_reject(
    db: AsyncSession,
    redis: aioredis.Redis,
    req: PurchaseRequest,
    account_id: str,
) -> ActionResult:
    """Execute reject action via shared service."""
    await reject_purchase_request(db, redis, req, account_id)
    return ActionResult(
        success=True,
        action="reject",
        request_id=req.id,
        status="rejected",
        message="Request rejected.",
    )
