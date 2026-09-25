"""migration 0008: CHECK constraint — avg_confidence IS NULL OR 0<=x<=1 (issue #80 advisory)."""

from __future__ import annotations

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels = None
depends_on = None

_NAME = "ck_transcripts_avg_confidence_range"


def upgrade() -> None:
    op.execute(
        "ALTER TABLE transcriptions ADD CONSTRAINT "
        f"{_NAME} CHECK (avg_confidence IS NULL OR (avg_confidence >= 0 AND avg_confidence <= 1))"
    )


def downgrade() -> None:
    op.execute(f"ALTER TABLE transcriptions DROP CONSTRAINT IF EXISTS {_NAME}")
