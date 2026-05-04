"""Add signup attribution columns to accounts.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-30

Backward-compatible: adds nullable columns. Existing accounts have NULL.
Old code can ignore these fields entirely.
"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for col_name, col_size in (
        ("signup_landing", 64),
        ("signup_source", 64),
        ("signup_medium", 64),
        ("signup_campaign", 128),
        ("signup_content", 128),
    ):
        op.add_column(
            "accounts",
            sa.Column(col_name, sa.String(col_size), nullable=True),
        )
        op.add_column(
            "verification_tokens",
            sa.Column(col_name, sa.String(col_size), nullable=True),
        )


def downgrade() -> None:
    for col_name in (
        "signup_content",
        "signup_campaign",
        "signup_medium",
        "signup_source",
        "signup_landing",
    ):
        op.drop_column("verification_tokens", col_name)
        op.drop_column("accounts", col_name)
