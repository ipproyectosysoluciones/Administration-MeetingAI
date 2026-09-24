"""Transcription REST router — read-only surface (TASK-304).

Cross-tenant policy: 404 (not 403) so existence is never leaked across tenants.
Writes/transitions are not part of this surface; the worker owns them.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthContext, get_db, require_permission
from app.core.exceptions import APIError
from app.modules.transcription.schemas import TranscriptionListResponse, TranscriptionResponse
from app.modules.transcription.service import TranscriptionService

router = APIRouter(tags=["transcriptions"])

Db = Annotated[AsyncSession, Depends(get_db)]
TranscriptionRead = Annotated[AuthContext, Depends(require_permission("transcription.read"))]

_MAX_PAGE_SIZE = 50


def _service(request: Request) -> TranscriptionService:
    return request.app.state.transcription_service


def _tenant(auth: AuthContext) -> uuid.UUID:
    if auth.tenant_id is None:
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP", "No active tenant membership")
    return auth.tenant_id


@router.get("/transcriptions/{transcription_id}", response_model=TranscriptionResponse)
async def get_transcription(
    transcription_id: uuid.UUID,
    request: Request,
    db: Db,
    auth: TranscriptionRead,
) -> TranscriptionResponse:
    row = await _service(request).get(
        db, transcription_id=transcription_id, tenant_id=_tenant(auth)
    )
    return TranscriptionResponse.model_validate(row)


@router.get(
    "/recordings/{recording_id}/transcriptions",
    response_model=TranscriptionListResponse,
)
async def list_recording_transcriptions(
    recording_id: uuid.UUID,
    request: Request,
    db: Db,
    auth: TranscriptionRead,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=_MAX_PAGE_SIZE),
) -> TranscriptionListResponse:
    return await _service(request).list_for_recording(
        db, recording_id=recording_id, tenant_id=_tenant(auth), page=page, page_size=page_size
    )
