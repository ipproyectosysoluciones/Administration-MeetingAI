"""Meeting participants business logic (meetings-crud).

Participants are children of a meeting; the meeting's organization carries tenancy,
so no extra tenant column exists on the participant row (data-model §meetings).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.modules.audit.service import AuditService
from app.modules.meetings.models import Meeting, MeetingParticipant
from app.modules.meetings.schemas import ParticipantAddRequest
from app.modules.users.models import User


def _public(p: MeetingParticipant) -> dict[str, Any]:
    return {
        "id": p.id,
        "meeting_id": p.meeting_id,
        "user_id": p.user_id,
        "external_email": p.external_email,
        "role": p.role,
        "created_at": p.created_at,
    }


class ParticipantService:
    async def _meeting(
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

    async def list(
        self, session: AsyncSession, meeting_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict[str, Any]:
        await self._meeting(session, meeting_id, tenant_id)
        rows = (
            (
                await session.execute(
                    select(MeetingParticipant)
                    .where(MeetingParticipant.meeting_id == meeting_id)
                    .order_by(MeetingParticipant.created_at)
                )
            )
            .scalars()
            .all()
        )
        return {"items": [_public(p) for p in rows], "total": len(rows)}

    async def add(
        self,
        session: AsyncSession,
        meeting_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: ParticipantAddRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> dict[str, Any]:
        await self._meeting(session, meeting_id, tenant_id)

        if payload.user_id is not None:
            internal = await session.get(User, payload.user_id)
            membership_ok = False
            if internal is not None and internal.deleted_at is None and internal.is_active:
                # same-tenant proof: a user_roles/membership row binding the user to this org
                from app.modules.organizations.models import Membership

                membership_ok = (
                    await session.execute(
                        select(Membership.id).where(
                            Membership.user_id == internal.id,
                            Membership.organization_id == tenant_id,
                        )
                    )
                ).scalar_one_or_none() is not None
            if not membership_ok:
                # do not leak whether the user exists outside the tenant
                raise APIError(404, "PARTICIPANT_USER_NOT_FOUND", "User not found in tenant")
            dup = (
                await session.execute(
                    select(MeetingParticipant).where(
                        MeetingParticipant.meeting_id == meeting_id,
                        MeetingParticipant.user_id == payload.user_id,
                    )
                )
            ).scalar_one_or_none()
            if dup is not None:
                raise APIError(409, "DUPLICATE_PARTICIPANT", "User is already a participant")
        else:
            assert payload.external_email is not None  # schema guarantees one channel
            dup = (
                await session.execute(
                    select(MeetingParticipant).where(
                        MeetingParticipant.meeting_id == meeting_id,
                        MeetingParticipant.external_email == payload.external_email,
                    )
                )
            ).scalar_one_or_none()
            if dup is not None:
                raise APIError(409, "DUPLICATE_PARTICIPANT", "Email is already a participant")

        participant = MeetingParticipant(
            meeting_id=meeting_id,
            user_id=payload.user_id,
            external_email=payload.external_email,
            role=payload.role,
        )
        session.add(participant)
        await session.flush()
        await AuditService.record(
            session,
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            action="meeting.participant.add",
            resource="meeting_participant",
            resource_id=participant.id,
            ip=ip,
            user_agent=user_agent,
        )
        await session.commit()
        await session.refresh(participant)
        return _public(participant)

    async def remove(
        self,
        session: AsyncSession,
        meeting_id: uuid.UUID,
        participant_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        await self._meeting(session, meeting_id, tenant_id)
        participant = (
            await session.execute(
                select(MeetingParticipant).where(
                    MeetingParticipant.id == participant_id,
                    MeetingParticipant.meeting_id == meeting_id,
                )
            )
        ).scalar_one_or_none()
        if participant is None:
            raise APIError(404, "PARTICIPANT_NOT_FOUND", "Participant not found")
        await session.delete(participant)
        await AuditService.record(
            session,
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            action="meeting.participant.remove",
            resource="meeting_participant",
            resource_id=participant_id,
            ip=ip,
            user_agent=user_agent,
        )
        await session.commit()
