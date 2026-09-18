"""auth: refresh_tokens, mfa_devices, sessions

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-15

Per data-model.md §2.2. Refresh tokens are rotating, hashed, and chain-tracked
via the self-referential ``replaced_by_token_id`` column.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)
_TSTZ = postgresql.TIMESTAMP(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "user_id",
            _UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", _TSTZ, nullable=False),
        sa.Column("revoked_at", _TSTZ),
        sa.Column(
            "replaced_by_token_id",
            _UUID,
            sa.ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        ),
        sa.Column("user_agent", sa.Text()),
        sa.Column("ip", postgresql.INET()),
        sa.Column("created_at", _TSTZ, nullable=False, server_default=_NOW),
    )
    op.create_index("ux_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])
    op.create_index(
        "ix_refresh_tokens_revoked_at",
        "refresh_tokens",
        ["revoked_at"],
        postgresql_where=sa.text("revoked_at IS NOT NULL"),
    )
    op.create_index("ix_refresh_tokens_replaced_by", "refresh_tokens", ["replaced_by_token_id"])

    op.create_table(
        "mfa_devices",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "user_id",
            _UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("secret_encrypted", sa.String(255), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_used_at", _TSTZ),
        sa.Column("created_at", _TSTZ, nullable=False, server_default=_NOW),
    )
    op.create_index("ux_mfa_devices_user_name", "mfa_devices", ["user_id", "name"], unique=True)
    op.create_index("ix_mfa_devices_user_id", "mfa_devices", ["user_id"])

    op.create_table(
        "sessions",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "user_id",
            _UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "refresh_token_id",
            _UUID,
            sa.ForeignKey("refresh_tokens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_agent", sa.Text()),
        sa.Column("ip", postgresql.INET()),
        sa.Column("last_activity_at", _TSTZ, nullable=False, server_default=_NOW),
        sa.Column("created_at", _TSTZ, nullable=False, server_default=_NOW),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_refresh_token_id", "sessions", ["refresh_token_id"])
    op.create_index("ix_sessions_last_activity", "sessions", ["last_activity_at"])


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("mfa_devices")
    op.drop_table("refresh_tokens")
