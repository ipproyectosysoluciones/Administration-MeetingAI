"""add_minute_versions_table

Revision ID: a438b01d9a07
Revises: 228004878c15
Create Date: 2026-10-07 21:16:17.086930

Add minute_versions table for draft version history.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a438b01d9a07"
down_revision: str | None = "228004878c15"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)
_TSTZ = postgresql.TIMESTAMP(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "minute_versions",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "minute_id",
            _UUID,
            sa.ForeignKey("minutes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_by",
            _UUID,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", _TSTZ, nullable=False, server_default=_NOW),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_minute_versions_minute_id", "minute_versions", ["minute_id"])
    op.create_index("ix_minute_versions_version", "minute_versions", ["minute_id", "version"])


def downgrade() -> None:
    op.drop_index("ix_minute_versions_version", table_name="minute_versions")
    op.drop_index("ix_minute_versions_minute_id", table_name="minute_versions")
    op.drop_table("minute_versions")
