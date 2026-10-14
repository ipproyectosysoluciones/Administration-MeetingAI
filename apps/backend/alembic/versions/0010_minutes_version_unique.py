"""unique index minutes (meeting_id, version) — issue #115."""

from __future__ import annotations

from alembic import op

revision: str = "0010"
down_revision: str | None = "a438b01d9a07"


def upgrade() -> None:
    op.create_unique_constraint("uq_minutes_meeting_version", "minutes", ["meeting_id", "version"])


def downgrade() -> None:
    op.drop_constraint("uq_minutes_meeting_version", "minutes", type_="unique")
