"""Organizations routes: platform org creation (super-admin) + tenant-scoped CRUD.

``POST /organizations`` is super-admin only (``organization.create`` per spec — the matrix
grants it to no tenant role, so the super-admin wildcard is the only path). Read/update/
delete of the caller's own organization are tenant-scoped via ``/organizations/me`` and
gate on ``organization.read``/``organization.update``/``organization.delete``.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthContext, get_db, require_auth, require_permission
from app.core.exceptions import APIError
from app.modules.organizations.schemas import (
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
)
from app.modules.organizations.service import OrganizationService

router = APIRouter(tags=["organizations"])

Db = Annotated[AsyncSession, Depends(get_db)]
Authenticated = Annotated[AuthContext, Depends(require_auth())]
OrgRead = Annotated[AuthContext, Depends(require_permission("organization.read"))]
OrgUpdate = Annotated[AuthContext, Depends(require_permission("organization.update"))]


def _service() -> OrganizationService:
    return OrganizationService()


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _require_tenant(context: AuthContext) -> uuid.UUID:
    if context.tenant_id is None:
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP")
    return context.tenant_id


@router.post("/organizations", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    payload: OrganizationCreateRequest, request: Request, db: Db, context: Authenticated
) -> OrganizationResponse:
    if not context.is_super_admin:
        raise APIError(403, "SUPER_ADMIN_REQUIRED", "Super-admin privileges required")
    return await _service().create_organization(
        db, context.user_id, payload, _ip(request), _user_agent(request)
    )


@router.get("/organizations/me", response_model=OrganizationResponse)
async def get_me(request: Request, db: Db, context: OrgRead) -> OrganizationResponse:
    tenant_id = _require_tenant(context)
    return await _service().get_me(db, tenant_id)


@router.patch("/organizations/me", response_model=OrganizationResponse)
async def update_me(
    payload: OrganizationUpdateRequest, request: Request, db: Db, context: OrgUpdate
) -> OrganizationResponse:
    tenant_id = _require_tenant(context)
    return await _service().update_me(
        db, tenant_id, context.user_id, payload, _ip(request), _user_agent(request)
    )


@router.delete("/organizations/{organization_id}")
async def delete_organization(
    organization_id: uuid.UUID, request: Request, db: Db, context: Authenticated
) -> dict[str, str]:
    if not context.is_super_admin:
        raise APIError(403, "SUPER_ADMIN_REQUIRED", "Super-admin privileges required")
    await _service().soft_delete_organization(
        db, organization_id, context.user_id, _ip(request), _user_agent(request)
    )
    return {"message": "Organization deleted"}
