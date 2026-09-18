"""RBAC slice 1 routes (api-contract.md §5.1–5.5): registry + custom role CRUD."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthContext, get_db, require_permission
from app.core.exceptions import APIError
from app.modules.rbac.roles_service import RolesService
from app.modules.rbac.schemas import (
    PermissionListResponse,
    RoleCreateRequest,
    RoleListResponse,
    RoleUpdateRequest,
    RoleView,
)

router = APIRouter(tags=["rbac"])

Db = Annotated[AsyncSession, Depends(get_db)]
PermissionRead = Annotated[AuthContext, Depends(require_permission("permission.read"))]
RoleRead = Annotated[AuthContext, Depends(require_permission("role.read"))]
RoleCreate = Annotated[AuthContext, Depends(require_permission("role.create"))]
RoleUpdate = Annotated[AuthContext, Depends(require_permission("role.update"))]
RoleDelete = Annotated[AuthContext, Depends(require_permission("role.delete"))]


def _service() -> RolesService:
    return RolesService()


def _tenant(context: AuthContext) -> uuid.UUID:
    if context.tenant_id is None:
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP")
    return context.tenant_id


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.get("/rbac/permissions", response_model=PermissionListResponse)
async def list_permissions(db: Db, context: PermissionRead) -> PermissionListResponse:
    _tenant(context)
    items, total = await _service().list_permissions(db)
    return PermissionListResponse(items=items, total=total)


@router.get("/rbac/roles", response_model=RoleListResponse)
async def list_roles(db: Db, context: RoleRead) -> RoleListResponse:
    items = await _service().list_roles(db, _tenant(context))
    return RoleListResponse(items=items, total=len(items))


@router.post("/rbac/roles", response_model=RoleView, status_code=201)
async def create_role(
    payload: RoleCreateRequest, request: Request, db: Db, context: RoleCreate
) -> RoleView:
    return await _service().create_role(
        db, _tenant(context), context.user_id, payload, _ip(request), _user_agent(request)
    )


@router.patch("/rbac/roles/{role_id}", response_model=RoleView)
async def update_role(
    role_id: uuid.UUID,
    payload: RoleUpdateRequest,
    request: Request,
    db: Db,
    context: RoleUpdate,
) -> RoleView:
    return await _service().update_role(
        db, _tenant(context), context.user_id, role_id, payload, _ip(request), _user_agent(request)
    )


@router.delete("/rbac/roles/{role_id}")
async def delete_role(
    role_id: uuid.UUID, request: Request, db: Db, context: RoleDelete
) -> dict[str, str]:
    await _service().delete_role(
        db, _tenant(context), context.user_id, role_id, _ip(request), _user_agent(request)
    )
    return {"message": "Role deleted"}
