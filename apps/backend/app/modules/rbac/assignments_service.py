"""RBAC slice 2 service: role↔permission and user↔role assignments (api-contract.md §5.6–5.9).

Tenant scoping mirrors ``roles_service``: roles must be visible to the caller's
tenant, target users must hold an active membership in the caller's tenant, and
mismatches return 404. ``org_admin`` revocation is protected by the
``LAST_ADMIN_PROTECTED`` rule (api-contract.md §5.9).
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.modules.organizations.models import Membership
from app.modules.rbac.models import Permission, Role, RolePermission, UserRole
from app.modules.rbac.roles_service import (
    get_visible_role,
    record_audit,
    require_custom_role,
    role_view,
)
from app.modules.rbac.schemas import RoleView, UserRoleView

_LAST_ADMIN_ROLE = "org_admin"


async def _active_membership(
    session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> Membership:
    membership = (
        await session.execute(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.organization_id == tenant_id,
                Membership.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise APIError(404, "USER_NOT_FOUND")
    return membership


class AssignmentsService:
    async def assign_permission(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        role_id: uuid.UUID,
        permission_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> RoleView:
        role = await get_visible_role(session, tenant_id, role_id)
        require_custom_role(role, "SYSTEM_ROLE_IMMUTABLE")
        permission = await session.get(Permission, permission_id)
        if permission is None:
            raise APIError(404, "PERMISSION_NOT_FOUND")
        existing = await session.execute(
            select(RolePermission).where(
                RolePermission.role_id == role.id, RolePermission.permission_id == permission.id
            )
        )
        if existing.scalar_one_or_none() is None:
            session.add(RolePermission(role_id=role.id, permission_id=permission.id))
            record_audit(
                session, actor_id, tenant_id, "role.permission.assign", role.id, ip, user_agent
            )
            await session.commit()
        return await role_view(session, role)

    async def revoke_permission(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        role_id: uuid.UUID,
        permission_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        role = await get_visible_role(session, tenant_id, role_id)
        require_custom_role(role, "SYSTEM_ROLE_IMMUTABLE")
        result = await session.execute(
            delete(RolePermission).where(
                RolePermission.role_id == role.id, RolePermission.permission_id == permission_id
            )
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise APIError(404, "ROLE_PERMISSION_NOT_FOUND")
        record_audit(
            session, actor_id, tenant_id, "role.permission.revoke", role.id, ip, user_agent
        )
        await session.commit()

    async def assign_role_to_user(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> UserRoleView:
        membership = await _active_membership(session, tenant_id, user_id)
        role = await get_visible_role(session, tenant_id, role_id)
        existing = await session.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role.id,
                UserRole.organization_id == tenant_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise APIError(409, "ROLE_ASSIGNMENT_EXISTS")
        user_role = UserRole(
            user_id=user_id, role_id=role.id, organization_id=tenant_id, assigned_by=actor_id
        )
        session.add(user_role)
        membership.role = role.name  # denormalized display role (see users service)
        record_audit(session, actor_id, tenant_id, "user.role.assign", role.id, ip, user_agent)
        await session.commit()
        return UserRoleView(
            user_id=user_role.user_id,
            role_id=user_role.role_id,
            organization_id=user_role.organization_id,
            created_at=user_role.created_at,
        )

    async def revoke_role_from_user(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        await _active_membership(session, tenant_id, user_id)
        assignment = (
            await session.execute(
                select(UserRole).where(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role_id,
                    UserRole.organization_id == tenant_id,
                )
            )
        ).scalar_one_or_none()
        role = await session.get(Role, role_id)
        if assignment is None or (
            role is not None
            and role.organization_id is not None
            and role.organization_id != tenant_id
        ):
            raise APIError(404, "USER_ROLE_NOT_FOUND")
        if role is not None and role.name == _LAST_ADMIN_ROLE:
            remaining = (
                await session.execute(
                    select(func.count())
                    .select_from(UserRole)
                    .join(Role, UserRole.role_id == Role.id)
                    .where(
                        UserRole.organization_id == tenant_id,
                        Role.name == _LAST_ADMIN_ROLE,
                        UserRole.user_id != user_id,
                    )
                )
            ).scalar_one()
            if remaining == 0:
                raise APIError(403, "LAST_ADMIN_PROTECTED")
        record_audit(session, actor_id, tenant_id, "user.role.revoke", role_id, ip, user_agent)
        await session.delete(assignment)
        await session.commit()
