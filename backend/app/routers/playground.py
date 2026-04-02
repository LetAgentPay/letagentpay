"""Public playground endpoints — no authentication required.

Provides a temporary sandbox experience where visitors can try the API
without signing up. Sessions are rate-limited and time-bounded.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.playground import create_session, get_session

router = APIRouter(prefix="/api/v1/playground", tags=["playground"])


def _require_playground():
    """Guard: fail fast if playground is disabled."""
    if not settings.playground_enabled:
        raise HTTPException(status_code=404, detail="Playground is not available")


def _client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind a reverse proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/session")
async def create_playground_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_playground),
):
    """Create a new playground session with a temporary demo agent.

    Rate-limited to 3 sessions per IP per 10 minutes.
    Each session lasts 15 minutes and allows up to 20 requests.
    """
    ip = _client_ip(request)
    try:
        session = await create_session(ip, db)
    except ValueError as e:
        raise HTTPException(status_code=429, detail=str(e))
    return session


@router.get("/session/{session_id}")
async def get_playground_session(
    session_id: str,
    _: None = Depends(_require_playground),
):
    """Get the status of an existing playground session."""
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session expired or not found")
    return session
