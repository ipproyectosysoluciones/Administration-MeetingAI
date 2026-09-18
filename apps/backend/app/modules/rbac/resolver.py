"""DB-backed authorization resolution (architecture §3 / §5).

This is the real implementation of ``core.dependencies.AuthorizationResolver``: it
resolves a user's active membership (tenant) and the union of their role permissions
from the database, reusing the pure ``resolve_active_membership`` /
``resolve_permissions`` functions. The tenant is always derived from the user's
membership — never from request input (reunionai-multitenant-security).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.dependencies import (
    AuthContext,
    AuthorizationResolver,
    Membership,
    Role,
    resolve_active_membership,
    resolve_permissions,
)
from app.core.exceptions import TenantResolutionError
from app.modules.organizations.models import Membership as MembershipModel
from app.modules.organizations.models import Organization
from app.modules.rbac.models import Permission, RolePermission, UserRole
from app.modules.rbac.models import Role as RoleModel
from app.modules.users.models import User


async def _load_memberships(session: AsyncSession, user_id: uuid.UUID) -> list[Membership]:
    stmt = (
        select(MembershipModel, Organization.deleted_at)
        .join(Organization, MembershipModel.organization_id == Organization.id)
        .where(MembershipModel.user_id == user_id)
    )
    rows = (await session.execute(stmt)).all()
    return [
        Membership(
            organization_id=m.organization_id,
            role=m.role,
            property_id=m.property_id,
            created_at=m.created_at,
            deleted_at=m.deleted_at,
            organization_deleted_at=org_deleted_at,
        )
        for m, org_deleted_at in rows
    ]


async def _load_roles(
    session: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID
) -> list[Role]:
    stmt = (
        select(RoleModel.name, Permission.name)
        .join(UserRole, UserRole.role_id == RoleModel.id)
        .join(RolePermission, RolePermission.role_id == RoleModel.id)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .where(UserRole.user_id == user_id, UserRole.organization_id == tenant_id)
    )
    rows = (await session.execute(stmt)).all()
    perms_by_role: dict[str, set[str]] = {}
    for role_name, perm_name in rows:
        perms_by_role.setdefault(role_name, set()).add(perm_name)
    return [Role(name=name, permissions=frozenset(perms)) for name, perms in perms_by_role.items()]


async def resolve_auth_context(session: AsyncSession, user_id: uuid.UUID) -> AuthContext:
    """Resolve the AuthContext (tenant + permissions) for ``user_id``.

    Raises ``TenantResolutionError`` when the user is inactive/soft-deleted or has no
    active membership. A platform super-admin resolves to ``tenant_id=None`` with a
    wildcard context (``is_super_admin=True``).
    """
    user = await session.get(User, user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise TenantResolutionError()
    if user.is_super_admin:
        return AuthContext(
            user_id=user_id,
            tenant_id=None,
            permissions=frozenset(),
            is_super_admin=True,
        )
    memberships = await _load_memberships(session, user_id)
    active = resolve_active_membership(memberships)
    if active is None:
        raise TenantResolutionError()
    roles = await _load_roles(session, user_id, active.organization_id)
    return AuthContext(
        user_id=user_id,
        tenant_id=active.organization_id,
        permissions=resolve_permissions(roles),
    )


class DBAuthorizationResolver(AuthorizationResolver):
    """``AuthorizationResolver`` implementation backed by the application database."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def resolve_context(self, user_id: uuid.UUID) -> AuthContext:
        async with self._session_factory() as session:
            return await resolve_auth_context(session, user_id)
