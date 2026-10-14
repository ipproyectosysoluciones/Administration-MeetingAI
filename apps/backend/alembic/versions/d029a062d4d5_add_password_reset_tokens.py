"""add_password_reset_tokens

Revision ID: d029a062d4d5
Revises: 0009
Create Date: 2026-10-07 19:40:45.666234

Add password_reset_tokens table for secure password reset flow.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d029a062d4d5"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)
_TSTZ = postgresql.TIMESTAMP(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "user_id",
            _UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", _TSTZ, nullable=False),
        sa.Column("used_at", _TSTZ),
        sa.Column("ip", postgresql.INET()),
        sa.Column("user_agent", sa.Text()),
        sa.Column("created_at", _TSTZ, nullable=False, server_default=_NOW),
    )
    op.create_index(
        "ux_password_reset_tokens_token_hash",
        "password_reset_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])
    op.create_index(
        "ix_password_reset_tokens_used_at",
        "password_reset_tokens",
        ["used_at"],
        postgresql_where=sa.text("used_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
