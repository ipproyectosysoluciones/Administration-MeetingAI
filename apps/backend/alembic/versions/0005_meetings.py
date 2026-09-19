"""migration 0005: meetings + meeting_participants (meetings-crud, TASK-200/201).

Revises: 0004
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_NOW = sa.text("now()")

_MEETING_STATUSES = ("scheduled", "in_progress", "finished", "cancelled")
_PARTICIPANT_ROLES = ("organizer", "presenter", "attendee")

# meeting.* permissions to seed (TASK-201; idempotent).
_MEETING_PERMISSIONS = (
    ("meeting.create", "meeting", "create", "Create meetings"),
    ("meeting.read", "meeting", "read", "Read meetings"),
    ("meeting.update", "meeting", "update", "Update meetings"),
    ("meeting.cancel", "meeting", "cancel", "Cancel meetings"),
    (
        "meeting.participant_manage",
        "meeting",
        "participant_manage",
        "Manage meeting participants",
    ),
)

# role_name → meeting permission names (extends the existing base-role matrix).
_MEETING_ROLE_MATRIX = {
    "super_admin": [p[0] for p in _MEETING_PERMISSIONS],
    "org_admin": [p[0] for p in _MEETING_PERMISSIONS],
    "secretary": [p[0] for p in _MEETING_PERMISSIONS],
    "president": ["meeting.read"],
    "board_member": ["meeting.read"],
    "resident": [],
}


def _seed_meeting_permissions() -> None:
    values = ",\n  ".join(
        f"(gen_random_uuid(), '{n}', '{r}', '{a}', '{d}', TRUE)"
        for n, r, a, d in _MEETING_PERMISSIONS
    )
    op.execute(
        "INSERT INTO permissions (id, name, resource, action, description, is_system)\n"
        f"VALUES {values}\n"
        "ON CONFLICT (name) DO NOTHING"
    )


def _seed_meeting_role_permissions() -> None:
    for role_name, perms in _MEETING_ROLE_MATRIX.items():
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
        "meetings",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "organization_id",
            _UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("starts_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ends_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column(
            "modality",
            sa.String(20),
            nullable=False,
            server_default="in_person",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True)),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW
        ),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW
        ),
        sa.CheckConstraint(
            "status IN ('scheduled','in_progress','finished','cancelled')",
            name="ck_meetings_status",
        ),
        sa.CheckConstraint(
            "modality IN ('in_person','virtual','hybrid')",
            name="ck_meetings_modality",
        ),
        sa.CheckConstraint("ends_at > starts_at", name="ck_meetings_time_range"),
    )
    op.create_index("ix_meetings_organization_id", "meetings", ["organization_id"])
    op.create_index(
        "ix_meetings_organization_starts_at",
        "meetings",
        ["organization_id", "starts_at"],
    )
    op.create_index("ix_meetings_organization_status", "meetings", ["organization_id", "status"])

    op.create_table(
        "meeting_participants",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "meeting_id",
            _UUID,
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Exactly one channel: internal user OR external email.
        sa.Column("user_id", _UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("external_email", sa.String(255)),
        sa.Column("role", sa.String(20), nullable=False, server_default="attendee"),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW
        ),
        sa.CheckConstraint(
            "(user_id IS NOT NULL)::int + (external_email IS NOT NULL)::int = 1",
            name="ck_meeting_participants_channel",
        ),
        sa.CheckConstraint(
            "role IN ('organizer','presenter','attendee')",
            name="ck_meeting_participants_role",
        ),
        sa.UniqueConstraint(
            "meeting_id",
            "user_id",
            name="uq_meeting_participants_user",
            deferrable=False,
        ),
        sa.UniqueConstraint(
            "meeting_id",
            "external_email",
            name="uq_meeting_participants_email",
            deferrable=False,
        ),
    )
    op.create_index("ix_meeting_participants_meeting_id", "meeting_participants", ["meeting_id"])
    op.create_index("ix_meeting_participants_user_id", "meeting_participants", ["user_id"])

    _seed_meeting_permissions()
    _seed_meeting_role_permissions()


def downgrade() -> None:
    op.execute(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE resource = 'meeting')"
    )
    op.execute("DELETE FROM permissions WHERE resource = 'meeting'")
    op.drop_table("meeting_participants")
    op.drop_table("meetings")
