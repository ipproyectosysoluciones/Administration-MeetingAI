"""Recordings REST router (TASK-252).

Tenant scoping is resolved server-side from the verified identity (never from a
client-supplied tenant). All uploads/downloads audit-logged.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthContext, get_db, require_permission
from app.core.exceptions import APIError
from app.modules.recordings.schemas import RecordingResponse
from app.modules.recordings.service import RecordingService

router = APIRouter(tags=["recordings"])

Db = Annotated[AsyncSession, Depends(get_db)]
RecordingUpload = Annotated[AuthContext, Depends(require_permission("recording.upload"))]
RecordingRead = Annotated[AuthContext, Depends(require_permission("recording.read"))]
RecordingDelete = Annotated[AuthContext, Depends(require_permission("recording.delete"))]


def _service(request: Request) -> RecordingService:
    return request.app.state.recording_service


def _tenant(auth: AuthContext) -> uuid.UUID:
    if auth.tenant_id is None:
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP", "No active tenant membership")
    return auth.tenant_id


# ---- uploads ---------------------------------------------------------------


@router.post(
    "/meetings/{meeting_id}/recordings",
    response_model=RecordingResponse,
    status_code=201,
)
async def upload_recording(
    meeting_id: uuid.UUID,
    request: Request,
    response: Response,
    db: Db,
    auth: RecordingUpload,
    file: UploadFile,
) -> RecordingResponse:
    svc = _service(request)
    result = await svc.upload(
        db,
        tenant_id=_tenant(auth),
        meeting_id=meeting_id,
        upload=file,
        uploaded_by=auth.user_id,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    status = result.pop("_status", 201)
    response.status_code = status
    return RecordingResponse.model_validate(result)


# ---- listing ---------------------------------------------------------------


@router.get("/meetings/{meeting_id}/recordings", response_model=list[RecordingResponse])
async def list_recordings(
    meeting_id: uuid.UUID,
    request: Request,
    db: Db,
    auth: RecordingRead,
) -> list[RecordingResponse]:
    svc = _service(request)
    rows = await svc.list_for_meeting(db, meeting_id=meeting_id, tenant_id=_tenant(auth))
    return [RecordingResponse.model_validate(r) for r in rows]


# ---- single ----------------------------------------------------------------


@router.get("/recordings/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: uuid.UUID,
    request: Request,
    db: Db,
    auth: RecordingRead,
) -> RecordingResponse:
    svc = _service(request)
    result = await svc.get(db, recording_id=recording_id, tenant_id=_tenant(auth))
    return RecordingResponse.model_validate(result)


# ---- download (streams, audit-logged) ----------------------------------------


@router.get("/recordings/{recording_id}/content")
async def download_recording(
    recording_id: uuid.UUID,
    response: Response,
    request: Request,
    db: Db,
    auth: RecordingRead,
) -> StreamingResponse:
    svc = _service(request)
    fh, content_type, filename = await svc.stream(
        db,
        recording_id=recording_id,
        tenant_id=_tenant(auth),
        actor_user_id=auth.user_id,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return StreamingResponse(
        fh,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---- soft delete ------------------------------------------------------------


@router.delete("/recordings/{recording_id}", status_code=204)
async def delete_recording(
    recording_id: uuid.UUID,
    request: Request,
    db: Db,
    auth: RecordingDelete,
) -> None:
    await _service(request).delete(
        db,
        recording_id=recording_id,
        tenant_id=_tenant(auth),
        actor_user_id=auth.user_id,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
