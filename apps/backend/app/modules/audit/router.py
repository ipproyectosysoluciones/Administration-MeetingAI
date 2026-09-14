"""Audit routes: GET /audit (paginated+filtered) and GET /audit/{event_id} (single event).

Permission: audit.read (enforced via require_auth dependency).
Append-only: no API mutation path — read-only endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_auth, AuthContext
from app.core.exceptions import APIError
from app.modules.audit.service import AuditService
from app.modules.audit.schemas import AuditEventResponse, AuditEventsPaginatedResponse

router = APIRouter(tags=["audit"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.get("/audit", response_model=AuditEventsPaginatedResponse)
async def list_audit_events(
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth()),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = Query(default=None),
    resource: str | None = Query(default=None),
    resource_id: uuid.UUID | None = Query(default=None),
    actor_user_id: uuid.UUID | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    ip: str | None = Query(default=None),
) -> dict:
    """Paginated, filterable audit log for the current tenant (api-contract.md §6.1).

    Requires ``audit.read`` permission (enforced by ``require_auth`` dependency).
    Results are automatically scoped to the authenticated user's active tenant.
    """
    tenant_id: uuid.UUID | None = auth.tenant_id

    if tenant_id is None:
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP", "No active tenant membership")

    # Parse ISO 8601 dates if provided
    parsed_date_from: datetime | None = None
    parsed_date_to: datetime | None = None
    if date_from is not None:
        try:
            parsed_date_from = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            raise APIError(400, "INVALID_DATE_FROM", "date_from must be ISO 8601")

    if date_to is not None:
        try:
            parsed_date_to = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            raise APIError(400, "INVALID_DATE_TO", "date_to must be ISO 8601")

    query_result = await AuditService.query(
        session=db,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        action=action,
        resource=resource,
        resource_id=resource_id,
        actor_user_id=actor_user_id,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
        ip=ip,
    )

    return query_result


@router.get("/audit/{event_id}", response_model=AuditEventResponse)
async def get_audit_event(
    event_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth()),
) -> dict:
    """Single audit event detail (api-contract.md §6.2).

    Requires ``audit.read`` permission.
    Returns 404 ``AUDIT_EVENT_NOT_FOUND`` when the event is not in the current tenant.
    """
    tenant_id: uuid.UUID | None = auth.tenant_id

    if tenant_id is None:
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP", "No active tenant membership")

    event = await AuditService.get(session=db, tenant_id=tenant_id, event_id=event_id)
    if event is None:
        raise APIError(404, "AUDIT_EVENT_NOT_FOUND", "Audit event not found in current tenant")

    return event
