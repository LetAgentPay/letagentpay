"""x402 authorization gateway.

LAP as policy middleware for x402 payments:
- POST /authorize — pre-payment policy check (analog of Stripe Authorization Stream)
- POST /report — post-payment audit logging
- GET /budget — current x402 budget state
- Wallet CRUD — register/list agent wallets
"""

import logging
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.dependencies import get_agent_by_token
from app.models import Account, Agent, AgentWallet, PurchaseRequest
from app.redis import get_redis
from app.schemas import (
    AgentWalletRequest,
    AgentWalletResponse,
    Policy,
    X402AuthorizeRequest,
    X402AuthorizeResponse,
    X402ReportRequest,
    X402ReportResponse,
)
from app.services.category_resolver import resolve_category
from app.services.exchange_rates import DepegError, to_usd
from app.services.rate_limit import check_rate_limit
from app.services.realtime import publish_event
from app.services.spending import (
    add_spent,
    adjust_account_spent,
    adjust_spent,
    get_daily_held,
    get_daily_spent,
    get_monthly_held,
    get_monthly_spent,
    get_weekly_held,
    get_weekly_spent,
)
from app.utils import utcnow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/x402", tags=["x402"])

_AUTH_EXPIRY_SECONDS = 120


@router.post("/authorize", response_model=X402AuthorizeResponse)
async def authorize_x402_payment(
    body: X402AuthorizeRequest,
    agent: Agent = Depends(get_agent_by_token),
    db: AsyncSession = Depends(get_db),
):
    """Pre-payment policy check for x402 payments.

    Agent asks LAP: "can I pay $X for resource Y?"
    LAP checks policy and returns authorized/declined.
    """
    redis = get_redis()
    await check_rate_limit(redis, f"rate_limit:x402:{agent.id}", 60, 60)

    req = body.payment_requirements
    amount_usd = body.max_amount_usd

    # Convert settlement currency to USD if needed
    asset = req.asset.upper()
    try:
        amount_usd = await to_usd(redis, amount_usd, asset)
    except DepegError as e:
        return X402AuthorizeResponse(
            authorized=False,
            reason=f"STABLECOIN_DEPEG: {e.currency} deviation {e.deviation_pct:.1f}%",
        )

    # Extract domain from resource URL for logging
    resource_url = req.resource or ""
    domain = ""
    if resource_url:
        try:
            domain = urlparse(resource_url).hostname or ""
        except Exception:
            domain = ""

    # Map x402 network to chain name
    chain = _network_to_chain(req.network)

    # Check x402 policy from agent's policy_json
    policy = Policy(**agent.policy) if agent.policy else Policy()
    x402_policy = (agent.policy or {}).get("x402", {})

    # 1. Check chain whitelist
    allowed_chains = x402_policy.get("allowed_chains", ["base", "base-sepolia"])
    if chain and chain not in allowed_chains:
        return X402AuthorizeResponse(
            authorized=False,
            reason="CHAIN_NOT_ALLOWED",
        )

    # 2. Check domain whitelist/blacklist
    if domain:
        blocked_domains = x402_policy.get("blocked_domains", [])
        if blocked_domains and _domain_matches(domain, blocked_domains):
            return X402AuthorizeResponse(
                authorized=False,
                reason="DOMAIN_BLOCKED",
            )
        allowed_domains = x402_policy.get("allowed_domains")
        if allowed_domains and not _domain_matches(domain, allowed_domains):
            return X402AuthorizeResponse(
                authorized=False,
                reason="DOMAIN_NOT_ALLOWED",
            )

    # 3. Check category (same rules as fiat purchases)
    resolved_category, _, _ = await resolve_category(
        body.category, agent.account_id, db
    )
    category = resolved_category
    if policy.allowed_categories and category not in policy.allowed_categories:
        return X402AuthorizeResponse(
            authorized=False,
            reason="CATEGORY_NOT_ALLOWED",
        )
    if (
        policy.blocked_categories
        and not policy.allowed_categories
        and category in policy.blocked_categories
    ):
        return X402AuthorizeResponse(
            authorized=False,
            reason="CATEGORY_BLOCKED",
        )

    # 4. Check per-request limit (from x402 policy or general policy)
    max_per_request = x402_policy.get("max_per_request")
    if max_per_request is not None and amount_usd > Decimal(str(max_per_request)):
        return X402AuthorizeResponse(
            authorized=False,
            reason="AMOUNT_EXCEEDS_PER_REQUEST_LIMIT",
        )
    if policy.per_request_limit is not None and amount_usd > policy.per_request_limit:
        return X402AuthorizeResponse(
            authorized=False,
            reason="AMOUNT_EXCEEDS_PER_REQUEST_LIMIT",
        )

    # 4. Budget checks (reuse existing spending counters, keyed by USD)
    timezone = agent.account.timezone
    currency = "USD"  # x402 budgets always tracked in USD-equivalent

    daily_spent = await get_daily_spent(redis, agent.id, currency, timezone)
    daily_held = await get_daily_held(redis, agent.id, currency, timezone)
    daily_total = daily_spent + daily_held

    if policy.daily_limit and daily_total + amount_usd > policy.daily_limit:
        return X402AuthorizeResponse(
            authorized=False,
            reason="DAILY_BUDGET_EXCEEDED",
        )

    weekly_spent = await get_weekly_spent(redis, agent.id, currency, timezone)
    weekly_held = await get_weekly_held(redis, agent.id, currency, timezone)
    if (
        policy.weekly_limit
        and weekly_spent + weekly_held + amount_usd > policy.weekly_limit
    ):
        return X402AuthorizeResponse(
            authorized=False,
            reason="WEEKLY_BUDGET_EXCEEDED",
        )

    monthly_spent = await get_monthly_spent(redis, agent.id, currency, timezone)
    monthly_held = await get_monthly_held(redis, agent.id, currency, timezone)
    monthly_total = monthly_spent + monthly_held

    if policy.monthly_limit and monthly_total + amount_usd > policy.monthly_limit:
        return X402AuthorizeResponse(
            authorized=False,
            reason="MONTHLY_BUDGET_EXCEEDED",
        )

    # 5. Total budget check
    remaining = agent.budget - agent.spent - agent.held
    if amount_usd > remaining:
        return X402AuthorizeResponse(
            authorized=False,
            reason="BUDGET_EXCEEDED",
        )

    # All checks passed — create authorization record as PurchaseRequest
    expires_at = utcnow() + timedelta(seconds=_AUTH_EXPIRY_SECONDS)
    pr = PurchaseRequest(
        agent_id=agent.id,
        amount=amount_usd,
        currency="USD",
        category=category,
        merchant=domain or None,
        description=resource_url[:2000] if resource_url else None,
        status="auto_approved",
        settlement_method="x402",
        settlement_currency=asset,
        settlement_network=chain,
        amount_usd=amount_usd,
        policy_check={
            "passed": True,
            "checks": [
                {"rule": "x402_chain", "result": "pass", "detail": chain},
                {"rule": "x402_domain", "result": "pass", "detail": domain},
                {"rule": "category", "result": "pass", "detail": category},
                {"rule": "x402_amount", "result": "pass", "detail": str(amount_usd)},
            ],
        },
        expires_at=expires_at,
        reviewed_at=utcnow(),
    )
    db.add(pr)

    # Deduct from budget immediately (same as auto_approved flow)
    await db.execute(
        update(Agent).where(Agent.id == agent.id).values(spent=Agent.spent + amount_usd)
    )
    await db.execute(
        update(Account)
        .where(Account.id == agent.account_id)
        .values(account_spent=Account.account_spent + amount_usd)
    )
    await add_spent(redis, agent.id, amount_usd, currency, timezone)

    await db.commit()
    await db.refresh(pr)
    await db.refresh(agent)

    await publish_event(
        redis,
        agent.id,
        "new_request",
        {
            "request_id": pr.id,
            "status": "auto_approved",
            "amount": str(amount_usd),
            "currency": "USD",
            "category": category,
            "settlement_method": "x402",
        },
    )

    return X402AuthorizeResponse(
        authorized=True,
        authorization_id=pr.id,
        expires_at=expires_at,
        remaining_daily_budget=(
            policy.daily_limit - daily_total - amount_usd
            if policy.daily_limit
            else None
        ),
        remaining_monthly_budget=(
            policy.monthly_limit - monthly_total - amount_usd
            if policy.monthly_limit
            else None
        ),
    )


@router.post("/report", response_model=X402ReportResponse)
async def report_x402_transaction(
    body: X402ReportRequest,
    agent: Agent = Depends(get_agent_by_token),
    db: AsyncSession = Depends(get_db),
):
    """Post-payment audit report. Agent reports tx_hash after settlement."""
    result = await db.execute(
        select(PurchaseRequest).where(
            PurchaseRequest.id == body.authorization_id,
            PurchaseRequest.agent_id == agent.id,
            PurchaseRequest.settlement_method == "x402",
        )
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=404, detail="Authorization not found")

    if pr.tx_hash:
        raise HTTPException(status_code=409, detail="Transaction already reported")

    # Ensure tx_hash is globally unique (prevent one tx closing multiple authorizations)
    existing = await db.execute(
        select(PurchaseRequest).where(
            PurchaseRequest.tx_hash == body.tx_hash,
            PurchaseRequest.id != pr.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Transaction hash already used for another authorization",
        )

    pr.tx_hash = body.tx_hash
    if body.resource_url:
        pr.description = body.resource_url[:2000]
    pr.completed_at = utcnow()
    pr.status = "completed"

    # Correct budget if actual amount differs from authorized amount
    if body.actual_amount_usd is not None:
        pr.actual_amount = body.actual_amount_usd
        authorized = pr.amount
        actual = body.actual_amount_usd
        delta = actual - authorized  # negative = refund, positive = overage

        if delta != 0:
            # Reload agent for account_id and timezone
            agent_result = await db.execute(
                select(Agent)
                .options(joinedload(Agent.account))
                .where(Agent.id == pr.agent_id)
            )
            agent_obj = agent_result.scalar_one()
            timezone = agent_obj.account.timezone
            currency = pr.currency or agent_obj.account.currency

            # Adjust DB counters (clamp to 0 to prevent negative values)
            await db.execute(
                update(Agent)
                .where(Agent.id == pr.agent_id)
                .values(spent=func.greatest(Agent.spent + delta, 0))
            )
            await db.execute(
                update(Account)
                .where(Account.id == agent_obj.account_id)
                .values(account_spent=func.greatest(Account.account_spent + delta, 0))
            )

            redis = get_redis()
            await adjust_spent(redis, pr.agent_id, delta, currency, timezone)
            await adjust_account_spent(
                redis, agent_obj.account_id, delta, currency, timezone
            )

    await db.commit()

    redis = get_redis()
    await publish_event(
        redis,
        agent.id,
        "request_updated",
        {"request_id": pr.id, "status": "completed", "tx_hash": body.tx_hash},
    )

    return X402ReportResponse(recorded=True, transaction_id=pr.id)


@router.get("/budget")
async def get_x402_budget(
    agent: Agent = Depends(get_agent_by_token),
    db: AsyncSession = Depends(get_db),
):
    """Current x402 budget state for the agent."""
    result = await db.execute(
        select(Agent).options(joinedload(Agent.account)).where(Agent.id == agent.id)
    )
    agent = result.scalar_one()

    redis = get_redis()
    timezone = agent.account.timezone
    currency = "USD"

    policy = Policy(**agent.policy) if agent.policy else Policy()
    x402_policy = (agent.policy or {}).get("x402", {})

    daily_spent = await get_daily_spent(redis, agent.id, currency, timezone)
    monthly_spent = await get_monthly_spent(redis, agent.id, currency, timezone)

    # Get wallets
    wallets_result = await db.execute(
        select(AgentWallet).where(
            AgentWallet.agent_id == agent.id,
            AgentWallet.is_active.is_(True),
        )
    )
    wallets = wallets_result.scalars().all()

    return {
        "agent_id": agent.id,
        "budget": str(agent.budget),
        "spent": str(agent.spent),
        "remaining": str(agent.budget - agent.spent - agent.held),
        "x402_policy": {
            "max_per_request": x402_policy.get("max_per_request"),
            "daily_limit": str(policy.daily_limit) if policy.daily_limit else None,
            "daily_spent": str(daily_spent),
            "monthly_limit": (
                str(policy.monthly_limit) if policy.monthly_limit else None
            ),
            "monthly_spent": str(monthly_spent),
            "allowed_domains": x402_policy.get("allowed_domains"),
            "allowed_chains": x402_policy.get(
                "allowed_chains", ["base", "base-sepolia"]
            ),
        },
        "wallets": [
            {
                "address": w.wallet_address,
                "chain": w.chain,
                "provider": w.wallet_provider,
            }
            for w in wallets
        ],
    }


# --- Wallet management ---


@router.post("/wallets", response_model=AgentWalletResponse, status_code=201)
async def register_wallet(
    body: AgentWalletRequest,
    agent: Agent = Depends(get_agent_by_token),
    db: AsyncSession = Depends(get_db),
):
    """Register a wallet address for the agent."""
    # Check if wallet already exists for this chain
    existing = await db.execute(
        select(AgentWallet).where(
            AgentWallet.agent_id == agent.id,
            AgentWallet.chain == body.chain,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Wallet already registered for chain {body.chain}",
        )

    wallet = AgentWallet(
        agent_id=agent.id,
        chain=body.chain,
        wallet_address=body.wallet_address,
        wallet_provider=body.wallet_provider,
    )
    db.add(wallet)
    await db.commit()
    await db.refresh(wallet)

    return AgentWalletResponse(
        wallet_address=wallet.wallet_address,
        chain=wallet.chain,
        wallet_provider=wallet.wallet_provider,
        is_active=wallet.is_active,
        created_at=wallet.created_at,
    )


@router.post("/wallets/create", response_model=AgentWalletResponse, status_code=201)
async def create_wallet_via_cdp(
    agent: Agent = Depends(get_agent_by_token),
    db: AsyncSession = Depends(get_db),
):
    """Create a new wallet via Coinbase Developer Platform and register it.

    Automatically creates an EVM account on Base Sepolia and stores the address.
    """
    from app.services.wallet_provider import WalletProviderError, create_wallet

    chain = "base-sepolia"

    # Check if wallet already exists for this chain
    existing = await db.execute(
        select(AgentWallet).where(
            AgentWallet.agent_id == agent.id,
            AgentWallet.chain == chain,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Wallet already registered for chain {chain}",
        )

    try:
        address = await create_wallet()
    except WalletProviderError as e:
        raise HTTPException(status_code=503, detail=str(e))

    wallet = AgentWallet(
        agent_id=agent.id,
        chain=chain,
        wallet_address=address,
        wallet_provider="coinbase",
    )
    db.add(wallet)
    await db.commit()
    await db.refresh(wallet)

    return AgentWalletResponse(
        wallet_address=wallet.wallet_address,
        chain=wallet.chain,
        wallet_provider=wallet.wallet_provider,
        is_active=wallet.is_active,
        created_at=wallet.created_at,
    )


@router.get("/wallets", response_model=list[AgentWalletResponse])
async def list_wallets(
    agent: Agent = Depends(get_agent_by_token),
    db: AsyncSession = Depends(get_db),
):
    """List agent's registered wallets."""
    result = await db.execute(
        select(AgentWallet).where(AgentWallet.agent_id == agent.id)
    )
    wallets = result.scalars().all()
    return [
        AgentWalletResponse(
            wallet_address=w.wallet_address,
            chain=w.chain,
            wallet_provider=w.wallet_provider,
            is_active=w.is_active,
            created_at=w.created_at,
        )
        for w in wallets
    ]


# --- Helpers ---


def _network_to_chain(network: str) -> str:
    """Convert x402 CAIP-2 network identifier to chain name."""
    _MAP = {
        "eip155:8453": "base",
        "eip155:84532": "base-sepolia",
        "eip155:1": "ethereum",
        "solana:mainnet": "solana",
    }
    return _MAP.get(network, network)


def _domain_matches(domain: str, patterns: list[str]) -> bool:
    """Check if domain matches any pattern (supports *.example.com wildcards)."""
    for pattern in patterns:
        if pattern.startswith("*."):
            suffix = pattern[1:]  # .example.com
            if domain == pattern[2:] or domain.endswith(suffix):
                return True
        elif domain == pattern:
            return True
    return False
