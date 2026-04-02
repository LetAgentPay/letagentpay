from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/public")
async def public_config():
    """Public feature flags consumed by the frontend."""
    return {
        "playground_enabled": settings.playground_enabled,
        "version": settings.app_version,
    }
