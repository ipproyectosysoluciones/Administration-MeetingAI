"""RBAC slice 2 routes (api-contract.md §5.6–5.9): permission + user-role assignments."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthContext, get_db, require_permission
from app.core.exceptions import APIError
from app.modules.rbac.assignments_service import AssignmentsService
from app.modules.rbac.schemas import (
    RolePermissionAssignRequest,
    RoleView,
    UserRoleAssignRequest,
    UserRoleAssignResponse,
)

router = APIRouter(tags=["rbac"])

Db = Annotated[AsyncSession, Depends(get_db)]
RolePermAssign = Annotated[AuthContext, Depends(require_permission("role.permission.assign"))]
RolePermRevoke = Annotated[AuthContext, Depends(require_permission("role.permission.revoke"))]
UserRoleAssign = Annotated[AuthContext, Depends(require_permission("user.role.assign"))]
UserRoleRevoke = Annotated[AuthContext, Depends(require_permission("user.role.revoke"))]


def _service() -> AssignmentsService:
    return AssignmentsService()


def _tenant(context: AuthContext) -> uuid.UUID:
    if context.tenant_id is None:
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP")
    return context.tenant_id


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.post("/rbac/roles/{role_id}/permissions", response_model=RoleView)
async def assign_permission(
    role_id: uuid.UUID,
    payload: RolePermissionAssignRequest,
    request: Request,
    db: Db,
    context: RolePermAssign,
) -> RoleView:
    return await _service().assign_permission(
        db,
        _tenant(context),
        context.user_id,
        role_id,
        payload.permission_id,
        _ip(request),
        _user_agent(request),
    )


@router.delete("/rbac/roles/{role_id}/permissions/{permission_id}")
async def revoke_permission(
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    request: Request,
    db: Db,
    context: RolePermRevoke,
) -> dict[str, str]:
    await _service().revoke_permission(
        db,
        _tenant(context),
        context.user_id,
        role_id,
        permission_id,
        _ip(request),
        _user_agent(request),
    )
    return {"message": "Permission revoked from role"}


@router.post("/rbac/users/{user_id}/roles", response_model=UserRoleAssignResponse)
async def assign_role_to_user(
    user_id: uuid.UUID,
    payload: UserRoleAssignRequest,
    request: Request,
    db: Db,
    context: UserRoleAssign,
) -> UserRoleAssignResponse:
    user_role = await _service().assign_role_to_user(
        db,
        _tenant(context),
        context.user_id,
        user_id,
        payload.role_id,
        _ip(request),
        _user_agent(request),
    )
    return UserRoleAssignResponse(message="Role assigned", user_role=user_role)


@router.delete("/rbac/users/{user_id}/roles/{role_id}")
async def revoke_role_from_user(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    request: Request,
    db: Db,
    context: UserRoleRevoke,
) -> dict[str, str]:
    await _service().revoke_role_from_user(
        db, _tenant(context), context.user_id, user_id, role_id, _ip(request), _user_agent(request)
    )
    return {"message": "Role revoked from user"}
