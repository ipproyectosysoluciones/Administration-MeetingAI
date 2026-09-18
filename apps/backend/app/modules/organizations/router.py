"""Organizations routes: org + property/group + membership management (TASK-060).

``POST /organizations`` and ``DELETE /organizations/{id}`` are super-admin only (the
``organization.create``/``organization.delete`` permissions are granted to no tenant role,
so the super-admin wildcard is the only path). Tenant-scoped ``/organizations/me`` paths
gate on the matching ``organization.*``/``property.*``/``membership.*`` permission.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthContext, get_db, require_auth, require_permission
from app.core.exceptions import APIError
from app.modules.organizations.schemas import (
    MembershipCreateRequest,
    MembershipListResponse,
    MembershipResponse,
    MembershipUpdateRequest,
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
    PropertyCreateRequest,
    PropertyListResponse,
    PropertyResponse,
    PropertyUpdateRequest,
)
from app.modules.organizations.service import OrganizationService

router = APIRouter(tags=["organizations"])

Db = Annotated[AsyncSession, Depends(get_db)]
Authenticated = Annotated[AuthContext, Depends(require_auth())]
OrgRead = Annotated[AuthContext, Depends(require_permission("organization.read"))]
OrgUpdate = Annotated[AuthContext, Depends(require_permission("organization.update"))]
PropertyRead = Annotated[AuthContext, Depends(require_permission("property.read"))]
PropertyCreate = Annotated[AuthContext, Depends(require_permission("property.create"))]
PropertyUpdate = Annotated[AuthContext, Depends(require_permission("property.update"))]
PropertyDelete = Annotated[AuthContext, Depends(require_permission("property.delete"))]
MembershipRead = Annotated[AuthContext, Depends(require_permission("membership.read"))]
MembershipCreate = Annotated[AuthContext, Depends(require_permission("membership.create"))]
MembershipUpdate = Annotated[AuthContext, Depends(require_permission("membership.update"))]
MembershipDelete = Annotated[AuthContext, Depends(require_permission("membership.delete"))]


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


def _pages(total: int, page_size: int) -> int:
    return (total + page_size - 1) // page_size if total else 1


# -- organization ------------------------------------------------------------


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


# -- properties --------------------------------------------------------------


@router.get("/organizations/me/properties", response_model=PropertyListResponse)
async def list_properties(
    request: Request,
    db: Db,
    context: PropertyRead,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PropertyListResponse:
    tenant_id = _require_tenant(context)
    items, total = await _service().list_properties(db, tenant_id, page, page_size)
    return PropertyListResponse(
        items=items, total=total, page=page, page_size=page_size, pages=_pages(total, page_size)
    )


@router.post("/organizations/me/properties", response_model=PropertyResponse, status_code=201)
async def create_property(
    payload: PropertyCreateRequest, request: Request, db: Db, context: PropertyCreate
) -> PropertyResponse:
    tenant_id = _require_tenant(context)
    return await _service().create_property(
        db, tenant_id, context.user_id, payload, _ip(request), _user_agent(request)
    )


@router.patch("/organizations/me/properties/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: uuid.UUID,
    payload: PropertyUpdateRequest,
    request: Request,
    db: Db,
    context: PropertyUpdate,
) -> PropertyResponse:
    tenant_id = _require_tenant(context)
    return await _service().update_property(
        db, tenant_id, context.user_id, property_id, payload, _ip(request), _user_agent(request)
    )


@router.delete("/organizations/me/properties/{property_id}")
async def delete_property(
    property_id: uuid.UUID, request: Request, db: Db, context: PropertyDelete
) -> dict[str, str]:
    tenant_id = _require_tenant(context)
    await _service().soft_delete_property(
        db, tenant_id, context.user_id, property_id, _ip(request), _user_agent(request)
    )
    return {"message": "Property deleted"}


# -- memberships -------------------------------------------------------------


@router.get("/organizations/me/memberships", response_model=MembershipListResponse)
async def list_memberships(
    request: Request,
    db: Db,
    context: MembershipRead,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> MembershipListResponse:
    tenant_id = _require_tenant(context)
    items, total = await _service().list_memberships(db, tenant_id, page, page_size)
    return MembershipListResponse(
        items=items, total=total, page=page, page_size=page_size, pages=_pages(total, page_size)
    )


@router.post("/organizations/me/memberships", response_model=MembershipResponse, status_code=201)
async def create_membership(
    payload: MembershipCreateRequest, request: Request, db: Db, context: MembershipCreate
) -> MembershipResponse:
    tenant_id = _require_tenant(context)
    return await _service().create_membership(
        db, tenant_id, context.user_id, payload, _ip(request), _user_agent(request)
    )


@router.patch("/organizations/me/memberships/{membership_id}", response_model=MembershipResponse)
async def update_membership(
    membership_id: uuid.UUID,
    payload: MembershipUpdateRequest,
    request: Request,
    db: Db,
    context: MembershipUpdate,
) -> MembershipResponse:
    tenant_id = _require_tenant(context)
    return await _service().update_membership(
        db, tenant_id, context.user_id, membership_id, payload, _ip(request), _user_agent(request)
    )


@router.delete("/organizations/me/memberships/{membership_id}")
async def delete_membership(
    membership_id: uuid.UUID, request: Request, db: Db, context: MembershipDelete
) -> dict[str, str]:
    tenant_id = _require_tenant(context)
    await _service().soft_delete_membership(
        db, tenant_id, context.user_id, membership_id, _ip(request), _user_agent(request)
    )
    return {"message": "Member removed"}
