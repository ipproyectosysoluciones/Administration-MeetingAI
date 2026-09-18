"""rbac: permissions, roles, role_permissions, user_roles (with seed data)

Revision ID: 0003
Revises: 0002
Create Date: 2025-01-15

Per data-model.md §2.3 / §4. Seeding is idempotent (``ON CONFLICT ... DO NOTHING``).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)
_NOW = sa.text("now()")

# (name, resource, action, description)
_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("auth.login", "auth", "login", "Log in to the system"),
    ("auth.register", "auth", "register", "Register a new organization"),
    ("auth.refresh", "auth", "refresh", "Refresh access token"),
    ("auth.revoke", "auth", "revoke", "Revoke own session"),
    ("auth.mfa.manage", "auth", "mfa.manage", "Manage own MFA devices"),
    ("user.read", "user", "read", "Read users in tenant"),
    ("user.create", "user", "create", "Create users in tenant"),
    ("user.update", "user", "update", "Update users in tenant"),
    ("user.delete", "user", "delete", "Soft-delete users in tenant"),
    ("user.password.change", "user", "password.change", "Change own password"),
    ("user.session.read", "user", "session.read", "List own sessions"),
    ("user.session.revoke", "user", "session.revoke", "Revoke own sessions"),
    ("user.role.assign", "user", "role.assign", "Assign roles to users"),
    ("user.role.revoke", "user", "role.revoke", "Revoke roles from users"),
    ("organization.read", "organization", "read", "Read organization settings"),
    ("organization.create", "organization", "create", "Create organizations (super-admin)"),
    ("organization.update", "organization", "update", "Update organization settings"),
    ("organization.delete", "organization", "delete", "Soft-delete organization"),
    ("property.read", "property", "read", "Read properties in tenant"),
    ("property.create", "property", "create", "Create properties in tenant"),
    ("property.update", "property", "update", "Update properties in tenant"),
    ("property.delete", "property", "delete", "Delete properties in tenant"),
    ("membership.read", "membership", "read", "List memberships in tenant"),
    ("membership.create", "membership", "create", "Add members to tenant"),
    ("membership.update", "membership", "update", "Update membership roles/properties"),
    ("membership.delete", "membership", "delete", "Remove members from tenant"),
    ("permission.read", "permission", "read", "List permissions"),
    ("role.read", "role", "read", "List roles in tenant"),
    ("role.create", "role", "create", "Create custom roles in tenant"),
    ("role.update", "role", "update", "Update custom roles in tenant"),
    ("role.delete", "role", "delete", "Delete custom roles in tenant"),
    ("role.permission.assign", "role", "permission.assign", "Assign permissions to roles"),
    ("role.permission.revoke", "role", "permission.revoke", "Revoke permissions from roles"),
    ("audit.read", "audit", "read", "Read audit log"),
]

# (name, display_name, description)
_BASE_ROLES: list[tuple[str, str, str]] = [
    ("super_admin", "Super Admin", "Platform administrator with full access"),
    ("org_admin", "Organization Admin", "Organization administrator"),
    ("property_admin", "Property Admin", "Property/group administrator"),
    ("president", "President", "Organization president"),
    ("secretary", "Secretary", "Organization secretary"),
    ("board_member", "Board Member", "Board member"),
    ("reviewer", "Reviewer", "Document/minutes reviewer"),
    ("co_owner", "Co-owner", "Co-owner/propietario"),
    ("resident", "Resident", "Resident/occupant"),
    ("guest", "Guest", "Guest with limited access"),
]

# Permission name sets per base role; None = wildcard (all permissions).
_ROLE_PERMISSIONS: dict[str, frozenset[str] | None] = {
    "super_admin": None,
    "org_admin": frozenset(
        {
            "organization.read",
            "organization.update",
            "user.read",
            "user.create",
            "user.update",
            "user.delete",
            "user.password.change",
            "user.session.read",
            "user.session.revoke",
            "user.role.assign",
            "user.role.revoke",
            "property.read",
            "property.create",
            "property.update",
            "property.delete",
            "membership.read",
            "membership.create",
            "membership.update",
            "membership.delete",
            "role.read",
            "role.create",
            "role.update",
            "role.delete",
            "role.permission.assign",
            "role.permission.revoke",
            "permission.read",
            "audit.read",
        }
    ),
    "property_admin": frozenset(
        {
            "property.read",
            "property.update",
            "membership.read",
            "membership.update",
            "user.read",
            "user.update",
            "audit.read",
        }
    ),
    "president": frozenset({"organization.read", "user.read", "membership.read", "audit.read"}),
    "secretary": frozenset({"organization.read", "user.read", "membership.read", "audit.read"}),
    "board_member": frozenset({"organization.read", "user.read", "membership.read"}),
    "reviewer": frozenset({"organization.read", "user.read", "membership.read"}),
    "co_owner": frozenset({"organization.read", "user.read", "membership.read"}),
    "resident": frozenset({"organization.read", "user.read"}),
    "guest": frozenset({"organization.read"}),
}


def _seed_permissions() -> None:
    values = ",\n  ".join(f"('{n}', '{r}', '{a}', '{d}', TRUE)" for n, r, a, d in _PERMISSIONS)
    op.execute(
        "INSERT INTO permissions (name, resource, action, description, is_system)\n"
        f"VALUES {values}\n"
        "ON CONFLICT (name) DO NOTHING"
    )


def _seed_roles() -> None:
    values = ",\n  ".join(
        f"(gen_random_uuid(), NULL, '{n}', '{d}', '{desc}', TRUE, FALSE)"
        for n, d, desc in _BASE_ROLES
    )
    op.execute(
        "INSERT INTO roles (id, organization_id, name, display_name, description, is_system,"
        " is_deletable)\n"
        f"VALUES {values}\n"
        "ON CONFLICT (organization_id, name) DO NOTHING"
    )


def _seed_role_permissions() -> None:
    for role_name, perms in _ROLE_PERMISSIONS.items():
        where = (
            "TRUE"
            if perms is None
            else "p.name IN (" + ", ".join(f"'{p}'" for p in sorted(perms)) + ")"
        )
        op.execute(
            "INSERT INTO role_permissions (role_id, permission_id)\n"
            "SELECT r.id, p.id FROM roles r CROSS JOIN permissions p\n"
            f"WHERE r.name = '{role_name}' AND r.organization_id IS NULL AND {where}\n"
            "ON CONFLICT DO NOTHING"
        )


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("resource", sa.String(50), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW
        ),
    )
    op.create_index("ux_permissions_name", "permissions", ["name"], unique=True)
    op.create_index("ix_permissions_resource", "permissions", ["resource"])

    op.create_table(
        "roles",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "organization_id",
            _UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_deletable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW
        ),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW
        ),
    )
    op.create_index(
        "ux_roles_org_name",
        "roles",
        ["organization_id", "name"],
        unique=True,
        # Base roles have organization_id = NULL; without NULLS NOT DISTINCT the
        # ON CONFLICT clause in _seed_roles() never matches and re-runs duplicate
        # the base roles (R3-rbac-seed-not-idempotent).
        postgresql_nulls_not_distinct=True,
    )
    op.create_index("ix_roles_organization_id", "roles", ["organization_id"])
    op.create_index("ix_roles_is_system", "roles", ["is_system"])

    op.create_table(
        "role_permissions",
        sa.Column(
            "role_id",
            _UUID,
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "permission_id",
            _UUID,
            sa.ForeignKey("permissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            _UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            _UUID,
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            _UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("assigned_by", _UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id", "organization_id"),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])
    op.create_index("ix_user_roles_organization_id", "user_roles", ["organization_id"])

    _seed_permissions()
    _seed_roles()
    _seed_role_permissions()


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("permissions")
