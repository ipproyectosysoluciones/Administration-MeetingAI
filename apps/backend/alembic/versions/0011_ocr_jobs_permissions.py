"""migration 0011: ocr_jobs table + document.*/ocr.* permissions (OCR-200)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_NOW = sa.text("now()")

_OCR_PERMISSIONS = [
    ("document.read", "document", "read", "Read documents"),
    ("document.upload", "document", "upload", "Upload documents"),
    ("document.download", "document", "download", "Download document files"),
    ("document.update", "document", "update", "Update document metadata"),
    ("document.delete", "document", "delete", "Delete documents"),
    ("ocr.run", "ocr", "run", "Enqueue/re-run OCR jobs"),
    ("ocr.read", "ocr", "read", "Read OCR job results"),
    ("ocr.correct", "ocr", "correct", "Submit human OCR corrections"),
]

_ROLE_MATRIX = {
    "super_admin": [name for name, _, _, _ in _OCR_PERMISSIONS],
    "org_admin": [name for name, _, _, _ in _OCR_PERMISSIONS],
    "secretary": [
        "document.read",
        "document.upload",
        "document.download",
        "ocr.run",
        "ocr.read",
        "ocr.correct",
    ],
    "president": ["document.read", "document.download", "ocr.read"],
    "board_member": [],
    "resident": [],
}


def _seed_permissions() -> None:
    values = ", ".join(
        f"(gen_random_uuid(), '{n}', '{r}', '{a}', '{d}', TRUE)" for n, r, a, d in _OCR_PERMISSIONS
    )
    op.execute(
        "INSERT INTO permissions (id, name, resource, action, description, is_system) "
        f"VALUES {values} ON CONFLICT (name) DO NOTHING"
    )


def _seed_role_permissions() -> None:
    for role_name, perms in _ROLE_MATRIX.items():
        if not perms:
            continue
        names = ", ".join(f"'{p}'" for p in perms)
        op.execute(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM roles r "
            "JOIN permissions p ON p.name IN (" + names + ") "
            f"WHERE r.name = '{role_name}' AND r.organization_id IS NULL "
            "ON CONFLICT (role_id, permission_id) DO NOTHING"
        )


def upgrade() -> None:
    op.create_table(
        "ocr_jobs",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            _UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            _UUID,
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("job_id", _UUID, sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("conf_threshold", sa.Float(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("pages", sa.Integer(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_by", _UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True)),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True)),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=_NOW,
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('queued','processing','completed','failed')",
            name="status",
        ),
        sa.CheckConstraint("attempt >= 1", name="attempt_min"),
        sa.UniqueConstraint("document_id", "attempt", name="ux_ocr_jobs_document_attempt"),
    )
    op.create_index("ix_ocr_jobs_tenant_id", "ocr_jobs", ["tenant_id"])
    op.create_index("ix_ocr_jobs_document_id", "ocr_jobs", ["document_id"])
    op.create_index("ix_ocr_jobs_status", "ocr_jobs", ["status"])
    _seed_permissions()
    _seed_role_permissions()


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ocr_jobs_status")
    op.execute("DROP INDEX IF EXISTS ix_ocr_jobs_document_id")
    op.execute("DROP INDEX IF EXISTS ix_ocr_jobs_tenant_id")
    op.drop_table("ocr_jobs")
    op.execute("DELETE FROM permissions WHERE resource IN ('document', 'ocr')")
