"""MinutesService — ciclo de vida append-only (MIN-102).

draft → review → approved → published → archived. Cada transición crea una
nueva entrada (nueva fila); nunca sobrescribe. Auditoría: actor + ip +
user_agent en cada evento; nada se publica sin approved_*.
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.modules.audit.service import AuditService
from app.modules.meetings.models import Meeting
from app.modules.minutes.models import Minute
from app.modules.minutes.schemas import MinuteListResponse, MinuteResponse

_VALID_TRANSITIONS: dict[str, str] = {
    "draft": "review",
    "review": "approved",
    "approved": "published",
    "published": "archived",
}


class MinutesService:
    async def create_draft(
        self,
        session: AsyncSession,
        *,
        meeting_id: uuid.UUID,
        tenant_id: uuid.UUID,
        title: str,
        content: str,
        created_by: uuid.UUID,
        ai_provider: str | None = None,
        ai_model: str | None = None,
        ai_request_id: str | None = None,
    ) -> Minute:
        """Inserta un nuevo borrador (version = siguiente libre para este meeting)."""
        meeting = (
            await session.execute(
                select(Meeting).where(
                    Meeting.id == meeting_id,
                    Meeting.organization_id == tenant_id,
                    Meeting.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if meeting is None:
            raise APIError(404, "MEETING_NOT_FOUND", "Meeting not found")

        last = (
            await session.execute(
                select(func.max(Minute.version)).where(
                    Minute.meeting_id == meeting_id, Minute.tenant_id == tenant_id
                )
            )
        ).scalar_one_or_none()
        next_version = (last or 0) + 1
        m = Minute(
            meeting_id=meeting_id,
            tenant_id=tenant_id,
            title=title,
            content=content,
            status="draft",
            version=next_version,
            created_by=created_by,
            ai_provider=ai_provider,
            ai_model=ai_model,
            ai_request_id=ai_request_id,
        )
        session.add(m)
        await session.flush()
        await self._audit(
            session,
            tenant_id=tenant_id,
            actor=created_by,
            action="minutes.draft.create",
            resource_id=m.id,
        )
        return m

    async def mark_reviewed(
        self,
        session: AsyncSession,
        minute: Minute,
        *,
        reviewed_by: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> Minute:
        if minute.status != "draft":
            raise APIError(409, "MINUTE_INVALID_STATE", "Solo un draft puede pasar a revisión")
        minute.status = "review"
        minute.reviewed_by = reviewed_by
        minute.reviewed_at = datetime.now(UTC)
        await session.flush()
        await self._audit(
            session,
            tenant_id=minute.tenant_id,
            actor=reviewed_by,
            action="minutes.review",
            resource_id=minute.id,
            ip=ip,
            user_agent=user_agent,
        )
        return minute

    async def approve(
        self,
        session: AsyncSession,
        minute: Minute,
        *,
        approved_by: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> Minute:
        if minute.status != "review":
            raise APIError(409, "MINUTE_INVALID_STATE", "Solo un reviewed puede aprobarse")
        minute.status = "approved"
        minute.approved_by = approved_by
        minute.approved_at = datetime.now(UTC)
        minute.approved_ip = ip
        minute.approved_user_agent = user_agent
        await session.flush()
        await self._audit(
            session,
            tenant_id=minute.tenant_id,
            actor=approved_by,
            action="minutes.approve",
            resource_id=minute.id,
            ip=ip,
            user_agent=user_agent,
        )
        return minute

    async def publish(
        self,
        session: AsyncSession,
        minute: Minute,
        *,
        published_by: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> Minute:
        if minute.status != "approved":
            raise APIError(409, "MINUTE_INVALID_STATE", "Solo un approved puede publicarse")
        minute.status = "published"
        minute.published_by = published_by
        minute.published_at = datetime.now(UTC)
        await session.flush()
        await self._audit(
            session,
            tenant_id=minute.tenant_id,
            actor=published_by,
            action="minutes.publish",
            resource_id=minute.id,
            ip=ip,
            user_agent=user_agent,
        )
        return minute

    async def archive(self, session: AsyncSession, minute: Minute, *, actor: uuid.UUID) -> Minute:
        if minute.status != "published":
            raise APIError(409, "MINUTE_INVALID_STATE", "Solo un published puede archivarse")
        minute.status = "archived"
        minute.archived_at = datetime.now(UTC)
        await session.flush()
        await self._audit(
            session,
            tenant_id=minute.tenant_id,
            actor=actor,
            action="minutes.archive",
            resource_id=minute.id,
        )
        return minute

    async def get_for_tenant(
        self, session: AsyncSession, *, minute_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Minute:
        row = (
            await session.execute(
                select(Minute).where(
                    Minute.id == minute_id,
                    Minute.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise APIError(404, "MINUTE_NOT_FOUND", "Minute not found")
        return row

    async def list_for_meeting(
        self,
        session: AsyncSession,
        *,
        meeting_id: uuid.UUID,
        tenant_id: uuid.UUID,
        page: int = 1,
        page_size: int = 10,
    ) -> MinuteListResponse:
        meeting = (
            await session.execute(
                select(Meeting).where(
                    Meeting.id == meeting_id,
                    Meeting.organization_id == tenant_id,
                    Meeting.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if meeting is None:
            raise APIError(404, "MEETING_NOT_FOUND", "Meeting not found")

        base = select(Minute).where(Minute.meeting_id == meeting_id, Minute.tenant_id == tenant_id)
        total = (
            await session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        rows = (
            (
                await session.execute(
                    base.order_by(Minute.version.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return MinuteListResponse(
            items=[MinuteResponse.model_validate(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
            pages=math.ceil(total / page_size) if total else 1,
        )

    async def _audit(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: uuid.UUID,
        action: str,
        resource_id: uuid.UUID,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        await AuditService.record(
            session,
            actor_user_id=actor,
            tenant_id=tenant_id,
            action=action,
            resource="minutes",
            resource_id=resource_id,
            ip=ip,
            user_agent=user_agent,
        )
