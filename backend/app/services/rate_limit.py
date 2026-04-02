import redis.asyncio as aioredis
from fastapi import HTTPException

# Lua script: atomically increment counter and set TTL on first request.
# Prevents race condition where TTL is never set if multiple requests
# arrive before the first expire() call.
_RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


async def check_rate_limit(
    redis: aioredis.Redis,
    key: str,
    max_requests: int,
    window_seconds: int,
) -> None:
    """Sliding window rate limiter using Redis (atomic via Lua script)."""
    current = await redis.eval(
        _RATE_LIMIT_SCRIPT, 1, key, window_seconds
    )  # type: ignore[misc]
    if current > max_requests:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
        )
