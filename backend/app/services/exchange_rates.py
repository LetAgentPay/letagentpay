"""Lightweight exchange rate service for policy accounting.

Not a trading engine — just reference rates for budget tracking.
All budgets and spend counters are in USD-equivalent.
"""

import logging
from decimal import Decimal

import httpx
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Cache TTL: 15s for crypto pairs, 300s for fiat
_CRYPTO_TTL = 15
_FIAT_TTL = 300

# Stablecoin depeg thresholds
_DEPEG_WARNING = Decimal("0.005")  # 0.5%
_DEPEG_PAUSE = Decimal("0.01")  # 1%

# Stablecoins pegged to USD (expected rate ~1.0)
_USD_PEGGED = {"USDC", "USDT"}

_HTTP_TIMEOUT = 5.0


class DepegError(Exception):
    """Raised when a stablecoin deviates >1% from peg."""

    def __init__(self, currency: str, rate: Decimal, deviation_pct: Decimal):
        self.currency = currency
        self.rate = rate
        self.deviation_pct = deviation_pct
        super().__init__(
            f"{currency} depeg: rate={rate}, deviation={deviation_pct:.2f}%"
        )


async def to_usd(
    redis: aioredis.Redis,
    amount: Decimal,
    currency: str,
) -> Decimal:
    """Convert any amount to USD-equivalent for budget tracking."""
    if currency == "USD":
        return amount

    # USDC/USDT → treat as 1:1 with depeg check
    if currency in _USD_PEGGED:
        rate = await get_rate(redis, f"{currency}/USD")
        _check_depeg(currency, rate, Decimal("1.0"))
        return amount * rate

    rate = await get_rate(redis, f"{currency}/USD")
    return amount * rate


async def get_rate(redis: aioredis.Redis, pair: str) -> Decimal:
    """Get exchange rate. Redis cache → Coinbase → CoinGecko fallback."""
    cache_key = f"rate:{pair}"
    cached = await redis.get(cache_key)
    if cached:
        return Decimal(cached)

    rate = await _fetch_coinbase(pair)
    if rate is None:
        rate = await _fetch_coingecko(pair)
    if rate is None:
        raise ValueError(f"Could not fetch rate for {pair}")

    is_fiat = "/" in pair and not any(
        s in pair for s in ("USDC", "USDT", "EURC", "SOL", "ETH")
    )
    ttl = _FIAT_TTL if is_fiat else _CRYPTO_TTL
    await redis.setex(cache_key, ttl, str(rate))

    return rate


def _check_depeg(currency: str, rate: Decimal, expected: Decimal) -> None:
    """Check stablecoin peg deviation."""
    if expected == 0:
        return
    deviation = abs(rate - expected) / expected
    if deviation > _DEPEG_PAUSE:
        raise DepegError(
            currency=currency,
            rate=rate,
            deviation_pct=deviation * 100,
        )
    if deviation > _DEPEG_WARNING:
        logger.warning(
            "Stablecoin %s deviation: rate=%s, expected=%s, deviation=%.2f%%",
            currency,
            rate,
            expected,
            deviation * 100,
        )


async def _fetch_coinbase(pair: str) -> Decimal | None:
    """Fetch rate from Coinbase API. Returns None on failure."""
    # Coinbase format: BTC-USD, USDC-USD, ETH-USD
    base, quote = pair.split("/")
    url = f"https://api.coinbase.com/v2/exchange-rates?currency={base}"
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            rate_str = data["data"]["rates"].get(quote)
            if rate_str:
                return Decimal(rate_str)
    except Exception:
        logger.warning("Coinbase rate fetch failed for %s", pair, exc_info=True)
    return None


async def _fetch_coingecko(pair: str) -> Decimal | None:
    """Fetch rate from CoinGecko API (free tier). Returns None on failure."""
    # Map common symbols to CoinGecko IDs
    _COINGECKO_IDS = {
        "USDC": "usd-coin",
        "USDT": "tether",
        "EURC": "euro-coin",
        "ETH": "ethereum",
        "SOL": "solana",
        "BTC": "bitcoin",
    }
    base, quote = pair.split("/")
    coin_id = _COINGECKO_IDS.get(base)
    if not coin_id:
        return None

    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={coin_id}&vs_currencies={quote.lower()}"
    )
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            price = data.get(coin_id, {}).get(quote.lower())
            if price is not None:
                return Decimal(str(price))
    except Exception:
        logger.warning("CoinGecko rate fetch failed for %s", pair, exc_info=True)
    return None
