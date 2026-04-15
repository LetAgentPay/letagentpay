"""Tests for x402 authorization gateway."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, Agent, AgentWallet, PurchaseRequest


@pytest.fixture
async def x402_agent(db: AsyncSession, account: Account) -> Agent:
    """Agent with x402-compatible policy."""
    ag = Agent(
        account_id=account.id,
        name="x402 Agent",
        budget=Decimal("1000.00"),
        policy={
            "daily_limit": 100,
            "monthly_limit": 500,
            "per_request_limit": 50,
            "x402": {
                "allowed_chains": ["base", "base-sepolia"],
                "blocked_domains": ["evil.com"],
                "max_per_request": 10,
            },
        },
    )
    db.add(ag)
    await db.commit()
    await db.refresh(ag)
    return ag


def _auth_header(agent: Agent) -> dict[str, str]:
    return {"Authorization": f"Bearer {agent.token}"}


class TestX402Authorize:
    """POST /api/v1/x402/authorize"""

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("0.05"),
    )
    async def test_authorize_success(self, mock_to_usd, client, x402_agent):
        resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "50000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                    "resource": "https://api.example.com/data",
                },
                "max_amount_usd": 0.05,
            },
            headers=_auth_header(x402_agent),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["authorized"] is True
        assert data["authorization_id"] is not None
        assert data["expires_at"] is not None

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("0.05"),
    )
    async def test_authorize_creates_purchase_request(
        self, mock_to_usd, client, db, x402_agent
    ):
        resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "50000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                    "resource": "https://api.example.com/data",
                },
                "max_amount_usd": 0.05,
            },
            headers=_auth_header(x402_agent),
        )
        data = resp.json()
        pr_id = data["authorization_id"]

        result = await db.execute(
            select(PurchaseRequest).where(PurchaseRequest.id == pr_id)
        )
        pr = result.scalar_one()
        assert pr.settlement_method == "x402"
        assert pr.settlement_currency == "USDC"
        assert pr.settlement_network == "base-sepolia"
        assert pr.category == "api"
        assert pr.status == "auto_approved"

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("0.05"),
    )
    async def test_authorize_blocked_domain(self, mock_to_usd, client, x402_agent):
        resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "50000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                    "resource": "https://evil.com/api",
                },
                "max_amount_usd": 0.05,
            },
            headers=_auth_header(x402_agent),
        )
        data = resp.json()
        assert data["authorized"] is False
        assert data["reason"] == "DOMAIN_BLOCKED"

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("0.05"),
    )
    async def test_authorize_chain_not_allowed(self, mock_to_usd, client, x402_agent):
        resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "solana:mainnet",
                    "amount": "50000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                    "resource": "https://api.example.com/data",
                },
                "max_amount_usd": 0.05,
            },
            headers=_auth_header(x402_agent),
        )
        data = resp.json()
        assert data["authorized"] is False
        assert data["reason"] == "CHAIN_NOT_ALLOWED"

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("0.05"),
    )
    async def test_authorize_category_not_allowed(
        self, mock_to_usd, client, db, account
    ):
        """Agent with allowed_categories rejects unlisted category."""
        ag = Agent(
            account_id=account.id,
            name="Category Agent",
            budget=Decimal("1000.00"),
            policy={
                "allowed_categories": ["api", "compute"],
                "x402": {"allowed_chains": ["base-sepolia"]},
            },
        )
        db.add(ag)
        await db.commit()
        await db.refresh(ag)

        resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "50000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                },
                "max_amount_usd": 0.05,
                "category": "gambling",
            },
            headers=_auth_header(ag),
        )
        data = resp.json()
        assert data["authorized"] is False
        assert data["reason"] == "CATEGORY_NOT_ALLOWED"

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("15.00"),
    )
    async def test_authorize_exceeds_per_request_limit(
        self, mock_to_usd, client, x402_agent
    ):
        resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "15000000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                    "resource": "https://api.example.com/data",
                },
                "max_amount_usd": 15.00,
            },
            headers=_auth_header(x402_agent),
        )
        data = resp.json()
        assert data["authorized"] is False
        assert data["reason"] == "AMOUNT_EXCEEDS_PER_REQUEST_LIMIT"

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("5.00"),
    )
    async def test_authorize_deducts_budget(self, mock_to_usd, client, db, x402_agent):
        await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "5000000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                },
                "max_amount_usd": 5.00,
            },
            headers=_auth_header(x402_agent),
        )
        await db.refresh(x402_agent)
        assert x402_agent.spent == Decimal("5.00")

    async def test_authorize_no_auth(self, client):
        resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "50000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                },
                "max_amount_usd": 0.05,
            },
        )
        assert resp.status_code == 401

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("5.00"),
    )
    async def test_authorize_exceeds_total_budget(
        self, mock_to_usd, client, db, x402_agent
    ):
        # Set budget to a small amount so we can exceed it within limits
        x402_agent.budget = Decimal("2.00")
        await db.commit()

        resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "5000000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                },
                "max_amount_usd": 5.00,
            },
            headers=_auth_header(x402_agent),
        )
        data = resp.json()
        assert data["authorized"] is False
        assert data["reason"] == "BUDGET_EXCEEDED"


class TestX402Report:
    """POST /api/v1/x402/report"""

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("0.05"),
    )
    async def test_report_success(self, mock_to_usd, client, db, x402_agent):
        # First authorize
        auth_resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "50000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                },
                "max_amount_usd": 0.05,
            },
            headers=_auth_header(x402_agent),
        )
        auth_id = auth_resp.json()["authorization_id"]

        # Then report
        resp = await client.post(
            "/api/v1/x402/report",
            json={
                "authorization_id": auth_id,
                "tx_hash": "0xabc123def456",
            },
            headers=_auth_header(x402_agent),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["recorded"] is True
        assert data["transaction_id"] == auth_id

        # Verify tx_hash stored
        result = await db.execute(
            select(PurchaseRequest).where(PurchaseRequest.id == auth_id)
        )
        pr = result.scalar_one()
        assert pr.tx_hash == "0xabc123def456"
        assert pr.status == "completed"

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("0.05"),
    )
    async def test_report_duplicate(self, mock_to_usd, client, x402_agent):
        auth_resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "50000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                },
                "max_amount_usd": 0.05,
            },
            headers=_auth_header(x402_agent),
        )
        auth_id = auth_resp.json()["authorization_id"]

        # First report
        await client.post(
            "/api/v1/x402/report",
            json={"authorization_id": auth_id, "tx_hash": "0xabc123"},
            headers=_auth_header(x402_agent),
        )
        # Duplicate report
        resp = await client.post(
            "/api/v1/x402/report",
            json={"authorization_id": auth_id, "tx_hash": "0xdef456"},
            headers=_auth_header(x402_agent),
        )
        assert resp.status_code == 409

    async def test_report_not_found(self, client, x402_agent):
        resp = await client.post(
            "/api/v1/x402/report",
            json={
                "authorization_id": "nonexistent-id",
                "tx_hash": "0xabc123",
            },
            headers=_auth_header(x402_agent),
        )
        assert resp.status_code == 404


class TestX402Budget:
    """GET /api/v1/x402/budget"""

    async def test_get_budget(self, client, x402_agent):
        resp = await client.get(
            "/api/v1/x402/budget",
            headers=_auth_header(x402_agent),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == x402_agent.id
        assert data["budget"] == "1000.00"
        assert data["x402_policy"]["allowed_chains"] == ["base", "base-sepolia"]


class TestX402Wallets:
    """Wallet CRUD endpoints."""

    async def test_register_wallet(self, client, x402_agent):
        resp = await client.post(
            "/api/v1/x402/wallets",
            json={
                "wallet_address": "0x1234567890abcdef",
                "chain": "base",
                "wallet_provider": "coinbase",
            },
            headers=_auth_header(x402_agent),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["wallet_address"] == "0x1234567890abcdef"
        assert data["chain"] == "base"
        assert data["is_active"] is True

    async def test_register_wallet_duplicate_chain(self, client, x402_agent):
        headers = _auth_header(x402_agent)
        await client.post(
            "/api/v1/x402/wallets",
            json={"wallet_address": "0xaaa", "chain": "base"},
            headers=headers,
        )
        resp = await client.post(
            "/api/v1/x402/wallets",
            json={"wallet_address": "0xbbb", "chain": "base"},
            headers=headers,
        )
        assert resp.status_code == 409

    async def test_list_wallets(self, client, db, x402_agent):
        wallet = AgentWallet(
            agent_id=x402_agent.id,
            chain="base-sepolia",
            wallet_address="0xtest",
            wallet_provider="crossmint",
        )
        db.add(wallet)
        await db.commit()

        resp = await client.get(
            "/api/v1/x402/wallets",
            headers=_auth_header(x402_agent),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["chain"] == "base-sepolia"

    async def test_register_wallet_invalid_chain(self, client, x402_agent):
        resp = await client.post(
            "/api/v1/x402/wallets",
            json={"wallet_address": "0xaaa", "chain": "invalid_chain"},
            headers=_auth_header(x402_agent),
        )
        assert resp.status_code == 422


class TestX402EdgeCases:
    """Edge cases and additional scenarios."""

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("0.05"),
    )
    async def test_authorize_with_custom_category(
        self, mock_to_usd, client, db, x402_agent
    ):
        """Category from request is stored on PurchaseRequest."""
        resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "50000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                },
                "max_amount_usd": 0.05,
                "category": "compute",
            },
            headers=_auth_header(x402_agent),
        )
        pr_id = resp.json()["authorization_id"]
        result = await db.execute(
            select(PurchaseRequest).where(PurchaseRequest.id == pr_id)
        )
        assert result.scalar_one().category == "compute"

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("0.05"),
    )
    async def test_authorize_default_category_is_api(
        self, mock_to_usd, client, db, x402_agent
    ):
        """Without category field, defaults to 'api'."""
        resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "50000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                },
                "max_amount_usd": 0.05,
            },
            headers=_auth_header(x402_agent),
        )
        pr_id = resp.json()["authorization_id"]
        result = await db.execute(
            select(PurchaseRequest).where(PurchaseRequest.id == pr_id)
        )
        assert result.scalar_one().category == "api"

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("0.05"),
    )
    async def test_report_with_actual_amount(self, mock_to_usd, client, db, x402_agent):
        """Report with actual_amount_usd stores it on PurchaseRequest."""
        auth_resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "50000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                },
                "max_amount_usd": 0.05,
            },
            headers=_auth_header(x402_agent),
        )
        auth_id = auth_resp.json()["authorization_id"]

        await client.post(
            "/api/v1/x402/report",
            json={
                "authorization_id": auth_id,
                "tx_hash": "0xabc",
                "actual_amount_usd": 0.04,
                "resource_url": "https://api.example.com/result",
            },
            headers=_auth_header(x402_agent),
        )

        result = await db.execute(
            select(PurchaseRequest).where(PurchaseRequest.id == auth_id)
        )
        pr = result.scalar_one()
        assert pr.actual_amount == Decimal("0.04")
        assert pr.description == "https://api.example.com/result"

    @patch(
        "app.routers.x402.to_usd",
        new_callable=AsyncMock,
    )
    async def test_authorize_depeg_rejection(self, mock_to_usd, client, x402_agent):
        """Stablecoin depeg causes rejection."""
        from app.services.exchange_rates import DepegError

        mock_to_usd.side_effect = DepegError("USDC", Decimal("0.94"), Decimal("6.0"))

        resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "50000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                },
                "max_amount_usd": 0.05,
            },
            headers=_auth_header(x402_agent),
        )
        data = resp.json()
        assert data["authorized"] is False
        assert "STABLECOIN_DEPEG" in data["reason"]

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("5.00"),
    )
    async def test_multiple_authorizations_deplete_budget(
        self, mock_to_usd, client, db, x402_agent
    ):
        """Sequential authorizations correctly deplete budget."""
        headers = _auth_header(x402_agent)
        payload = {
            "payment_requirements": {
                "scheme": "exact",
                "network": "eip155:84532",
                "amount": "5000000",
                "asset": "USDC",
                "pay_to": "0xRecipient",
            },
            "max_amount_usd": 5.00,
        }

        # First authorization
        resp1 = await client.post(
            "/api/v1/x402/authorize", json=payload, headers=headers
        )
        assert resp1.json()["authorized"] is True

        # Second authorization
        resp2 = await client.post(
            "/api/v1/x402/authorize", json=payload, headers=headers
        )
        assert resp2.json()["authorized"] is True

        # Verify spent increased by 10
        await db.refresh(x402_agent)
        assert x402_agent.spent == Decimal("10.00")

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("0.05"),
    )
    async def test_authorize_allowed_domain_pass(
        self, mock_to_usd, client, db, account
    ):
        """Agent with allowed_domains passes matching domain."""
        ag = Agent(
            account_id=account.id,
            name="Domain Agent",
            budget=Decimal("1000.00"),
            policy={
                "x402": {
                    "allowed_chains": ["base-sepolia"],
                    "allowed_domains": ["*.example.com"],
                },
            },
        )
        db.add(ag)
        await db.commit()
        await db.refresh(ag)

        resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "50000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                    "resource": "https://api.example.com/data",
                },
                "max_amount_usd": 0.05,
            },
            headers=_auth_header(ag),
        )
        assert resp.json()["authorized"] is True

    @patch(
        "app.services.exchange_rates.to_usd",
        new_callable=AsyncMock,
        return_value=Decimal("0.05"),
    )
    async def test_authorize_allowed_domain_reject(
        self, mock_to_usd, client, db, account
    ):
        """Agent with allowed_domains rejects non-matching domain."""
        ag = Agent(
            account_id=account.id,
            name="Domain Agent 2",
            budget=Decimal("1000.00"),
            policy={
                "x402": {
                    "allowed_chains": ["base-sepolia"],
                    "allowed_domains": ["*.example.com"],
                },
            },
        )
        db.add(ag)
        await db.commit()
        await db.refresh(ag)

        resp = await client.post(
            "/api/v1/x402/authorize",
            json={
                "payment_requirements": {
                    "scheme": "exact",
                    "network": "eip155:84532",
                    "amount": "50000",
                    "asset": "USDC",
                    "pay_to": "0xRecipient",
                    "resource": "https://other-api.com/data",
                },
                "max_amount_usd": 0.05,
            },
            headers=_auth_header(ag),
        )
        data = resp.json()
        assert data["authorized"] is False
        assert data["reason"] == "DOMAIN_NOT_ALLOWED"


class TestExchangeRateService:
    """Unit tests for exchange rate service."""

    async def test_to_usd_passthrough(self, mock_redis):
        from app.services.exchange_rates import to_usd

        result = await to_usd(mock_redis, Decimal("100"), "USD")
        assert result == Decimal("100")

    @patch("app.services.exchange_rates._fetch_coinbase")
    async def test_to_usd_usdc(self, mock_fetch, mock_redis):
        mock_fetch.return_value = Decimal("1.0001")
        from app.services.exchange_rates import to_usd

        result = await to_usd(mock_redis, Decimal("100"), "USDC")
        assert result == Decimal("100.01")

    @patch("app.services.exchange_rates._fetch_coinbase")
    async def test_depeg_error(self, mock_fetch, mock_redis):
        mock_fetch.return_value = Decimal("0.95")
        from app.services.exchange_rates import DepegError, to_usd

        with pytest.raises(DepegError):
            await to_usd(mock_redis, Decimal("100"), "USDC")

    async def test_rate_cached(self, mock_redis):
        mock_redis._store["rate:ETH/USD"] = "3000.50"
        from app.services.exchange_rates import get_rate

        rate = await get_rate(mock_redis, "ETH/USD")
        assert rate == Decimal("3000.50")


class TestDomainMatching:
    """Unit tests for domain matching helper."""

    def test_exact_match(self):
        from app.routers.x402 import _domain_matches

        assert _domain_matches("evil.com", ["evil.com"]) is True
        assert _domain_matches("good.com", ["evil.com"]) is False

    def test_wildcard_match(self):
        from app.routers.x402 import _domain_matches

        assert _domain_matches("api.example.com", ["*.example.com"]) is True
        assert _domain_matches("example.com", ["*.example.com"]) is True
        assert _domain_matches("other.com", ["*.example.com"]) is False

    def test_subdomain_wildcard(self):
        from app.routers.x402 import _domain_matches

        assert _domain_matches("deep.sub.example.com", ["*.example.com"]) is True


class TestNetworkToChain:
    """Unit tests for CAIP-2 network mapping."""

    def test_known_networks(self):
        from app.routers.x402 import _network_to_chain

        assert _network_to_chain("eip155:8453") == "base"
        assert _network_to_chain("eip155:84532") == "base-sepolia"
        assert _network_to_chain("eip155:1") == "ethereum"
        assert _network_to_chain("solana:mainnet") == "solana"

    def test_unknown_network(self):
        from app.routers.x402 import _network_to_chain

        assert _network_to_chain("eip155:999") == "eip155:999"
