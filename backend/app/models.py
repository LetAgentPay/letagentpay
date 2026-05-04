import hashlib
import secrets
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.utils import utcnow


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    timezone: Mapped[str] = mapped_column(String(50), default="America/New_York")
    plan: Mapped[str] = mapped_column(String(10), default="free")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    all_agents_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    account_spent: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    account_held: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    request_expiry_minutes: Mapped[int] = mapped_column(Integer, default=30)

    signup_landing: Mapped[str | None] = mapped_column(String(64))
    signup_source: Mapped[str | None] = mapped_column(String(64))
    signup_medium: Mapped[str | None] = mapped_column(String(64))
    signup_campaign: Mapped[str | None] = mapped_column(String(128))
    signup_content: Mapped[str | None] = mapped_column(String(128))

    agents: Mapped[list["Agent"]] = relationship(back_populates="account")
    push_subscriptions: Mapped[list["PushSubscription"]] = relationship(
        back_populates="account"
    )
    budget_rules: Mapped[list["BudgetRule"]] = relationship(back_populates="account")
    notification_channels: Mapped[list["NotificationChannel"]] = relationship(
        back_populates="account"
    )
    categories: Mapped[list["Category"]] = relationship(back_populates="account")


def hash_token(token: str) -> str:
    """SHA-256 hash of agent token for secure storage/lookup."""
    return hashlib.sha256(token.encode()).hexdigest()


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="active")
    budget: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    spent: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    held: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    policy: Mapped[dict | None] = mapped_column(JSONB)
    policy_text: Mapped[str | None] = mapped_column(Text)
    token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        default=lambda: f"agt_{secrets.token_urlsafe(32)}",
    )
    token_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    is_sandbox: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_replenish_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_replenish_threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    auto_replenish_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    auto_replenish_max_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    account: Mapped["Account"] = relationship(back_populates="agents")
    requests: Mapped[list["PurchaseRequest"]] = relationship(back_populates="agent")
    policy_logs: Mapped[list["PolicyLog"]] = relationship(back_populates="agent")
    wallets: Mapped[list["AgentWallet"]] = relationship(back_populates="agent")


@event.listens_for(Agent, "before_insert")
def _agent_set_token_hash(mapper, connection, target):
    """Ensure token_hash is set before INSERT (covers column defaults).

    Note: this event fires reliably on sync drivers (psycopg2) and PostgreSQL.
    For async drivers, call ensure_token_hash() after flush as a safety net.
    """
    if target.token and not target.token_hash:
        target.token_hash = hash_token(target.token)


class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    category: Mapped[str] = mapped_column(String(50))
    original_category: Mapped[str | None] = mapped_column(String(100))
    merchant: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    agent_comment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    policy_check: Mapped[dict | None] = mapped_column(JSONB)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    receipt_url: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    category_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Settlement fields (x402 / Stripe / manual)
    settlement_method: Mapped[str | None] = mapped_column(String(20))
    settlement_currency: Mapped[str | None] = mapped_column(String(10))
    settlement_network: Mapped[str | None] = mapped_column(String(30))
    tx_hash: Mapped[str | None] = mapped_column(String(66))
    amount_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))

    agent: Mapped["Agent"] = relationship(back_populates="requests")

    __table_args__ = (
        Index("ix_requests_agent_status", "agent_id", "status"),
        Index("ix_requests_agent_created", "agent_id", "created_at"),
    )


class AgentWallet(Base):
    __tablename__ = "agent_wallets"

    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id"), primary_key=True
    )
    chain: Mapped[str] = mapped_column(String(20), primary_key=True)
    wallet_address: Mapped[str] = mapped_column(String(64), nullable=False)
    wallet_provider: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    agent: Mapped["Agent"] = relationship(back_populates="wallets")


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pair: Mapped[str] = mapped_column(String(20), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    __table_args__ = (Index("ix_rates_pair_time", "pair", "fetched_at"),)


class PolicyLog(Base):
    __tablename__ = "policy_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    user_input: Mapped[str] = mapped_column(Text)
    ai_output: Mapped[dict] = mapped_column(JSONB)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    agent: Mapped["Agent"] = relationship(back_populates="policy_logs")


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    endpoint: Mapped[str] = mapped_column(Text, unique=True)
    p256dh: Mapped[str] = mapped_column(Text)
    auth: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    account: Mapped["Account"] = relationship(back_populates="push_subscriptions")


class BudgetRule(Base):
    __tablename__ = "budget_rules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    limit_type: Mapped[str] = mapped_column(String(20))  # daily|weekly|monthly|total
    limit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    days_of_week: Mapped[list[int] | None] = mapped_column(JSONB, nullable=True)
    start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    account: Mapped["Account"] = relationship(back_populates="budget_rules")


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    channel_type: Mapped[str] = mapped_column(String(20))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    account: Mapped["Account"] = relationship(back_populates="notification_channels")

    __table_args__ = (
        UniqueConstraint("account_id", "channel_type", name="uq_notif_account_type"),
    )


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    channel_type: Mapped[str] = mapped_column(String(20))
    event_type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(10))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(50))
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    account: Mapped["Account"] = relationship(back_populates="categories")
    aliases: Mapped[list["CategoryAlias"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("account_id", "name", name="uq_category_account_name"),
    )


class CategoryAlias(Base):
    __tablename__ = "category_aliases"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    category_id: Mapped[str] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE")
    )
    alias: Mapped[str] = mapped_column(String(100))
    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    category: Mapped["Category"] = relationship(back_populates="aliases")

    __table_args__ = (
        UniqueConstraint("account_id", "alias", name="uq_alias_account_alias"),
    )


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    otp_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    otp_attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    signup_landing: Mapped[str | None] = mapped_column(String(64))
    signup_source: Mapped[str | None] = mapped_column(String(64))
    signup_medium: Mapped[str | None] = mapped_column(String(64))
    signup_campaign: Mapped[str | None] = mapped_column(String(128))
    signup_content: Mapped[str | None] = mapped_column(String(128))
