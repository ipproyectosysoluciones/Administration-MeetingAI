"""init_core: users, organizations, properties, memberships

Revision ID: 0001
Revises:
Create Date: 2025-01-15

Per data-model.md §2.1. ``organizations`` is the tenant root (``tenant_id`` FKs
reference ``organizations.id``); there is no separate ``tenants`` table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)
_TSTZ = postgresql.TIMESTAMP(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "users",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_super_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("mfa_secret", sa.String(255)),
        sa.Column("last_login_at", _TSTZ),
        sa.Column("deleted_at", _TSTZ),
        sa.Column("created_at", _TSTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TSTZ, nullable=False, server_default=_NOW),
    )
    op.create_index(
        "ux_users_email",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_users_is_active", "users", ["is_active"])
    op.create_index(
        "ix_users_deleted_at",
        "users",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NOT NULL"),
    )

    op.create_table(
        "organizations",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("deleted_at", _TSTZ),
        sa.Column("created_at", _TSTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TSTZ, nullable=False, server_default=_NOW),
    )
    op.create_index(
        "ux_organizations_slug",
        "organizations",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_organizations_deleted_at",
        "organizations",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NOT NULL"),
    )

    op.create_table(
        "properties",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "organization_id",
            _UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50)),
        sa.Column("description", sa.Text()),
        sa.Column("deleted_at", _TSTZ),
        sa.Column("created_at", _TSTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TSTZ, nullable=False, server_default=_NOW),
    )
    op.create_index("ix_properties_organization_id", "properties", ["organization_id"])
    op.create_index(
        "ux_properties_org_code",
        "properties",
        ["organization_id", "code"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND code IS NOT NULL"),
    )
    op.create_index(
        "ix_properties_deleted_at",
        "properties",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NOT NULL"),
    )

    op.create_table(
        "memberships",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "user_id",
            _UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            _UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            _UUID,
            sa.ForeignKey("properties.id", ondelete="SET NULL"),
        ),
        sa.Column("role", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", _TSTZ),
        sa.Column("created_at", _TSTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TSTZ, nullable=False, server_default=_NOW),
    )
    op.create_index(
        "ux_memberships_user_org",
        "memberships",
        ["user_id", "organization_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"])
    op.create_index("ix_memberships_property_id", "memberships", ["property_id"])
    op.create_index(
        "ix_memberships_deleted_at",
        "memberships",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table("memberships")
    op.drop_table("properties")
    op.drop_table("organizations")
    op.drop_table("users")
    # Extensions are intentionally left in place: they are shared cluster-level
    # objects and dropping them could affect unrelated databases.
