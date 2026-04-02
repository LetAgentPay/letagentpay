"""Playground session management.

Creates temporary accounts + agents for the public no-auth playground demo.
Sessions are tracked in Redis with a TTL; DB records are cleaned up periodically.
"""

import logging
import random
import uuid
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Account, Agent, PurchaseRequest
from app.redis import get_redis

logger = logging.getLogger(__name__)

# Redis key prefixes
_SESSION_KEY = "playground:session:"  # {session_id} → agent_token
_IP_KEY = "playground:ip:"  # {ip} → request count
_REQ_COUNT_KEY = "playground:reqs:"  # {session_id} → request count

# Playground account marker email
PLAYGROUND_EMAIL_DOMAIN = "playground.letagentpay.internal"

# Pool of diverse policy presets — each highlights different policy features
PLAYGROUND_POLICY_PRESETS = [
    {
        "name": "Office Assistant",
        "budget": 300,
        "policy": {
            "auto_approve": {"enabled": True, "max_amount": 25},
            "daily_limit": 100,
            "categories": {
                "allowed": [
                    "food_delivery",
                    "taxi",
                    "subscriptions",
                    "education",
                    "groceries",
                ]
            },
        },
        "policy_text": (
            "Office Assistant policy: auto-approve under $25, "
            "daily limit $100. "
            "Allowed: food delivery, taxi, subscriptions, education, groceries."
        ),
    },
    {
        "name": "Marketing Agent",
        "budget": 500,
        "policy": {
            "auto_approve": {"enabled": True, "max_amount": 75},
            "weekly_limit": 300,
            "per_request_limit": 120,
            "categories": {
                "allowed": [
                    "entertainment",
                    "subscriptions",
                    "restaurants",
                    "education",
                    "other",
                ]
            },
        },
        "policy_text": (
            "Marketing Agent policy: auto-approve under $75, "
            "per-request limit $120, weekly limit $300. "
            "Allowed: entertainment, subscriptions, restaurants, education, other."
        ),
    },
    {
        "name": "Research Agent",
        "budget": 400,
        "policy": {
            "auto_approve": {"enabled": True, "max_amount": 50},
            "monthly_limit": 350,
            "categories": {"blocked": ["flights", "accommodation", "clothing"]},
        },
        "policy_text": (
            "Research Agent policy: auto-approve under $50, "
            "monthly limit $350. "
            "Blocked categories: flights, accommodation, clothing."
        ),
    },
    {
        "name": "Personal Shopper",
        "budget": 600,
        "policy": {
            "auto_approve": {"enabled": True, "max_amount": 40},
            "per_request_limit": 150,
            "daily_limit": 250,
            "categories": {
                "allowed": [
                    "groceries",
                    "clothing",
                    "electronics",
                    "household",
                    "health",
                ]
            },
        },
        "policy_text": (
            "Personal Shopper policy: auto-approve under $40, "
            "per-request limit $150, daily limit $250. "
            "Allowed: groceries, clothing, electronics, household, health."
        ),
    },
    {
        "name": "Travel Planner",
        "budget": 800,
        "policy": {
            "auto_approve": {"enabled": True, "max_amount": 100},
            "daily_limit": 400,
            "per_request_limit": 250,
            "categories": {
                "allowed": [
                    "flights",
                    "accommodation",
                    "taxi",
                    "restaurants",
                    "food_delivery",
                    "transport",
                ]
            },
        },
        "policy_text": (
            "Travel Planner policy: auto-approve under $100, "
            "per-request limit $250, daily limit $400. "
            "Allowed: flights, accommodation, taxi, restaurants, "
            "food delivery, transport."
        ),
    },
]


def _pick_random_preset() -> dict:
    """Pick a random policy preset for a new playground session."""
    return random.choice(PLAYGROUND_POLICY_PRESETS)


async def create_session(client_ip: str, db: AsyncSession) -> dict:
    """Create a new playground session with a temporary account + agent.

    Returns dict with session_id, agent_token, budget, policy, expires_in.
    Raises ValueError if rate-limited.
    """
    redis = get_redis()
    ttl = settings.playground_session_ttl_minutes * 60

    # Rate limit: 1 session per IP per 10 minutes
    ip_key = f"{_IP_KEY}{client_ip}"
    current = await redis.get(ip_key)
    if current and int(current) >= 3:
        raise ValueError("Too many sessions. Please wait a few minutes.")
    await redis.incr(ip_key)
    await redis.expire(ip_key, 600)  # 10 min window

    # Pick a random policy preset
    preset = _pick_random_preset()

    # Create temporary account
    session_id = str(uuid.uuid4())
    email = f"{session_id}@{PLAYGROUND_EMAIL_DOMAIN}"

    account = Account(
        email=email,
        name="Playground User",
        currency="USD",
        timezone="America/New_York",
    )
    db.add(account)
    await db.flush()

    # Create agent with randomly selected policy
    budget = Decimal(str(preset["budget"]))
    agent = Agent(
        account_id=account.id,
        name=preset["name"],
        description=f"Playground {preset['name']} — auto-created, temporary",
        budget=budget,
        policy=preset["policy"],
        policy_text=preset["policy_text"],
        is_sandbox=True,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    # Store session in Redis
    session_key = f"{_SESSION_KEY}{session_id}"
    await redis.set(session_key, agent.token, ex=ttl)

    # Init request counter
    req_key = f"{_REQ_COUNT_KEY}{session_id}"
    await redis.set(req_key, "0", ex=ttl)

    return {
        "session_id": session_id,
        "agent_token": agent.token,
        "agent_name": preset["name"],
        "budget": str(budget),
        "currency": "USD",
        "policy": preset["policy"],
        "policy_text": preset["policy_text"],
        "expires_in": ttl,
        "max_requests": settings.playground_max_requests,
    }


async def get_session(session_id: str) -> dict | None:
    """Get session info from Redis. Returns None if expired."""
    redis = get_redis()
    session_key = f"{_SESSION_KEY}{session_id}"
    token = await redis.get(session_key)
    if not token:
        return None

    ttl = await redis.ttl(session_key)
    req_key = f"{_REQ_COUNT_KEY}{session_id}"
    req_count = await redis.get(req_key)

    return {
        "session_id": session_id,
        "agent_token": token,
        "expires_in": max(ttl, 0),
        "requests_used": int(req_count) if req_count else 0,
        "max_requests": settings.playground_max_requests,
    }


async def increment_request_count(session_id: str) -> int:
    """Increment and return the request count for a session.

    Raises ValueError if max requests exceeded.
    """
    redis = get_redis()
    req_key = f"{_REQ_COUNT_KEY}{session_id}"
    count = await redis.incr(req_key)
    if count > settings.playground_max_requests:
        raise ValueError(
            f"Maximum {settings.playground_max_requests} requests per session."
        )
    return count


async def cleanup_expired_sessions(db: AsyncSession) -> int:
    """Delete playground accounts/agents/requests that have no active session.

    Called periodically (e.g. every 30 minutes) to prevent DB bloat.
    Returns the number of accounts deleted.
    """
    redis = get_redis()

    # Find all playground accounts
    result = await db.execute(
        select(Account.id, Account.email).where(
            Account.email.like(f"%@{PLAYGROUND_EMAIL_DOMAIN}")
        )
    )
    playground_accounts = result.all()

    deleted = 0
    for account_id, email in playground_accounts:
        # Extract session_id from email
        session_id = email.split("@")[0]
        session_key = f"{_SESSION_KEY}{session_id}"

        # Check if session is still active
        if await redis.exists(session_key):
            continue

        # Session expired — delete all related data
        # Delete requests first (FK dependency)
        agents_result = await db.execute(
            select(Agent.id).where(Agent.account_id == account_id)
        )
        agent_ids = [row[0] for row in agents_result.all()]

        if agent_ids:
            await db.execute(
                delete(PurchaseRequest).where(PurchaseRequest.agent_id.in_(agent_ids))
            )
            await db.execute(delete(Agent).where(Agent.account_id == account_id))

        await db.execute(delete(Account).where(Account.id == account_id))
        deleted += 1

    if deleted:
        await db.commit()
        logger.info("Cleaned up %d expired playground sessions", deleted)

    return deleted
