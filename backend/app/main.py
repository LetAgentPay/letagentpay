import asyncio
import contextlib
import logging
import logging.handlers
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.redis import close_redis, init_redis
from app.services.expiry import expire_pending_requests_loop
from app.services.telegram import setup_webhook as setup_telegram_webhook
from app.services.telegram import start_polling as start_telegram_polling

# ---------------------------------------------------------------------------
# Logging setup — write all logs to logs/backend.log
# ---------------------------------------------------------------------------
_log_dir = Path(__file__).resolve().parent.parent / "logs"
_log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.handlers.RotatingFileHandler(
            _log_dir / "backend.log",
            maxBytes=5_000_000,
            backupCount=3,
        ),
        logging.StreamHandler(),
    ],
)

# Quiet noisy libraries
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


class _HealthCheckFilter(logging.Filter):
    """Suppress repetitive health check log lines."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_HealthCheckFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()

    # Auto-rebuild Redis spending counters if Redis is empty (e.g. after data loss)
    try:
        from app.services.redis_rebuild import (
            check_redis_needs_rebuild,
            rebuild_all_counters,
        )

        if await check_redis_needs_rebuild():
            logging.getLogger(__name__).info(
                "Redis has no spending keys — rebuilding counters from DB"
            )
            result = await rebuild_all_counters()
            logging.getLogger(__name__).info("Redis rebuild complete: %s", result)
    except Exception:
        logging.getLogger(__name__).exception("Failed to auto-rebuild Redis counters")

    expiry_task = asyncio.create_task(expire_pending_requests_loop())

    # Playground: periodic cleanup of expired sessions
    playground_task = None
    if settings.playground_enabled:

        async def _playground_cleanup_loop():
            from app.database import async_session
            from app.services.playground import cleanup_expired_sessions

            while True:
                await asyncio.sleep(1800)  # every 30 minutes
                try:
                    async with async_session() as db:
                        await cleanup_expired_sessions(db)
                except Exception:
                    logging.getLogger(__name__).exception("Playground cleanup failed")

        playground_task = asyncio.create_task(_playground_cleanup_loop())

    # Telegram: use webhook in production, long polling in dev
    telegram_task = None
    if settings.telegram_bot_token:
        if "localhost" in settings.frontend_url:
            telegram_task = asyncio.create_task(start_telegram_polling())
        else:
            await setup_telegram_webhook()

    yield

    expiry_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await expiry_task
    if telegram_task:
        telegram_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await telegram_task
    if playground_task:
        playground_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await playground_task
    await close_redis()


app = FastAPI(
    title="LetAgentPay API",
    version="0.1.0",
    lifespan=lifespan,
)

_cors_origins = [settings.frontend_url]
# In dev, also allow 127.0.0.1 variant so both localhost and 127.0.0.1 work
if "localhost" in settings.frontend_url:
    _cors_origins.append(settings.frontend_url.replace("localhost", "127.0.0.1"))


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response


class SlidingSessionMiddleware(BaseHTTPMiddleware):
    """Refresh JWT cookie when more than 50% of its lifetime has elapsed.

    This turns a fixed 7-day token into a sliding window: the token expires
    7 days after the *last activity*, not 7 days after login.
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        token = request.cookies.get("access_token")
        if not token:
            return response

        try:
            import jwt as pyjwt

            from app.utils import utcnow

            payload = pyjwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
            iat = payload.get("iat")
            exp = payload.get("exp")
            if iat is None or exp is None:
                return response

            now_ts = utcnow().timestamp()
            lifetime = exp - iat
            elapsed = now_ts - iat

            # Refresh when >50% of lifetime has elapsed
            if elapsed > lifetime * 0.5:
                from datetime import timedelta

                new_exp = utcnow() + timedelta(days=settings.access_token_expire_days)
                payload["iat"] = int(utcnow().timestamp())
                payload["exp"] = new_exp
                new_token = pyjwt.encode(
                    payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
                )
                response.set_cookie(
                    key="access_token",
                    value=new_token,
                    httponly=True,
                    secure=settings.cookie_secure,
                    samesite="lax",
                    max_age=settings.access_token_expire_days * 86400,
                )
        except Exception:
            pass  # Never break the response over token refresh

        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SlidingSessionMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Core routers — imported after app creation to avoid circular imports
from app.routers import (  # noqa: E402
    actions,
    agent_api,
    agents,
    auth,
    budget_rules,
    config,
    events,
    me,
    notifications,
    playground,
    policy,
    push,
    requests,
    telegram,
)

app.include_router(config.router)
app.include_router(auth.router)
app.include_router(me.router)
app.include_router(agents.router)
app.include_router(policy.router)
app.include_router(
    actions.router
)  # before requests — /action must match before /{request_id}
app.include_router(requests.router)
app.include_router(agent_api.router)
app.include_router(events.router)
app.include_router(push.router)
app.include_router(budget_rules.router)
app.include_router(notifications.router)
app.include_router(telegram.router)
app.include_router(playground.router)

# Enterprise modules (optional — core works fully standalone without ee/)
# Disabled in self-hosted mode: admin panel, billing, stats are SaaS-only.
if not settings.self_hosted:
    try:
        from ee import register_enterprise

        register_enterprise(app)
    except ImportError:
        pass


@app.get("/health/live")
async def health_live():
    """Liveness probe — returns 200 if the process is running."""
    return {"status": "ok"}


@app.get("/health")
async def health():
    """Readiness probe — checks PostgreSQL and Redis connectivity."""
    from fastapi.responses import JSONResponse
    from sqlalchemy import text

    from app.database import async_session
    from app.redis import get_redis

    checks: dict[str, str] = {}

    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"

    try:
        redis = get_redis()
        await redis.ping()  # type: ignore[misc]
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        content={"status": "ok" if all_ok else "degraded", "checks": checks},
        status_code=200 if all_ok else 503,
    )
