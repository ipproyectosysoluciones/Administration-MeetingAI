"""Meeting participants routes (meetings-crud, TASK-220/221)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthContext, get_db, require_permission
from app.core.exceptions import APIError
from app.modules.meetings.participants_service import ParticipantService
from app.modules.meetings.schemas import (
    ParticipantAddRequest,
    ParticipantListResponse,
    ParticipantResponse,
)

router = APIRouter(tags=["meetings"])

Db = Annotated[AsyncSession, Depends(get_db)]
ParticipantManage = Annotated[
    AuthContext, Depends(require_permission("meeting.participant_manage"))
]


def _svc() -> ParticipantService:
    return ParticipantService()


def _tenant(auth: AuthContext) -> uuid.UUID:
    if auth.tenant_id is None:
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP", "No active tenant membership")
    return auth.tenant_id


@router.get(
    "/meetings/{meeting_id}/participants",
    response_model=ParticipantListResponse,
)
async def list_participants(
    meeting_id: uuid.UUID,
    db: Db,
    auth: Annotated[AuthContext, Depends(require_permission("meeting.read"))],
) -> dict:
    return await _svc().list(db, meeting_id, _tenant(auth))


@router.post(
    "/meetings/{meeting_id}/participants",
    response_model=ParticipantResponse,
    status_code=201,
)
async def add_participant(
    meeting_id: uuid.UUID,
    payload: ParticipantAddRequest,
    request: Request,
    db: Db,
    auth: ParticipantManage,
) -> dict:
    if payload.user_id is None and payload.external_email is None:
        raise APIError(422, "PARTICIPANT_CHANNEL_REQUIRED", "user_id or external_email required")
    if payload.user_id is not None and payload.external_email is not None:
        raise APIError(422, "PARTICIPANT_AMBIGUOUS", "Only one of user_id / external_email allowed")
    ip = request.client.host if request.client else None
    return await _svc().add(
        db,
        meeting_id,
        _tenant(auth),
        auth.user_id,
        payload,
        ip,
        request.headers.get("user-agent"),
    )


@router.delete("/meetings/{meeting_id}/participants/{participant_id}", status_code=204)
async def remove_participant(
    meeting_id: uuid.UUID,
    participant_id: uuid.UUID,
    request: Request,
    db: Db,
    auth: ParticipantManage,
) -> None:
    ip = request.client.host if request.client else None
    await _svc().remove(
        db,
        meeting_id,
        participant_id,
        _tenant(auth),
        auth.user_id,
        ip,
        request.headers.get("user-agent"),
    )
