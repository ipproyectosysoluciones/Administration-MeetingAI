"""migration 0009: minutes table + minutes.* permissions (MIN-100)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_NOW = sa.text("now()")

_MINUTES_PERMISSIONS = [
    ("minutes.read", "minutes", "read", "Read minutes"),
    ("minutes.write", "minutes", "write", "Create/review minutes"),
    ("minutes.approve", "minutes", "approve", "Approve minutes"),
    ("minutes.publish", "minutes", "publish", "Publish minutes"),
]

_ROLE_MATRIX = {
    "super_admin": ["minutes.read", "minutes.write", "minutes.approve", "minutes.publish"],
    "org_admin": ["minutes.read", "minutes.write", "minutes.approve", "minutes.publish"],
    "secretary": ["minutes.read", "minutes.write"],
    "president": ["minutes.read"],
    "board_member": [],
    "resident": [],
}


def _seed_permissions() -> None:
    values = ", ".join(
        f"(gen_random_uuid(), '{n}', '{r}', '{a}', '{d}', TRUE)"
        for n, r, a, d in _MINUTES_PERMISSIONS
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
        "minutes",
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
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("created_by", _UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_by", _UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", postgresql.TIMESTAMP(timezone=True)),
        sa.Column("approved_by", _UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", postgresql.TIMESTAMP(timezone=True)),
        sa.Column("approved_ip", sa.Text(), nullable=True),
        sa.Column("approved_user_agent", sa.Text(), nullable=True),
        sa.Column("published_by", _UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("published_at", postgresql.TIMESTAMP(timezone=True)),
        sa.Column("archived_at", postgresql.TIMESTAMP(timezone=True)),
        sa.Column("ai_provider", sa.Text(), nullable=True),
        sa.Column("ai_model", sa.Text(), nullable=True),
        sa.Column("ai_request_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=_NOW,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=_NOW,
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('draft','review','approved','published','archived')",
            name="ck_minutes_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_minutes_version_min"),
    )
    op.create_index("ix_minutes_tenant_id", "minutes", ["tenant_id"])
    op.create_index("ix_minutes_meeting_id", "minutes", ["meeting_id"])
    op.create_index("ix_minutes_status", "minutes", ["status"])
    _seed_permissions()
    _seed_role_permissions()


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_minutes_status")
    op.execute("DROP INDEX IF EXISTS ix_minutes_meeting_id")
    op.execute("DROP INDEX IF EXISTS ix_minutes_tenant_id")
    op.drop_table("minutes")
    op.execute("DELETE FROM permissions WHERE resource = 'minutes'")
