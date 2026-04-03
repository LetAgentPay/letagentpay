import asyncio
import logging

import jwt
from fastapi import Depends, HTTPException, Request
from jwt.exceptions import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import get_db
from app.models import Account, Agent

logger = logging.getLogger(__name__)


def _get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _fire_auth_alert(message: str) -> None:
    """Send auth failure alert as a background task (fire-and-forget)."""
    from app.services.telegram import send_alert_notification

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_alert_notification(message))
    except RuntimeError:
        pass


async def get_current_account(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Account:
    """Extract account from JWT cookie."""
    ip = _get_client_ip(request)
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        account_id: str = payload["sub"]
    except (PyJWTError, KeyError):
        logger.warning("Invalid JWT token from ip=%s", ip)
        _fire_auth_alert(f"🔑 Invalid JWT token\nIP: {ip}")
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        logger.warning("JWT references missing account=%s ip=%s", account_id, ip)
        _fire_auth_alert(
            f"🔑 JWT references missing account\nAccount: {account_id}\nIP: {ip}"
        )
        raise HTTPException(status_code=401, detail="Account not found")
    if account.blocked:
        raise HTTPException(status_code=403, detail="Account is blocked")
    return account


async def get_current_admin(
    account: Account = Depends(get_current_account),
) -> Account:
    """Ensure current user is an admin."""
    if not account.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return account


async def get_agent_by_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Agent:
    """Extract agent from Bearer token (Agent API)."""
    ip = _get_client_ip(request)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = auth_header[7:]
    result = await db.execute(
        select(Agent).options(joinedload(Agent.account)).where(Agent.token == token)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        token_preview = f"{token[:8]}..." if len(token) > 8 else token
        logger.warning("Invalid agent token from ip=%s token=%s", ip, token_preview)
        _fire_auth_alert(f"🤖 Invalid agent token\nIP: {ip}\nToken: {token_preview}")
        raise HTTPException(status_code=401, detail="Invalid agent token")
    if agent.account.blocked:
        raise HTTPException(status_code=403, detail="Account is blocked")
    if agent.account.all_agents_paused:
        raise HTTPException(
            status_code=403, detail="All agents are paused by account owner"
        )
    if agent.status == "archived":
        raise HTTPException(status_code=403, detail="Agent is archived")
    if agent.status != "active":
        raise HTTPException(status_code=403, detail="Agent is paused")
    return agent


async def get_owner_agent(
    agent_id: str,
    account: Account,
    db: AsyncSession,
) -> Agent:
    """Fetch agent ensuring it belongs to the account."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.account_id == account.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
