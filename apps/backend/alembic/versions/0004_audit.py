"""audit: audit_events (append-only)

Revision ID: 0004
Revises: 0003
Create Date: 2025-01-15

Per data-model.md §2.4. Append-only is enforced by a trigger (BEFORE UPDATE OR
DELETE) rather than ``REVOKE``, because no application database role exists yet;
the trigger is role-independent and testable. A future ``REVOKE UPDATE, DELETE``
for the app role can coexist with the trigger.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FORBID_TRIGGER = "trg_audit_events_append_only"
_FORBID_FN = "forbid_audit_mutation"


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "timestamp",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("ip", postgresql.INET()),
        sa.Column("user_agent", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index(
        "ix_audit_events_tenant_timestamp",
        "audit_events",
        ["tenant_id", "timestamp"],
    )
    op.create_index(
        "ix_audit_events_actor_timestamp",
        "audit_events",
        ["actor_user_id", "timestamp"],
    )
    op.create_index("ix_audit_events_resource", "audit_events", ["resource", "resource_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_timestamp", "audit_events", ["timestamp"])

    op.execute(
        f"CREATE FUNCTION {_FORBID_FN}() RETURNS trigger AS $$\n"
        "BEGIN\n"
        "  RAISE EXCEPTION 'audit_events is append-only (%)', TG_OP;\n"
        "END;\n"
        "$$ LANGUAGE plpgsql"
    )
    op.execute(
        f"CREATE TRIGGER {_FORBID_TRIGGER}\n"
        "BEFORE UPDATE OR DELETE ON audit_events\n"
        f"FOR EACH ROW EXECUTE FUNCTION {_FORBID_FN}()"
    )


def downgrade() -> None:
    op.execute(f"DROP TRIGGER IF EXISTS {_FORBID_TRIGGER} ON audit_events")
    op.execute(f"DROP FUNCTION IF EXISTS {_FORBID_FN}()")
    op.drop_table("audit_events")
