"""Meetings routes: tenant-scoped CRUD per api-contract.md (meetings-crud)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthContext, get_db, require_permission
from app.core.exceptions import APIError
from app.modules.meetings.schemas import (
    MeetingCreateRequest,
    MeetingListResponse,
    MeetingResponse,
    MeetingUpdateRequest,
)
from app.modules.meetings.service import MeetingService

router = APIRouter(tags=["meetings"])

Db = Annotated[AsyncSession, Depends(get_db)]
MeetingCreate = Annotated[AuthContext, Depends(require_permission("meeting.create"))]
MeetingRead = Annotated[AuthContext, Depends(require_permission("meeting.read"))]
MeetingUpdate = Annotated[AuthContext, Depends(require_permission("meeting.update"))]
MeetingCancel = Annotated[AuthContext, Depends(require_permission("meeting.cancel"))]


def _service() -> MeetingService:
    return MeetingService()


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _tenant(auth: AuthContext) -> uuid.UUID:
    if auth.tenant_id is None:
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP", "No active tenant membership")
    return auth.tenant_id


def _parse_iso(value: str | None, code: str) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise APIError(400, code, "date parameter must be ISO 8601") from exc


@router.post("/meetings", response_model=MeetingResponse, status_code=201)
async def create_meeting(
    payload: MeetingCreateRequest, request: Request, db: Db, auth: MeetingCreate
) -> dict:
    tenant_id = _tenant(auth)
    return await _service().create(
        db, tenant_id, auth.user_id, payload, _ip(request), _user_agent(request)
    )


@router.get("/meetings", response_model=MeetingListResponse)
async def list_meetings(
    request: Request,
    db: Db,
    auth: MeetingRead,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    q: str | None = None,
) -> dict:
    tenant_id = _tenant(auth)
    return await _service().list(
        db,
        tenant_id,
        page=page,
        page_size=page_size,
        status=status,
        date_from=_parse_iso(date_from, "INVALID_DATE_FROM"),
        date_to=_parse_iso(date_to, "INVALID_DATE_TO"),
        q=q,
    )


@router.get("/meetings/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting_id: uuid.UUID, db: Db, auth: MeetingRead) -> dict:
    return await _service().get(db, meeting_id, _tenant(auth))


@router.patch("/meetings/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: uuid.UUID,
    payload: MeetingUpdateRequest,
    request: Request,
    db: Db,
    auth: MeetingUpdate,
) -> dict:
    return await _service().update(
        db, meeting_id, _tenant(auth), auth.user_id, payload, _ip(request), _user_agent(request)
    )


@router.post("/meetings/{meeting_id}/cancel", response_model=MeetingResponse)
async def cancel_meeting(
    meeting_id: uuid.UUID, request: Request, db: Db, auth: MeetingCancel
) -> dict:
    return await _service().cancel(
        db, meeting_id, _tenant(auth), auth.user_id, _ip(request), _user_agent(request)
    )
