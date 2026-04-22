"""Add token_hash column to agents for secure token lookup.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-20

Backward-compatible: adds nullable column, populates from existing tokens.
Old code can still read/write the `token` column (kept as-is).
New code uses `token_hash` for lookups.
"""

import hashlib

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add nullable token_hash column
    op.add_column(
        "agents",
        sa.Column("token_hash", sa.String(64), nullable=True),
    )

    # 2. Populate token_hash from existing tokens
    conn = op.get_bind()
    agents = conn.execute(sa.text("SELECT id, token FROM agents")).fetchall()
    for agent_id, token in agents:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        conn.execute(
            sa.text("UPDATE agents SET token_hash = :hash WHERE id = :id"),
            {"hash": token_hash, "id": agent_id},
        )

    # 3. Add unique index on token_hash
    op.create_index("ix_agents_token_hash", "agents", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_agents_token_hash", table_name="agents")
    op.drop_column("agents", "token_hash")
