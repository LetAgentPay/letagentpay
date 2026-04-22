import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_account, get_owner_agent
from app.models import Account
from app.redis import get_redis

router = APIRouter(prefix="/api/v1/agents/{agent_id}/events", tags=["events"])


async def _event_generator(agent_id: str, request: Request):
    redis = get_redis()
    pubsub = redis.pubsub()
    channel = f"channel:agent:{agent_id}"
    await pubsub.subscribe(channel)

    heartbeat_sec = 15
    queue: asyncio.Queue[str] = asyncio.Queue()

    async def _reader():
        """Read from pubsub.listen() and push to queue instantly."""
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    await queue.put(data)
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(_reader())

    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                data = await asyncio.wait_for(queue.get(), timeout=heartbeat_sec)
                yield f"data: {data.replace(chr(10), '')}\n\n"
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
    finally:
        task.cancel()
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()  # type: ignore[attr-defined]


@router.get("")
async def agent_events(
    agent_id: str,
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_owner_agent(agent_id, account, db)
    resolved_agent_id = agent.id
    # Close the DB session before starting long-lived SSE stream
    # to avoid holding an idle transaction (ACCESS SHARE lock) for hours,
    # which blocks ALTER TABLE during migrations.
    await db.close()

    return StreamingResponse(
        _event_generator(resolved_agent_id, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
