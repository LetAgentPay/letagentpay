import json

import redis.asyncio as aioredis


async def publish_event(
    redis: aioredis.Redis, agent_id: str, event_type: str, data: dict
) -> None:
    payload = json.dumps({"type": event_type, "data": data}, default=str)
    await redis.publish(f"channel:agent:{agent_id}", payload)
