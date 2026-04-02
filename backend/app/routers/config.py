import re
from pathlib import Path

from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/api/v1/config", tags=["config"])

_root = Path(__file__).resolve().parent.parent.parent
_version_file = _root / "version.py"
_app_version = "dev"
if _version_file.exists():
    _match = re.search(r'__version__\s*=\s*"(.+?)"', _version_file.read_text())
    if _match:
        _app_version = _match.group(1)


@router.get("/public")
async def public_config():
    """Public feature flags consumed by the frontend."""
    return {
        "playground_enabled": settings.playground_enabled,
        "version": _app_version,
    }
