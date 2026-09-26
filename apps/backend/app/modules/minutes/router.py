"""Minutes REST router (MIN-103) — lifecycle + cross-tenant reads.

Cross-tenant policy: 404 (not 403) so existence is never leaked across tenants.
Mutations are permission-gated: write (draft/review), approve, publish.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthContext, get_db, require_permission
from app.core.exceptions import APIError
from app.modules.minutes.schemas import (
    MinuteCreateRequest,
    MinuteListResponse,
    MinuteResponse,
)
from app.modules.minutes.service import MinutesService

router = APIRouter(tags=["minutes"])

Db = Annotated[AsyncSession, Depends(get_db)]
MinuteRead = Annotated[AuthContext, Depends(require_permission("minutes.read"))]
MinuteWrite = Annotated[AuthContext, Depends(require_permission("minutes.write"))]
MinuteApprove = Annotated[AuthContext, Depends(require_permission("minutes.approve"))]
MinutePublish = Annotated[AuthContext, Depends(require_permission("minutes.publish"))]

_MAX_PAGE_SIZE = 50


def _service() -> MinutesService:
    return MinutesService()


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _tenant(auth: AuthContext) -> uuid.UUID:
    if auth.tenant_id is None:
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP", "No active tenant membership")
    return auth.tenant_id


@router.get("/meetings/{meeting_id}/minutes", response_model=MinuteListResponse)
async def list_meeting_minutes(
    meeting_id: uuid.UUID,
    request: Request,
    db: Db,
    auth: MinuteRead,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=_MAX_PAGE_SIZE),
) -> MinuteListResponse:
    return await _service().list_for_meeting(
        db,
        meeting_id=meeting_id,
        tenant_id=_tenant(auth),
        page=page,
        page_size=page_size,
    )


@router.get("/minutes/{minute_id}", response_model=MinuteResponse)
async def get_minute(minute_id: uuid.UUID, db: Db, auth: MinuteRead) -> MinuteResponse:
    row = await _service().get_for_tenant(db, minute_id=minute_id, tenant_id=_tenant(auth))
    return MinuteResponse.model_validate(row)


@router.post("/meetings/{meeting_id}/minutes", response_model=MinuteResponse, status_code=201)
async def create_minute_draft(
    meeting_id: uuid.UUID,
    payload: MinuteCreateRequest,
    request: Request,
    db: Db,
    auth: MinuteWrite,
) -> MinuteResponse:
    row = await _service().create_draft(
        db,
        meeting_id=meeting_id,
        tenant_id=_tenant(auth),
        title=payload.title,
        content=payload.content,
        created_by=auth.user_id,
        ai_provider=payload.ai_provider,
        ai_model=payload.ai_model,
        ai_request_id=payload.ai_request_id,
    )
    await db.commit()
    return MinuteResponse.model_validate(row)


@router.post("/minutes/{minute_id}/review", response_model=MinuteResponse)
async def review_minute(
    minute_id: uuid.UUID, request: Request, db: Db, auth: MinuteWrite
) -> MinuteResponse:
    minute = await _service().get_for_tenant(db, minute_id=minute_id, tenant_id=_tenant(auth))
    row = await _service().mark_reviewed(
        db,
        minute=minute,
        reviewed_by=auth.user_id,
        ip=_ip(request),
        user_agent=_user_agent(request),
    )
    await db.commit()
    return MinuteResponse.model_validate(row)


@router.post("/minutes/{minute_id}/approve", response_model=MinuteResponse)
async def approve_minute(
    minute_id: uuid.UUID, request: Request, db: Db, auth: MinuteApprove
) -> MinuteResponse:
    minute = await _service().get_for_tenant(db, minute_id=minute_id, tenant_id=_tenant(auth))
    row = await _service().approve(
        db,
        minute=minute,
        approved_by=auth.user_id,
        ip=_ip(request),
        user_agent=_user_agent(request),
    )
    await db.commit()
    return MinuteResponse.model_validate(row)


@router.post("/minutes/{minute_id}/publish", response_model=MinuteResponse)
async def publish_minute(
    minute_id: uuid.UUID, request: Request, db: Db, auth: MinutePublish
) -> MinuteResponse:
    minute = await _service().get_for_tenant(db, minute_id=minute_id, tenant_id=_tenant(auth))
    row = await _service().publish(
        db,
        minute=minute,
        published_by=auth.user_id,
        ip=_ip(request),
        user_agent=_user_agent(request),
    )
    await db.commit()
    return MinuteResponse.model_validate(row)


@router.post("/minutes/{minute_id}/archive", response_model=MinuteResponse)
async def archive_minute(
    minute_id: uuid.UUID, request: Request, db: Db, auth: MinutePublish
) -> MinuteResponse:
    minute = await _service().get_for_tenant(db, minute_id=minute_id, tenant_id=_tenant(auth))
    row = await _service().archive(db, minute=minute, actor=auth.user_id)
    await db.commit()
    return MinuteResponse.model_validate(row)
