from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from project root (one level up from backend/)
_backend_dir = Path(__file__).resolve().parent.parent
_root_dir = _backend_dir.parent
_env_file = (
    _root_dir / ".env" if (_root_dir / ".env").exists() else _backend_dir / ".env"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_env_file), env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = (
        "postgresql+asyncpg://letagentpay:letagentpay@localhost:5434/letagentpay"
    )

    # Redis
    redis_url: str = "redis://localhost:6380"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_days: int = 7
    magic_link_expire_minutes: int = 15
    magic_link_base_url: str = "http://localhost:3000/auth/verify"

    # Email
    resend_api_key: str = ""
    email_from: str = "LetAgentPay <noreply@letagentpay.com>"

    # AI
    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-4-20250514"

    # Web Push (VAPID)
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_contact_email: str = "admin@letagentpay.com"

    # Stripe / Billing
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""
    stripe_pro_yearly_price_id: str = ""
    pro_price: float = 0.00  # 0 = free for early adopters
    pro_yearly_price: float = 0.00  # 0 = not available

    # Admin
    admin_emails: str = ""

    # Self-hosted mode
    self_hosted: bool = False
    admin_password: str = ""  # Password login for self-hosted (instead of magic link)

    # Cookie
    cookie_secure: bool = False

    # CORS
    frontend_url: str = "http://localhost:3000"

    # App version (set via APP_VERSION env var in Docker)
    app_version: str = "dev"

    # Playground (public demo)
    playground_enabled: bool = False
    playground_session_ttl_minutes: int = 15
    playground_max_requests: int = 20
    playground_budget: float = 500.0

    # Telegram (notifications)
    telegram_bot_token: str = ""
    telegram_admin_chat_id: str = ""  # Internal monitoring: new signups etc.


settings = Settings()

# Fail fast if JWT secret is not configured in production
if settings.jwt_secret == "change-me-in-production" and settings.cookie_secure:
    raise RuntimeError(
        "JWT_SECRET must be set in production. "
        "Update your .env file with a secure random value."
    )
