"""Initial core schema.

Revision ID: 0001
Revises: -
Create Date: 2026-04-02
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column(
            "timezone", sa.String(50), nullable=False, server_default="America/New_York"
        ),
        sa.Column("plan", sa.String(10), nullable=False, server_default="free"),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("blocked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "all_agents_paused", sa.Boolean, nullable=False, server_default="false"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "account_spent", sa.Numeric(12, 2), nullable=False, server_default="0.00"
        ),
        sa.Column(
            "account_held", sa.Numeric(12, 2), nullable=False, server_default="0.00"
        ),
        sa.Column(
            "request_expiry_minutes", sa.Integer, nullable=False, server_default="30"
        ),
    )

    op.create_table(
        "agents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("accounts.id"),
            index=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(10), nullable=False, server_default="active"),
        sa.Column("budget", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("spent", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("held", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("policy", JSONB, nullable=True),
        sa.Column("policy_text", sa.Text, nullable=True),
        sa.Column("token", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column("is_sandbox", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "auto_replenish_enabled", sa.Boolean, nullable=False, server_default="false"
        ),
        sa.Column("auto_replenish_threshold", sa.Numeric(12, 2), nullable=True),
        sa.Column("auto_replenish_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("auto_replenish_max_budget", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "purchase_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "agent_id", sa.String(36), sa.ForeignKey("agents.id"), nullable=False
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("original_category", sa.String(100), nullable=True),
        sa.Column("merchant", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("agent_comment", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("policy_check", JSONB, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("receipt_url", sa.Text, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_requests_agent_status", "purchase_requests", ["agent_id", "status"]
    )
    op.create_index(
        "ix_requests_agent_created", "purchase_requests", ["agent_id", "created_at"]
    )

    op.create_table(
        "policy_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "agent_id", sa.String(36), sa.ForeignKey("agents.id"), nullable=False
        ),
        sa.Column("user_input", sa.Text, nullable=False),
        sa.Column("ai_output", JSONB, nullable=False),
        sa.Column("accepted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "account_id", sa.String(36), sa.ForeignKey("accounts.id"), nullable=False
        ),
        sa.Column("endpoint", sa.Text, unique=True, nullable=False),
        sa.Column("p256dh", sa.Text, nullable=False),
        sa.Column("auth", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "budget_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("accounts.id"),
            index=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("limit_type", sa.String(20), nullable=False),
        sa.Column("limit_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("days_of_week", JSONB, nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "notification_channels",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("accounts.id"),
            index=True,
            nullable=False,
        ),
        sa.Column("channel_type", sa.String(20), nullable=False),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("account_id", "channel_type", name="uq_notif_account_type"),
    )

    op.create_table(
        "notification_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("accounts.id"),
            index=True,
            nullable=False,
        ),
        sa.Column("request_id", sa.String(36), nullable=True),
        sa.Column("channel_type", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "verification_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), index=True, nullable=False),
        sa.Column("token", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("otp_code", sa.String(6), nullable=True),
        sa.Column("otp_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("verification_tokens")
    op.drop_table("notification_log")
    op.drop_table("notification_channels")
    op.drop_table("budget_rules")
    op.drop_table("push_subscriptions")
    op.drop_table("policy_logs")
    op.drop_table("purchase_requests")
    op.drop_table("agents")
    op.drop_table("accounts")
