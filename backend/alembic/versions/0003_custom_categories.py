"""Add categories and category_aliases tables, category_status column.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-20

Backward-compatible: adds new tables and a nullable column only.
Old code continues to work — new tables are independent, column defaults to NULL.
Data seed: creates 'other' category for every existing account.
"""

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Categories table (per-account) ---
    op.create_table(
        "categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("account_id", "name", name="uq_category_account_name"),
    )
    op.create_index("ix_categories_account_id", "categories", ["account_id"])

    # --- Category aliases table (per-account, denormalized account_id) ---
    op.create_table(
        "category_aliases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.String(36),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(100), nullable=False),
        sa.Column(
            "is_auto_generated", sa.Boolean, nullable=False, server_default="false"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("account_id", "alias", name="uq_alias_account_alias"),
    )
    op.create_index(
        "ix_category_aliases_account_id", "category_aliases", ["account_id"]
    )

    # --- category_status on purchase_requests ---
    op.add_column(
        "purchase_requests",
        sa.Column("category_status", sa.String(20), nullable=True),
    )

    # --- Seed: create 'other' category for every existing account ---
    conn = op.get_bind()
    accounts = conn.execute(sa.text("SELECT id FROM accounts"))
    for row in accounts:
        cat_id = str(uuid.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO categories (id, account_id, name, display_name, is_active, created_at, updated_at) "
                "VALUES (:id, :account_id, 'other', 'Other', true, now(), now())"
            ),
            {"id": cat_id, "account_id": row[0]},
        )


def downgrade() -> None:
    op.drop_column("purchase_requests", "category_status")
    op.drop_index("ix_category_aliases_account_id", table_name="category_aliases")
    op.drop_table("category_aliases")
    op.drop_index("ix_categories_account_id", table_name="categories")
    op.drop_table("categories")
