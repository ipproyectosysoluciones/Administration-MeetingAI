"""add_documents_table

Revision ID: 228004878c15
Revises: d029a062d4d5
Create Date: 2026-10-07 20:00:10.577682

Documents table with versioning, OCR support, and tenant isolation.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "228004878c15"
down_revision: str | None = "d029a062d4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)
_TSTZ = postgresql.TIMESTAMP(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    # Create enum types
    op.execute(
        "CREATE TYPE document_status AS ENUM ('pending', 'processing', 'completed', 'failed')"
    )
    op.execute("CREATE TYPE document_type AS ENUM ('pdf', 'jpg', 'jpeg', 'png', 'tiff')")

    op.create_table(
        "documents",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            _UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "meeting_id",
            _UUID,
            sa.ForeignKey("meetings.id", ondelete="SET NULL"),
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "type",
            postgresql.ENUM(
                "pdf",
                "jpg",
                "jpeg",
                "png",
                "tiff",
                name="document_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "processing",
                "completed",
                "failed",
                name="document_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ocr_text", sa.Text()),
        sa.Column("ocr_confidence", sa.Float()),
        sa.Column("ocr_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("ocr_error", sa.Text()),
        sa.Column("pages", sa.Integer()),
        sa.Column(
            "uploaded_by",
            _UUID,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column("deleted_at", _TSTZ),
        sa.Column("created_at", _TSTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TSTZ, nullable=False, server_default=_NOW),
        sa.CheckConstraint("version >= 1", name="ck_documents_version_min"),
        sa.CheckConstraint("file_size > 0", name="ck_documents_file_size_positive"),
    )
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])
    op.create_index("ix_documents_meeting_id", "documents", ["meeting_id"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_sha256", "documents", ["sha256"])
    op.create_index("ix_documents_uploaded_by", "documents", ["uploaded_by"])

    # Document versions table
    op.create_table(
        "document_versions",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "document_id",
            _UUID,
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("ocr_text", sa.Text()),
        sa.Column("ocr_confidence", sa.Float()),
        sa.Column("ocr_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("pages", sa.Integer()),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_by",
            _UUID,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", _TSTZ, nullable=False, server_default=_NOW),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_index("ix_document_versions_version", "document_versions", ["document_id", "version"])


def downgrade() -> None:
    op.drop_index("ix_document_versions_version", table_name="document_versions")
    op.drop_index("ix_document_versions_document_id", table_name="document_versions")
    op.drop_table("document_versions")

    op.drop_index("ix_documents_uploaded_by", table_name="documents")
    op.drop_index("ix_documents_sha256", table_name="documents")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_meeting_id", table_name="documents")
    op.drop_index("ix_documents_tenant_id", table_name="documents")
    op.drop_table("documents")

    op.execute("DROP TYPE IF EXISTS document_status")
    op.execute("DROP TYPE IF EXISTS document_type")
