"""Add x402 settlement fields, agent_wallets and exchange_rates tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-13

Backward-compatible: adds nullable columns and new tables only.
Old code continues to work — new columns default to NULL.
"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Settlement fields on purchase_requests ---
    op.add_column(
        "purchase_requests",
        sa.Column("settlement_method", sa.String(20), nullable=True),
    )
    op.add_column(
        "purchase_requests",
        sa.Column("settlement_currency", sa.String(10), nullable=True),
    )
    op.add_column(
        "purchase_requests",
        sa.Column("settlement_network", sa.String(30), nullable=True),
    )
    op.add_column(
        "purchase_requests",
        sa.Column("tx_hash", sa.String(66), nullable=True),
    )
    op.add_column(
        "purchase_requests",
        sa.Column("amount_usd", sa.Numeric(18, 6), nullable=True),
    )

    # --- Agent wallets (composite PK: agent_id + chain) ---
    op.create_table(
        "agent_wallets",
        sa.Column(
            "agent_id", sa.String(36), sa.ForeignKey("agents.id"), nullable=False
        ),
        sa.Column("chain", sa.String(20), nullable=False),
        sa.Column("wallet_address", sa.String(64), nullable=False),
        sa.Column("wallet_provider", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("agent_id", "chain"),
    )

    # --- Exchange rates (audit trail) ---
    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("pair", sa.String(20), nullable=False),
        sa.Column("rate", sa.Numeric(18, 8), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rates_pair_time", "exchange_rates", ["pair", "fetched_at"])


def downgrade() -> None:
    op.drop_index("ix_rates_pair_time", table_name="exchange_rates")
    op.drop_table("exchange_rates")
    op.drop_table("agent_wallets")

    op.drop_column("purchase_requests", "amount_usd")
    op.drop_column("purchase_requests", "tx_hash")
    op.drop_column("purchase_requests", "settlement_network")
    op.drop_column("purchase_requests", "settlement_currency")
    op.drop_column("purchase_requests", "settlement_method")
