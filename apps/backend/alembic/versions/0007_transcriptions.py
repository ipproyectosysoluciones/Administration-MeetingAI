"""migration 0007: transcriptions table + transcription.* permissions (TASK-300).

Revises: 0006
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_NOW = sa.text("now()")

_TRANSCRIPTION_PERMISSIONS = (
    ("transcription.read", "transcription", "read", "Read transcripts"),
    ("transcription.create", "transcription", "create", "Create transcripts (worker)"),
    ("transcription.retry", "transcription", "retry", "Retry transcription jobs"),
)

_TRANSCRIPTION_ROLE_MATRIX = {
    "super_admin": [p[0] for p in _TRANSCRIPTION_PERMISSIONS],
    "org_admin": [p[0] for p in _TRANSCRIPTION_PERMISSIONS],
    "secretary": ["transcription.read"],
    "president": ["transcription.read"],
    "board_member": [],
    "resident": [],
}


def _seed_transcription_permissions() -> None:
    values = ",\n  ".join(
        f"(gen_random_uuid(), '{n}', '{r}', '{a}', '{d}', TRUE)"
        for n, r, a, d in _TRANSCRIPTION_PERMISSIONS
    )
    op.execute(
        "INSERT INTO permissions (id, name, resource, action, description, is_system)\n"
        f"VALUES {values}\n"
        "ON CONFLICT (name) DO NOTHING"
    )


def _seed_transcription_role_permissions() -> None:
    for role_name, perms in _TRANSCRIPTION_ROLE_MATRIX.items():
        if not perms:
            continue
        names = ", ".join(f"'{p}'" for p in perms)
        op.execute(
            "INSERT INTO role_permissions (role_id, permission_id)\n"
            "SELECT r.id, p.id FROM roles r\n"
            "JOIN permissions p ON p.name IN (" + names + ")\n"
            f"WHERE r.name = '{role_name}' AND r.organization_id IS NULL\n"
            "ON CONFLICT (role_id, permission_id) DO NOTHING"
        )


def upgrade() -> None:
    op.create_table(
        "transcriptions",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "recording_id",
            _UUID,
            sa.ForeignKey("recordings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "meeting_id",
            _UUID,
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            _UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("language", sa.String(16)),  # e.g. 'es', 'en'
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "segments", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"
        ),
        sa.Column("avg_confidence", sa.Numeric(4, 3)),
        sa.Column("model_used", sa.String(64)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("error", sa.Text()),
        sa.Column("created_by_job_id", _UUID),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW
        ),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW
        ),
        sa.CheckConstraint(
            "status IN ('draft','final','failed')",
            name="ck_transcripts_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_transcripts_version_min"),
    )
    op.create_index("ix_transcripts_recording", "transcriptions", ["recording_id"])
    op.create_index("ix_transcripts_tenant", "transcriptions", ["tenant_id"])
    op.create_index("ix_transcripts_meeting", "transcriptions", ["meeting_id"])
    op.create_index(
        "ux_transcripts_active_draft",
        "transcriptions",
        ["recording_id"],
        unique=True,
        postgresql_where=sa.text("status = 'draft'"),
    )

    _seed_transcription_permissions()
    _seed_transcription_role_permissions()


def downgrade() -> None:
    op.execute(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE resource = 'transcription')"
    )
    op.execute("DELETE FROM permissions WHERE resource = 'transcription'")
    op.drop_table("transcriptions")
