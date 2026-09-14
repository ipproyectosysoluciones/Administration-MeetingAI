"""RBAC slice 1 service: permission registry + role CRUD (api-contract.md §5.1–5.5).

Every lookup is tenant-scoped: the tenant id always comes from the resolved
``AuthContext`` (never from the request), custom roles are only visible to their
owning organization, and cross-tenant access returns 404 (not 403) so role
existence is never leaked (reunionai-multitenant-security).

Naming reconciliation: the registry keeps the api-contract/data-model canonical
``auth.mfa.manage``; the draft ``user.mfa.manage`` found in proposal/specs was
never seeded and simply does not resolve (unknown permissions deny).
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.modules.audit.models import AuditEvent
from app.modules.rbac.models import Permission, Role, RolePermission, UserRole
from app.modules.rbac.schemas import (
    PermissionView,
    RoleCreateRequest,
    RoleUpdateRequest,
    RoleView,
)

_BASE_ROLE_NAMES = frozenset(
    {
        "super_admin",
        "org_admin",
        "property_admin",
        "president",
        "secretary",
        "board_member",
        "reviewer",
        "co_owner",
        "resident",
        "guest",
    }
)


def _permission_view(p: Permission) -> PermissionView:
    return PermissionView(
        id=p.id,
        name=p.name,
        resource=p.resource,
        action=p.action,
        description=p.description,
        is_system=p.is_system,
    )


async def role_view(session: AsyncSession, role: Role) -> RoleView:
    permissions = (
        (
            await session.execute(
                select(Permission)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id == role.id)
                .order_by(Permission.name)
            )
        )
        .scalars()
        .all()
    )
    return RoleView(
        id=role.id,
        organization_id=role.organization_id,
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        is_system=role.is_system,
        permissions=[_permission_view(p) for p in permissions],
    )


async def get_visible_role(session: AsyncSession, tenant_id: uuid.UUID, role_id: uuid.UUID) -> Role:
    """Fetch a role visible to ``tenant_id``: base (platform) roles or own custom roles."""
    role = await session.get(Role, role_id)
    if role is None or (role.organization_id is not None and role.organization_id != tenant_id):
        raise APIError(404, "ROLE_NOT_FOUND")
    return role


def require_custom_role(role: Role, code: str) -> None:
    """Reject mutations on base/system roles (spec.rbac §base roles: immutable)."""
    if role.organization_id is None or role.is_system:
        raise APIError(403, code)


async def require_permissions(
    session: AsyncSession, permission_ids: list[uuid.UUID]
) -> list[Permission]:
    rows = (
        (await session.execute(select(Permission).where(Permission.id.in_(permission_ids))))
        .scalars()
        .all()
    )
    found = {p.id for p in rows}
    missing = [pid for pid in permission_ids if pid not in found]
    if missing:
        raise APIError(404, "PERMISSION_NOT_FOUND", f"Unknown permission: {missing[0]}")
    return list(rows)


def record_audit(
    session: AsyncSession,
    actor_id: uuid.UUID,
    tenant_id: uuid.UUID | None,
    action: str,
    resource_id: uuid.UUID | None,
    ip: str | None,
    user_agent: str | None,
) -> None:
    if tenant_id is None:
        return  # platform-scope mutations have no tenant audit row yet
    session.add(
        AuditEvent(
            actor_user_id=actor_id,
            tenant_id=tenant_id,
            action=action,
            resource="role",
            resource_id=resource_id,
            ip=ip,
            user_agent=user_agent,
            metadata_json={},
        )
    )


class RolesService:
    async def list_permissions(self, session: AsyncSession) -> tuple[list[PermissionView], int]:
        rows = (await session.execute(select(Permission).order_by(Permission.name))).scalars().all()
        return [_permission_view(p) for p in rows], len(rows)

    async def list_roles(self, session: AsyncSession, tenant_id: uuid.UUID) -> list[RoleView]:
        roles = (
            (
                await session.execute(
                    select(Role)
                    .where((Role.organization_id.is_(None)) | (Role.organization_id == tenant_id))
                    .order_by(Role.name)
                )
            )
            .scalars()
            .all()
        )
        return [await role_view(session, role) for role in roles]

    async def create_role(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: RoleCreateRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> RoleView:
        if payload.name in _BASE_ROLE_NAMES:
            raise APIError(403, "SYSTEM_ROLE_NAME_RESERVED")
        exists = (
            await session.execute(
                select(func.count())
                .select_from(Role)
                .where(Role.organization_id == tenant_id, Role.name == payload.name)
            )
        ).scalar_one()
        if exists:
            raise APIError(409, "ROLE_NAME_EXISTS")
        permissions = await require_permissions(session, payload.permission_ids)
        role = Role(
            organization_id=tenant_id,
            name=payload.name,
            display_name=payload.display_name,
            description=payload.description,
            is_system=False,
            is_deletable=True,
        )
        session.add(role)
        await session.flush()
        for permission in permissions:
            session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        record_audit(session, actor_id, tenant_id, "role.create", role.id, ip, user_agent)
        await session.commit()
        return await role_view(session, role)

    async def update_role(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        role_id: uuid.UUID,
        payload: RoleUpdateRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> RoleView:
        role = await get_visible_role(session, tenant_id, role_id)
        require_custom_role(role, "SYSTEM_ROLE_IMMUTABLE")
        if payload.display_name is not None:
            role.display_name = payload.display_name
        if payload.description is not None:
            role.description = payload.description
        if payload.permission_ids is not None:
            permissions = await require_permissions(session, payload.permission_ids)
            await session.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
            for permission in permissions:
                session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        record_audit(session, actor_id, tenant_id, "role.update", role.id, ip, user_agent)
        await session.commit()
        return await role_view(session, role)

    async def delete_role(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        role_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        role = await get_visible_role(session, tenant_id, role_id)
        require_custom_role(role, "ROLE_CANNOT_DELETE")
        assigned = (
            await session.execute(
                select(func.count()).select_from(UserRole).where(UserRole.role_id == role.id)
            )
        ).scalar_one()
        if assigned:
            raise APIError(403, "ROLE_CANNOT_DELETE", "Role has assigned users")
        record_audit(session, actor_id, tenant_id, "role.delete", role.id, ip, user_agent)
        await session.delete(role)
        await session.commit()
