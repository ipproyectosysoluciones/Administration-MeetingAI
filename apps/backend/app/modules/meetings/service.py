"""Meetings business logic: CRUD, FSM transitions, audit (api-contract §meetings)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.modules.audit.service import AuditService
from app.modules.meetings.models import MEETING_TRANSITIONS, Meeting
from app.modules.meetings.schemas import (
    MeetingCreateRequest,
    MeetingUpdateRequest,
)


def _public(meeting: Meeting) -> dict[str, Any]:
    return {
        "id": meeting.id,
        "organization_id": meeting.organization_id,
        "title": meeting.title,
        "description": meeting.description,
        "starts_at": meeting.starts_at,
        "ends_at": meeting.ends_at,
        "location": meeting.location,
        "modality": meeting.modality,
        "status": meeting.status,
        "created_at": meeting.created_at,
        "updated_at": meeting.updated_at,
    }


class MeetingService:
    """Tenant-scoped meeting operations; every mutation writes one audit event."""

    async def _get_scoped(
        self, session: AsyncSession, meeting_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Meeting:
        row = (
            await session.execute(
                select(Meeting).where(
                    Meeting.id == meeting_id,
                    Meeting.organization_id == tenant_id,
                    Meeting.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise APIError(404, "MEETING_NOT_FOUND", "Meeting not found")
        return row

    async def create(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: MeetingCreateRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> dict[str, Any]:
        if payload.ends_at <= payload.starts_at:
            raise APIError(422, "INVALID_TIME_RANGE", "ends_at must be after starts_at")
        meeting = Meeting(
            organization_id=tenant_id,
            title=payload.title,
            description=payload.description,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            location=payload.location,
            modality=payload.modality,
        )
        session.add(meeting)
        await session.flush()
        await AuditService.record(
            session,
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            action="meeting.create",
            resource="meeting",
            resource_id=meeting.id,
            ip=ip,
            user_agent=user_agent,
        )
        await session.commit()
        await session.refresh(meeting)
        return _public(meeting)

    async def get(
        self, session: AsyncSession, meeting_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict[str, Any]:
        return _public(await self._get_scoped(session, meeting_id, tenant_id))

    async def list(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
        status: str | None,
        date_from: Any,
        date_to: Any,
        q: str | None,
    ) -> dict[str, Any]:
        stmt = select(Meeting).where(
            Meeting.organization_id == tenant_id, Meeting.deleted_at.is_(None)
        )
        if status is not None:
            stmt = stmt.where(Meeting.status == status)
        if date_from is not None:
            stmt = stmt.where(Meeting.starts_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(Meeting.starts_at <= date_to)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Meeting.title.ilike(like), Meeting.location.ilike(like)))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await session.execute(count_stmt)).scalar_one()

        stmt = (
            stmt.order_by(Meeting.starts_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        rows = (await session.execute(stmt)).scalars().all()
        return {
            "items": [_public(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": -(-total // page_size),
        }

    async def update(
        self,
        session: AsyncSession,
        meeting_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: MeetingUpdateRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> dict[str, Any]:
        meeting = await self._get_scoped(session, meeting_id, tenant_id)

        fields = payload.model_dump(exclude_unset=True)
        new_status = fields.pop("status", None)
        status_changed = new_status is not None and new_status != meeting.status
        for key, value in fields.items():
            setattr(meeting, key, value)

        if "starts_at" in fields or "ends_at" in fields:
            if meeting.ends_at <= meeting.starts_at:
                raise APIError(422, "INVALID_TIME_RANGE", "ends_at must be after starts_at")

        if status_changed:
            allowed = MEETING_TRANSITIONS.get(meeting.status, set())
            if new_status not in allowed:
                raise APIError(
                    422,
                    "INVALID_STATUS_TRANSITION",
                    f"Cannot transition from {meeting.status} to {new_status}",
                )
            meeting.status = new_status

        if fields or status_changed:
            await AuditService.record(
                session,
                actor_user_id=actor_user_id,
                tenant_id=tenant_id,
                action="meeting.update",
                resource="meeting",
                resource_id=meeting.id,
                ip=ip,
                user_agent=user_agent,
            )
            await session.commit()
            await session.refresh(meeting)
        return _public(meeting)

    async def cancel(
        self,
        session: AsyncSession,
        meeting_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> dict[str, Any]:
        meeting = await self._get_scoped(session, meeting_id, tenant_id)
        if meeting.status in ("finished", "cancelled"):
            raise APIError(
                422, "INVALID_STATUS_TRANSITION", f"Cannot cancel a {meeting.status} meeting"
            )
        meeting.status = "cancelled"
        await AuditService.record(
            session,
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            action="meeting.cancel",
            resource="meeting",
            resource_id=meeting.id,
            ip=ip,
            user_agent=user_agent,
        )
        await session.commit()
        await session.refresh(meeting)
        return _public(meeting)
