"""Users routes: self-service (/users/me) (TASK-050 self-service)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthContext, get_db, require_auth
from app.core.exceptions import APIError
from app.modules.users.schemas import (
    PasswordChangeRequest,
    UserMeResponse,
)
from app.modules.users.service import UserService

router = APIRouter(tags=["users"])

Db = Annotated[AsyncSession, Depends(get_db)]
Authenticated = Annotated[AuthContext, Depends(require_auth())]

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
