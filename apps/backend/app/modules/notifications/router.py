"""Notifications REST router (internal - triggered by other modules)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthContext
from app.modules.notifications.service import NotificationsService

router = APIRouter(tags=["notifications"], prefix="/notifications")

Db = Annotated["AsyncSession", "get_db"]
Admin = Annotated["AuthContext", "Depends(require_permission(\"notifications.send\"))"]


def _service() -> NotificationsService:
    from app.modules.notifications.service import NotificationsService
    return NotificationsService()


def _tenant(auth) -> uuid.UUID:
    if auth.tenant_id is None:
        from app.core.exceptions import APIError
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP", "No active tenant membership")
    return auth.tenant_id


@router.post("/minutes/reviewed", status_code=202)
async def notify_minute_reviewed(
    request: Request,
    db,
    auth,
    minute_id: uuid.UUID,
    minute_title: str,
    reviewer_name: str,
    recipient_user_ids: list[uuid.UUID],
):
    """Notify that a minute has been reviewed."""
    svc = NotificationsService()
    count = await svc.notify_minute_reviewed(
        db,
        tenant_id=auth.tenant_id,
        minute_id=minute_id,
        minute_title=minute_title,
        reviewed_by=auth.user_id,
        reviewer_name=reviewer_name,
        recipient_user_ids=recipient_user_ids,
    )
    return {"sent": count}


@router.post("/minutes/approved", status_code=202)
async def notify_minute_approved(
    request: Request,
    db,
    auth,
    minute_id: uuid.UUID,
    minute_title: str,
    approver_name: str,
    recipient_user_ids: list[uuid.UUID],
):
    """Notify that a minute has been approved."""
    svc = NotificationsService()
    count = await svc.notify_minute_approved(
        db,
        tenant_id=auth.tenant_id,
        minute_id=minute_id,
        minute_title=minute_title,
        approved_by=auth.user_id,
        approver_name=approver_name,
        recipient_user_ids=recipient_user_ids,
    )
    return {"sent": count}


@router.post("/minutes/published", status_code=202)
async def notify_minute_published(
    request: Request,
    db,
    auth,
    minute_id: uuid.UUID,
    minute_title: str,
    publisher_name: str,
    recipient_user_ids: list[uuid.UUID],
):
    """Notify that a minute has been published."""
    svc = NotificationsService()
    count = await svc.notify_minute_published(
        db,
        tenant_id=auth.tenant_id,
        minute_id=minute_id,
        minute_title=minute_title,
        published_by=auth.user_id,
        publisher_name=publisher_name,
        recipient_user_ids=recipient_user_ids,
    )
    return {"sent": count}


@router.post("/minutes/archived", status_code=202)
async def notify_minute_archived(
    request: Request,
    db,
    auth,
    minute_id: uuid.UUID,
    minute_title: str,
    archiver_name: str,
    recipient_user_ids: list[uuid.UUID],
):
    """Notify that a minute has been archived."""
    svc = NotificationsService()
    count = await svc.notify_minute_archived(
        db,
        tenant_id=auth.tenant_id,
        minute_id=minute_id,
        minute_title=minute_title,
        archived_by=auth.user_id,
        archiver_name=archiver_name,
        recipient_user_ids=recipient_user_ids,
    )
    return {"sent": count}


@router.post("/minutes/draft-created", status_code=202)
async def notify_minute_draft_created(
    request: Request,
    db,
    auth,
    minute_id: uuid.UUID,
    minute_title: str,
    creator_name: str,
    recipient_user_ids: list[uuid.UUID],
):
    """Notify that a new minute draft was created."""
    svc = NotificationsService()
    count = await svc.notify_minute_draft_created(
        db,
        tenant_id=auth.tenant_id,
        minute_id=minute_id,
        minute_title=minute_title,
        created_by=auth.user_id,
        creator_name=creator_name,
        recipient_user_ids=recipient_user_ids,
    )
    return {"sent": count}


@router.post("/minutes/content-updated", status_code=202)
async def notify_minute_content_updated(
    request: Request,
    db,
    auth,
    minute_id: uuid.UUID,
    minute_title: str,
    updater_name: str,
    recipient_user_ids: list[uuid.UUID],
):
    """Notify that minute content was updated (new version)."""
    svc = NotificationsService()
    count = await svc.notify_minute_content_updated(
        db,
        tenant_id=auth.tenant_id,
        minute_id=minute_id,
        minute_title=minute_title,
        updated_by=auth.user_id,
        updater_name=updater_name,
        recipient_user_ids=recipient_user_ids,
    )
    return {"sent": count}