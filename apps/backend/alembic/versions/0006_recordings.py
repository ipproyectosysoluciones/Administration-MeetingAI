"""migration 0006: recordings + jobs tables (meetings-recording-upload, TASK-250).

Revises: 0005
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_NOW = sa.text("now()")

_RECORDING_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("recording.upload", "recording", "upload", "Upload meeting recordings"),
    ("recording.read", "recording", "read", "Read/list recording metadata"),
    ("recording.delete", "recording", "delete", "Delete recordings (soft)"),
]

_RECORDING_ROLE_MATRIX: dict[str, frozenset[str]] = {
    "super_admin": frozenset(p[0] for p in _RECORDING_PERMISSIONS),
    "org_admin": frozenset(p[0] for p in _RECORDING_PERMISSIONS),
    "secretary": frozenset({"recording.upload", "recording.read"}),
    "president": frozenset({"recording.read"}),
    "board_member": frozenset({"recording.read"}),
}


def _seed_recording_permissions() -> None:
    values = ",\n  ".join(
        f"(gen_random_uuid(), '{n}', '{r}', '{a}', '{d}', TRUE)"
        for n, r, a, d in _RECORDING_PERMISSIONS
    )
    op.execute(
        "INSERT INTO permissions (id, name, resource, action, description, is_system)\n"
        f"VALUES {values}\n"
        "ON CONFLICT (name) DO NOTHING"
    )


def _seed_recording_role_permissions() -> None:
    for role_name, perms in _RECORDING_ROLE_MATRIX.items():
        if not perms:
            continue
        perm_list = ", ".join(f"'{p}'" for p in perms)
        op.execute(
            "INSERT INTO role_permissions (role_id, permission_id)\n"
            "SELECT r.id, p.id FROM roles r\n"
            "JOIN permissions p ON p.name IN (" + perm_list + ")\n"
            f"WHERE r.name = '{role_name}' AND r.organization_id IS NULL\n"
            "ON CONFLICT (role_id, permission_id) DO NOTHING"
        )


def upgrade() -> None:
    op.create_table(
        "recordings",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
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
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="stored",
        ),
        sa.Column(
            "uploaded_by",
            _UUID,
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True)),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW
        ),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW
        ),
        sa.CheckConstraint("size_bytes > 0", name="ck_recordings_size_positive"),
        sa.CheckConstraint(
            "status IN ('stored','queued','transcribing','transcribed','failed')",
            name="ck_recordings_status",
        ),
    )
    op.create_index("ix_recordings_tenant", "recordings", ["tenant_id"])
    op.create_index("ix_recordings_meeting", "recordings", ["meeting_id"])
    op.create_index(
        "ux_recordings_meeting_sha256_active",
        "recordings",
        ["meeting_id", "sha256"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "jobs",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "run_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
        sa.Column("locked_by", sa.String(120)),
        sa.Column("locked_at", postgresql.TIMESTAMP(timezone=True)),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True)),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW
        ),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW
        ),
        sa.CheckConstraint(
            "status IN ('pending','running','done','failed')",
            name="ck_jobs_status",
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_jobs_attempts"),
    )
    op.create_index(
        "ix_jobs_pending",
        "jobs",
        ["run_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    _seed_recording_permissions()
    _seed_recording_role_permissions()


def downgrade() -> None:
    op.execute(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE resource = 'recording')"
    )
    op.execute("DELETE FROM permissions WHERE resource = 'recording'")
    op.drop_table("jobs")
    op.drop_table("recordings")
