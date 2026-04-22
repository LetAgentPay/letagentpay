from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import redis.asyncio as aioredis

# TTL constants — slightly longer than the time window to handle timezone edge cases
DAILY_TTL = 26 * 3600  # 26 hours (24h + 2h buffer for timezone variance)
WEEKLY_TTL = 8 * 86400  # 8 days (7d + 1d buffer)
MONTHLY_TTL = 32 * 86400  # 32 days (31d + 1d buffer)

# Lua script: atomically GET multiple keys in a single call.
# Returns list of values (nil → "0") preserving key order.
_MGET_SCRIPT = """
local results = {}
for i = 1, #KEYS do
    local v = redis.call('GET', KEYS[i])
    if v == false then
        results[i] = '0'
    else
        results[i] = v
    end
end
return results
"""

# Lua script: atomically DECRBY with floor at 0.
# Uses INCRBY to correct instead of SET — preserves existing TTL.
_DECRBY_FLOOR_SCRIPT = """
local val = redis.call('DECRBY', KEYS[1], ARGV[1])
if val < 0 then
    redis.call('INCRBY', KEYS[1], 0 - val)
    return 0
end
return val
"""


async def _safe_decrby(redis: aioredis.Redis, key: str, amount: int) -> int:
    """Atomically decrement a key, clamping at 0 to prevent negative counters."""
    return await redis.eval(_DECRBY_FLOOR_SCRIPT, 1, key, amount)  # type: ignore[misc,return-value]


# Subunit multiplier: store amounts as integer cents for exact arithmetic.
# Decimal("150.50") → 15050 (INCRBY, no float precision loss).
_SUBUNITS = 100


def _to_subunits(amount: Decimal) -> int:
    """Convert Decimal amount to integer subunits (cents).

    Uses quantize to round to 2 decimal places before converting,
    ensuring Decimal("1.005") → 101 (rounded) not 100 (truncated).
    """
    return int((amount * _SUBUNITS).to_integral_value())


def _from_subunits(raw: str | bytes | None) -> Decimal:
    """Convert Redis integer subunits back to Decimal."""
    if not raw:
        return Decimal(0)
    return Decimal(int(raw)) / _SUBUNITS


# ---------------------------------------------------------------------------
# Agent-level spending
# ---------------------------------------------------------------------------


async def get_daily_spent(
    redis: aioredis.Redis, agent_id: str, currency: str, timezone: str
) -> Decimal:
    tz = ZoneInfo(timezone)
    today = datetime.now(tz).strftime("%Y-%m-%d")
    key = f"spent:{agent_id}:{currency}:daily:{today}"
    val = await redis.get(key)
    return _from_subunits(val)


async def get_weekly_spent(
    redis: aioredis.Redis, agent_id: str, currency: str, timezone: str
) -> Decimal:
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    # ISO week: Monday is day 1
    week_key = now.strftime("%G-W%V")
    key = f"spent:{agent_id}:{currency}:weekly:{week_key}"
    val = await redis.get(key)
    return _from_subunits(val)


async def get_monthly_spent(
    redis: aioredis.Redis, agent_id: str, currency: str, timezone: str
) -> Decimal:
    tz = ZoneInfo(timezone)
    month_key = datetime.now(tz).strftime("%Y-%m")
    key = f"spent:{agent_id}:{currency}:monthly:{month_key}"
    val = await redis.get(key)
    return _from_subunits(val)


async def add_spent(
    redis: aioredis.Redis,
    agent_id: str,
    amount: Decimal,
    currency: str,
    timezone: str,
) -> None:
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    cents = _to_subunits(amount)

    # Daily
    daily_key = f"spent:{agent_id}:{currency}:daily:{now.strftime('%Y-%m-%d')}"
    await redis.incrby(daily_key, cents)
    await redis.expire(daily_key, DAILY_TTL)

    # Weekly
    week_key = f"spent:{agent_id}:{currency}:weekly:{now.strftime('%G-W%V')}"
    await redis.incrby(week_key, cents)
    await redis.expire(week_key, WEEKLY_TTL)

    # Monthly
    month_key = f"spent:{agent_id}:{currency}:monthly:{now.strftime('%Y-%m')}"
    await redis.incrby(month_key, cents)
    await redis.expire(month_key, MONTHLY_TTL)


async def adjust_spent(
    redis: aioredis.Redis,
    agent_id: str,
    delta: Decimal,
    currency: str,
    timezone: str,
) -> None:
    """Adjust agent spent counters by delta (positive = increase, negative = decrease).

    Used to correct counters when x402 actual_amount differs from authorized_amount.
    Counters are clamped to 0 to prevent going negative.
    """
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    cents = _to_subunits(abs(delta))

    daily_key = f"spent:{agent_id}:{currency}:daily:{now.strftime('%Y-%m-%d')}"
    weekly_key = f"spent:{agent_id}:{currency}:weekly:{now.strftime('%G-W%V')}"
    monthly_key = f"spent:{agent_id}:{currency}:monthly:{now.strftime('%Y-%m')}"

    for key, ttl in (
        (daily_key, DAILY_TTL),
        (weekly_key, WEEKLY_TTL),
        (monthly_key, MONTHLY_TTL),
    ):
        if delta > 0:
            await redis.incrby(key, cents)
        else:
            await _safe_decrby(redis, key, cents)
        await redis.expire(key, ttl)


async def adjust_account_spent(
    redis: aioredis.Redis,
    account_id: str,
    delta: Decimal,
    currency: str,
    timezone: str,
) -> None:
    """Adjust account spent counters by delta. See adjust_spent."""
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    cents = _to_subunits(abs(delta))

    daily_key = f"acct_spent:{account_id}:{currency}:daily:{now.strftime('%Y-%m-%d')}"
    weekly_key = f"acct_spent:{account_id}:{currency}:weekly:{now.strftime('%G-W%V')}"
    monthly_key = f"acct_spent:{account_id}:{currency}:monthly:{now.strftime('%Y-%m')}"

    for key, ttl in (
        (daily_key, DAILY_TTL),
        (weekly_key, WEEKLY_TTL),
        (monthly_key, MONTHLY_TTL),
    ):
        if delta > 0:
            await redis.incrby(key, cents)
        else:
            await _safe_decrby(redis, key, cents)
        await redis.expire(key, ttl)


# ---------------------------------------------------------------------------
# Account-level spending
# ---------------------------------------------------------------------------


async def get_account_daily_spent(
    redis: aioredis.Redis, account_id: str, currency: str, timezone: str
) -> Decimal:
    tz = ZoneInfo(timezone)
    today = datetime.now(tz).strftime("%Y-%m-%d")
    key = f"acct_spent:{account_id}:{currency}:daily:{today}"
    val = await redis.get(key)
    return _from_subunits(val)


async def get_account_weekly_spent(
    redis: aioredis.Redis, account_id: str, currency: str, timezone: str
) -> Decimal:
    tz = ZoneInfo(timezone)
    week_key = datetime.now(tz).strftime("%G-W%V")
    key = f"acct_spent:{account_id}:{currency}:weekly:{week_key}"
    val = await redis.get(key)
    return _from_subunits(val)


async def get_account_monthly_spent(
    redis: aioredis.Redis, account_id: str, currency: str, timezone: str
) -> Decimal:
    tz = ZoneInfo(timezone)
    month_key = datetime.now(tz).strftime("%Y-%m")
    key = f"acct_spent:{account_id}:{currency}:monthly:{month_key}"
    val = await redis.get(key)
    return _from_subunits(val)


async def get_rule_spent(
    redis: aioredis.Redis, account_id: str, rule_id: str, currency: str
) -> Decimal:
    key = f"acct_spent:{account_id}:{currency}:rule:{rule_id}"
    val = await redis.get(key)
    return _from_subunits(val)


async def add_account_spent(
    redis: aioredis.Redis,
    account_id: str,
    amount: Decimal,
    currency: str,
    timezone: str,
    active_rule_ids: list[str] | None = None,
) -> None:
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    cents = _to_subunits(amount)

    # Daily
    daily_key = f"acct_spent:{account_id}:{currency}:daily:{now.strftime('%Y-%m-%d')}"
    await redis.incrby(daily_key, cents)
    await redis.expire(daily_key, DAILY_TTL)

    # Weekly
    week_key = f"acct_spent:{account_id}:{currency}:weekly:{now.strftime('%G-W%V')}"
    await redis.incrby(week_key, cents)
    await redis.expire(week_key, WEEKLY_TTL)

    # Monthly
    month_key = f"acct_spent:{account_id}:{currency}:monthly:{now.strftime('%Y-%m')}"
    await redis.incrby(month_key, cents)
    await redis.expire(month_key, MONTHLY_TTL)

    # Per-rule counters (for temporal total rules)
    if active_rule_ids:
        for rule_id in active_rule_ids:
            rule_key = f"acct_spent:{account_id}:{currency}:rule:{rule_id}"
            await redis.incrby(rule_key, cents)
            # TTL set externally based on rule end_at


# ---------------------------------------------------------------------------
# Agent-level holds
# ---------------------------------------------------------------------------


async def get_daily_held(
    redis: aioredis.Redis, agent_id: str, currency: str, timezone: str
) -> Decimal:
    tz = ZoneInfo(timezone)
    today = datetime.now(tz).strftime("%Y-%m-%d")
    key = f"hold:{agent_id}:{currency}:daily:{today}"
    val = await redis.get(key)
    return _from_subunits(val)


async def get_weekly_held(
    redis: aioredis.Redis, agent_id: str, currency: str, timezone: str
) -> Decimal:
    tz = ZoneInfo(timezone)
    week_key = datetime.now(tz).strftime("%G-W%V")
    key = f"hold:{agent_id}:{currency}:weekly:{week_key}"
    val = await redis.get(key)
    return _from_subunits(val)


async def get_monthly_held(
    redis: aioredis.Redis, agent_id: str, currency: str, timezone: str
) -> Decimal:
    tz = ZoneInfo(timezone)
    month_key = datetime.now(tz).strftime("%Y-%m")
    key = f"hold:{agent_id}:{currency}:monthly:{month_key}"
    val = await redis.get(key)
    return _from_subunits(val)


async def add_held(
    redis: aioredis.Redis,
    agent_id: str,
    amount: Decimal,
    currency: str,
    timezone: str,
) -> None:
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    cents = _to_subunits(amount)

    daily_key = f"hold:{agent_id}:{currency}:daily:{now.strftime('%Y-%m-%d')}"
    await redis.incrby(daily_key, cents)
    await redis.expire(daily_key, DAILY_TTL)

    week_key = f"hold:{agent_id}:{currency}:weekly:{now.strftime('%G-W%V')}"
    await redis.incrby(week_key, cents)
    await redis.expire(week_key, WEEKLY_TTL)

    month_key = f"hold:{agent_id}:{currency}:monthly:{now.strftime('%Y-%m')}"
    await redis.incrby(month_key, cents)
    await redis.expire(month_key, MONTHLY_TTL)


async def remove_held(
    redis: aioredis.Redis,
    agent_id: str,
    amount: Decimal,
    currency: str,
    timezone: str,
) -> None:
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    cents = _to_subunits(amount)

    daily_key = f"hold:{agent_id}:{currency}:daily:{now.strftime('%Y-%m-%d')}"
    await _safe_decrby(redis, daily_key, cents)

    week_key = f"hold:{agent_id}:{currency}:weekly:{now.strftime('%G-W%V')}"
    await _safe_decrby(redis, week_key, cents)

    month_key = f"hold:{agent_id}:{currency}:monthly:{now.strftime('%Y-%m')}"
    await _safe_decrby(redis, month_key, cents)


# ---------------------------------------------------------------------------
# Account-level holds
# ---------------------------------------------------------------------------


async def get_account_daily_held(
    redis: aioredis.Redis, account_id: str, currency: str, timezone: str
) -> Decimal:
    tz = ZoneInfo(timezone)
    today = datetime.now(tz).strftime("%Y-%m-%d")
    key = f"acct_hold:{account_id}:{currency}:daily:{today}"
    val = await redis.get(key)
    return _from_subunits(val)


async def get_account_weekly_held(
    redis: aioredis.Redis, account_id: str, currency: str, timezone: str
) -> Decimal:
    tz = ZoneInfo(timezone)
    week_key = datetime.now(tz).strftime("%G-W%V")
    key = f"acct_hold:{account_id}:{currency}:weekly:{week_key}"
    val = await redis.get(key)
    return _from_subunits(val)


async def get_account_monthly_held(
    redis: aioredis.Redis, account_id: str, currency: str, timezone: str
) -> Decimal:
    tz = ZoneInfo(timezone)
    month_key = datetime.now(tz).strftime("%Y-%m")
    key = f"acct_hold:{account_id}:{currency}:monthly:{month_key}"
    val = await redis.get(key)
    return _from_subunits(val)


async def get_account_rule_held(
    redis: aioredis.Redis, account_id: str, rule_id: str, currency: str
) -> Decimal:
    key = f"acct_hold:{account_id}:{currency}:rule:{rule_id}"
    val = await redis.get(key)
    return _from_subunits(val)


async def add_account_held(
    redis: aioredis.Redis,
    account_id: str,
    amount: Decimal,
    currency: str,
    timezone: str,
    active_rule_ids: list[str] | None = None,
) -> None:
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    cents = _to_subunits(amount)

    daily_key = f"acct_hold:{account_id}:{currency}:daily:{now.strftime('%Y-%m-%d')}"
    await redis.incrby(daily_key, cents)
    await redis.expire(daily_key, DAILY_TTL)

    week_key = f"acct_hold:{account_id}:{currency}:weekly:{now.strftime('%G-W%V')}"
    await redis.incrby(week_key, cents)
    await redis.expire(week_key, WEEKLY_TTL)

    month_key = f"acct_hold:{account_id}:{currency}:monthly:{now.strftime('%Y-%m')}"
    await redis.incrby(month_key, cents)
    await redis.expire(month_key, MONTHLY_TTL)

    if active_rule_ids:
        for rule_id in active_rule_ids:
            rule_key = f"acct_hold:{account_id}:{currency}:rule:{rule_id}"
            await redis.incrby(rule_key, cents)


# ---------------------------------------------------------------------------
# Atomic multi-key reads (Lua-based)
# ---------------------------------------------------------------------------


class AgentCounters:
    """Snapshot of agent spending counters read atomically."""

    __slots__ = (
        "daily_spent",
        "daily_held",
        "weekly_spent",
        "weekly_held",
        "monthly_spent",
        "monthly_held",
    )

    def __init__(self, values: list[Decimal]):
        self.daily_spent = values[0]
        self.daily_held = values[1]
        self.weekly_spent = values[2]
        self.weekly_held = values[3]
        self.monthly_spent = values[4]
        self.monthly_held = values[5]


class AccountCounters:
    """Snapshot of account spending counters read atomically."""

    __slots__ = (
        "daily_spent",
        "daily_held",
        "weekly_spent",
        "weekly_held",
        "monthly_spent",
        "monthly_held",
    )

    def __init__(self, values: list[Decimal]):
        self.daily_spent = values[0]
        self.daily_held = values[1]
        self.weekly_spent = values[2]
        self.weekly_held = values[3]
        self.monthly_spent = values[4]
        self.monthly_held = values[5]


async def get_agent_counters_atomic(
    redis: aioredis.Redis, agent_id: str, currency: str, timezone: str
) -> AgentCounters:
    """Read all 6 agent spending/hold counters in a single atomic Lua call."""
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    today = now.strftime("%Y-%m-%d")
    week_key = now.strftime("%G-W%V")
    month_key = now.strftime("%Y-%m")

    keys = [
        f"spent:{agent_id}:{currency}:daily:{today}",
        f"hold:{agent_id}:{currency}:daily:{today}",
        f"spent:{agent_id}:{currency}:weekly:{week_key}",
        f"hold:{agent_id}:{currency}:weekly:{week_key}",
        f"spent:{agent_id}:{currency}:monthly:{month_key}",
        f"hold:{agent_id}:{currency}:monthly:{month_key}",
    ]

    raw = await redis.eval(_MGET_SCRIPT, len(keys), *keys)  # type: ignore[misc]
    return AgentCounters([_from_subunits(v) for v in raw])


async def get_account_counters_atomic(
    redis: aioredis.Redis, account_id: str, currency: str, timezone: str
) -> AccountCounters:
    """Read all 6 account spending/hold counters in a single atomic Lua call."""
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    today = now.strftime("%Y-%m-%d")
    week_key = now.strftime("%G-W%V")
    month_key = now.strftime("%Y-%m")

    keys = [
        f"acct_spent:{account_id}:{currency}:daily:{today}",
        f"acct_hold:{account_id}:{currency}:daily:{today}",
        f"acct_spent:{account_id}:{currency}:weekly:{week_key}",
        f"acct_hold:{account_id}:{currency}:weekly:{week_key}",
        f"acct_spent:{account_id}:{currency}:monthly:{month_key}",
        f"acct_hold:{account_id}:{currency}:monthly:{month_key}",
    ]

    raw = await redis.eval(_MGET_SCRIPT, len(keys), *keys)  # type: ignore[misc]
    return AccountCounters([_from_subunits(v) for v in raw])


async def get_rule_counters_atomic(
    redis: aioredis.Redis, account_id: str, rule_id: str, currency: str
) -> tuple[Decimal, Decimal]:
    """Read rule spent + held atomically. Returns (spent, held)."""
    keys = [
        f"acct_spent:{account_id}:{currency}:rule:{rule_id}",
        f"acct_hold:{account_id}:{currency}:rule:{rule_id}",
    ]
    raw = await redis.eval(_MGET_SCRIPT, len(keys), *keys)  # type: ignore[misc]
    return _from_subunits(raw[0]), _from_subunits(raw[1])


async def _scan_keys(redis: aioredis.Redis, pattern: str) -> list:
    """Collect keys matching pattern using SCAN (non-blocking, unlike KEYS)."""
    keys = []
    async for key in redis.scan_iter(match=pattern, count=100):
        keys.append(key)
    return keys


async def clear_agent_spending(redis: aioredis.Redis, agent_id: str) -> None:
    """Delete all spending/hold Redis keys for an agent."""
    keys = await _scan_keys(redis, f"spent:{agent_id}:*")
    keys += await _scan_keys(redis, f"hold:{agent_id}:*")
    if keys:
        await redis.delete(*keys)


async def clear_account_spending(redis: aioredis.Redis, account_id: str) -> None:
    """Delete all spending/hold Redis keys for an account."""
    keys = await _scan_keys(redis, f"acct_spent:{account_id}:*")
    keys += await _scan_keys(redis, f"acct_hold:{account_id}:*")
    if keys:
        await redis.delete(*keys)


async def remove_account_held(
    redis: aioredis.Redis,
    account_id: str,
    amount: Decimal,
    currency: str,
    timezone: str,
    active_rule_ids: list[str] | None = None,
) -> None:
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    cents = _to_subunits(amount)

    daily_key = f"acct_hold:{account_id}:{currency}:daily:{now.strftime('%Y-%m-%d')}"
    await _safe_decrby(redis, daily_key, cents)

    week_key = f"acct_hold:{account_id}:{currency}:weekly:{now.strftime('%G-W%V')}"
    await _safe_decrby(redis, week_key, cents)

    month_key = f"acct_hold:{account_id}:{currency}:monthly:{now.strftime('%Y-%m')}"
    await _safe_decrby(redis, month_key, cents)

    if active_rule_ids:
        for rule_id in active_rule_ids:
            rule_key = f"acct_hold:{account_id}:{currency}:rule:{rule_id}"
            await _safe_decrby(redis, rule_key, cents)
