"""Users routes: self-service (/users/me) + tenant-scoped admin CRUD (TASK-050).

Self-service paths (profile read/update, password change) gate on ``require_auth`` —
the operation is inherently scoped to the caller's own account (mirroring PR-3's
``auth.revoke``/MFA deviations; the ``user.update``/``user.password.change``
permissions are not granted to non-admin roles). Admin CRUD gates on the
``user.read``/``user.update``/``user.delete`` permissions per specs/users/spec.md.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthContext, get_db, require_auth, require_permission
from app.core.exceptions import APIError
from app.modules.users.schemas import (
    PasswordChangeRequest,
    UserAdminUpdateRequest,
    UserDeleteResponse,
    UserListResponse,
    UserMeResponse,
)
from app.modules.users.service import UserService

router = APIRouter(tags=["users"])

Db = Annotated[AsyncSession, Depends(get_db)]
Authenticated = Annotated[AuthContext, Depends(require_auth())]
UserRead = Annotated[AuthContext, Depends(require_permission("user.read"))]
UserUpdate = Annotated[AuthContext, Depends(require_permission("user.update"))]
UserDelete = Annotated[AuthContext, Depends(require_permission("user.delete"))]

# Fields a self-service profile update must never change (specs/users/spec.md —
# "cannot change email, roles, tenant").
RESTRICTED_SELF_FIELDS = frozenset(
    {
        "email",
        "role",
        "roles",
        "tenant_id",
        "organization_id",
        "membership",
        "is_active",
        "is_super_admin",
        "password",
        "password_hash",
        "deleted_at",
    }
)

ALLOWED_SELF_FIELDS = frozenset({"full_name", "avatar_url"})


def _service(request: Request) -> UserService:
    return UserService(password_hasher=request.app.state.password_hasher)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _require_tenant(context: AuthContext) -> uuid.UUID:
    if context.tenant_id is None:
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP")
    return context.tenant_id


@router.get("/users/me", response_model=UserMeResponse)
async def get_me(request: Request, db: Db, context: Authenticated) -> UserMeResponse:
    tenant_id = _require_tenant(context)
    return await _service(request).get_me(db, context.user_id, tenant_id, context.permissions)


@router.patch("/users/me", response_model=UserMeResponse)
async def update_me(request: Request, db: Db, context: Authenticated) -> UserMeResponse:
    tenant_id = _require_tenant(context)
    body = await request.json()
    restricted = sorted(set(body) & RESTRICTED_SELF_FIELDS)
    if restricted:
        raise APIError(403, "FIELD_NOT_ALLOWED", f"Cannot modify field(s): {', '.join(restricted)}")
    updates = {key: value for key, value in body.items() if key in ALLOWED_SELF_FIELDS}
    return await _service(request).update_me(
        db, context.user_id, tenant_id, context.permissions, updates
    )


@router.post("/users/me/password")
async def change_password(
    payload: PasswordChangeRequest, request: Request, db: Db, context: Authenticated
) -> dict[str, str]:
    tenant_id = _require_tenant(context)
    await _service(request).change_password(
        db,
        context.user_id,
        tenant_id,
        payload.current_password,
        payload.new_password,
        _ip(request),
        _user_agent(request),
    )
    return {"message": "Password changed successfully"}


@router.get("/users", response_model=UserListResponse)
async def list_users(
    request: Request,
    db: Db,
    context: UserRead,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = None,
    is_active: bool | None = None,
    role: str | None = None,
) -> UserListResponse:
    tenant_id = _require_tenant(context)
    items, total = await _service(request).list_users(
        db, tenant_id, page, page_size, search, is_active, role
    )
    pages = (total + page_size - 1) // page_size if total else 1
    return UserListResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/users/{user_id}", response_model=None)
async def get_user(user_id: uuid.UUID, request: Request, db: Db, context: UserRead) -> object:
    tenant_id = _require_tenant(context)
    return await _service(request).get_user(db, tenant_id, user_id)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    payload: UserAdminUpdateRequest,
    request: Request,
    db: Db,
    context: UserUpdate,
) -> object:
    tenant_id = _require_tenant(context)
    return await _service(request).update_user(
        db,
        tenant_id,
        context.user_id,
        user_id,
        payload,
        _ip(request),
        _user_agent(request),
    )


@router.delete("/users/{user_id}", response_model=UserDeleteResponse)
async def delete_user(
    user_id: uuid.UUID, request: Request, db: Db, context: UserDelete
) -> UserDeleteResponse:
    tenant_id = _require_tenant(context)
    deleted_at = await _service(request).soft_delete_user(
        db, tenant_id, context.user_id, user_id, _ip(request), _user_agent(request)
    )
    return UserDeleteResponse(message="User deleted", deleted_at=deleted_at)
