"""Audit routes: GET /audit (paginated+filtered) and GET /audit/{event_id} (single event).

Permission: audit.read (enforced via require_permission dependency).
Append-only: no API mutation path — read-only endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthContext, get_db, require_permission
from app.core.exceptions import APIError
from app.modules.audit.schemas import AuditEventResponse, AuditEventsPaginatedResponse
from app.modules.audit.service import AuditService

router = APIRouter(tags=["audit"])

AuditRead = Annotated[AuthContext, Depends(require_permission("audit.read"))]
DbSession = Annotated[AsyncSession, Depends(get_db)]


def _parse_iso8601(raw: str, code: str) -> datetime:
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as err:
        raise APIError(400, code, "date parameter must be ISO 8601") from err


@router.get("/audit", response_model=AuditEventsPaginatedResponse)
async def list_audit_events(
    request: Request,
    db: DbSession,
    auth: AuditRead,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    action: str | None = None,
    resource: str | None = None,
    resource_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    ip: str | None = None,
) -> dict:
    """Paginated, filterable audit log for the current tenant (api-contract.md §6.1).

    Requires ``audit.read`` permission (enforced by ``require_permission("audit.read")``).
    Results are automatically scoped to the authenticated user's active tenant.
    """
    tenant_id = auth.tenant_id
    if tenant_id is None:
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP", "No active tenant membership")

    parsed_date_from = _parse_iso8601(date_from, "INVALID_DATE_FROM") if date_from else None
    parsed_date_to = _parse_iso8601(date_to, "INVALID_DATE_TO") if date_to else None

    return await AuditService.query(
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


@router.get("/audit/{event_id}", response_model=AuditEventResponse)
async def get_audit_event(
    event_id: uuid.UUID,
    request: Request,
    db: DbSession,
    auth: AuditRead,
) -> dict:
    """Single audit event detail (api-contract.md §6.2).

    Requires ``audit.read`` permission.
    Returns 404 ``AUDIT_EVENT_NOT_FOUND`` when the event is not in the current tenant.
    """
    tenant_id = auth.tenant_id
    if tenant_id is None:
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP", "No active tenant membership")

    event = await AuditService.get(session=db, tenant_id=tenant_id, event_id=event_id)
    if event is None:
        raise APIError(404, "AUDIT_EVENT_NOT_FOUND", "Audit event not found in current tenant")

    return event
