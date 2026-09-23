"""Recording service: tenant-scoped upload/list/get/download/delete (TASK-252/253).

Storage key convention: ``{tenant_id}/{meeting_id}/{recording_id}`` from
providers.make_recording_key (never derived from client input).
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, BinaryIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.modules.audit.service import AuditService
from app.modules.meetings.models import Meeting
from app.modules.recordings.models import Recording
from app.modules.recordings.providers import StorageProvider, make_recording_key
from app.modules.recordings.schemas import RecordingResponse

_UPLOAD_MAX_BYTES = 200 * 1024 * 1024
_ALLOWED_EXTENSIONS = frozenset({".mp3", ".wav", ".m4a", ".ogg"})
_CONTENT_TYPE_FOR_EXT: dict[str, str] = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
}

_CHUNK = 1024 * 1024  # 1 MiB


class RecordingService:
    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    # -- tenant-scoped lookups --------------------------------------------------

    async def _meeting_for_tenant(
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

    async def _get_scoped(
        self, session: AsyncSession, recording_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Recording:
        row = (
            await session.execute(
                select(Recording).where(
                    Recording.id == recording_id,
                    Recording.tenant_id == tenant_id,
                    Recording.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise APIError(404, "RECORDING_NOT_FOUND", "Recording not found")
        return row

    # -- upload ----------------------------------------------------------------

    async def upload(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        meeting_id: uuid.UUID,
        upload: Any,
        uploaded_by: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> dict[str, Any]:
        await self._meeting_for_tenant(session, meeting_id, tenant_id)

        filename = getattr(upload, "filename", None) or "recording"
        if "." not in filename:
            raise APIError(415, "UNSUPPORTED_MEDIA", "Missing file extension")
        ext = "." + filename.rsplit(".", 1)[1].lower()
        if ext not in _ALLOWED_EXTENSIONS:
            raise APIError(415, "UNSUPPORTED_MEDIA", f"File type not supported: {ext}")
        content_type = _CONTENT_TYPE_FOR_EXT[ext]

        chunks: list[bytes] = []
        hasher = hashlib.sha256()
        size = 0
        while chunk := await upload.read(_CHUNK):
            chunks.append(chunk)
            size += len(chunk)
            hasher.update(chunk)
            if size > _UPLOAD_MAX_BYTES:
                raise APIError(413, "PAYLOAD_TOO_LARGE", "File exceeds the 200MB limit")
        sha = hasher.hexdigest()

        existing = (
            await session.execute(
                select(Recording).where(
                    Recording.meeting_id == meeting_id,
                    Recording.sha256 == sha,
                    Recording.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing_response = self._public(existing)
            return {**existing_response.model_dump(), "_status": 200}

        recording_id = uuid.uuid4()
        key = make_recording_key(tenant_id, meeting_id, recording_id)

        async def _chunks_stream():
            for c in chunks:
                yield c

        await self._storage.store(key, _chunks_stream())

        recording = Recording(
            id=recording_id,
            meeting_id=meeting_id,
            tenant_id=tenant_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size,
            sha256=sha,
            storage_path=key,
            status="queued",
            uploaded_by=uploaded_by,
        )
        session.add(recording)
        await session.flush()

        await AuditService.record(
            session,
            actor_user_id=uploaded_by,
            tenant_id=tenant_id,
            action="recording.upload",
            resource="recording",
            resource_id=recording.id,
            ip=ip,
            user_agent=user_agent,
        )
        await session.commit()
        await session.refresh(recording)
        recording_response = self._public(recording)
        return {**recording_response.model_dump(), "_status": 201}

    # -- reads ----------------------------------------------------------------

    async def list_for_meeting(
        self,
        session: AsyncSession,
        meeting_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[RecordingResponse]:
        await self._meeting_for_tenant(session, meeting_id, tenant_id)
        rows = (
            (
                await session.execute(
                    select(Recording)
                    .where(Recording.meeting_id == meeting_id, Recording.deleted_at.is_(None))
                    .order_by(Recording.created_at)
                )
            )
            .scalars()
            .all()
        )
        return [self._public(r) for r in rows]

    async def get(
        self, session: AsyncSession, recording_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> RecordingResponse:
        return self._public(await self._get_scoped(session, recording_id, tenant_id))

    # -- download --------------------------------------------------------------

    async def stream(
        self,
        session: AsyncSession,
        *,
        recording_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> tuple[BinaryIO, str, str]:
        """Return ``(file, content_type, filename)`` or raise 404-style APIError."""
        recording = await self._get_scoped(session, recording_id, tenant_id)
        await AuditService.record(
            session,
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            action="recording.download",
            resource="recording",
            resource_id=recording.id,
            ip=ip,
            user_agent=user_agent,
        )
        await session.commit()
        fh = await self._storage.open_read(recording.storage_path)
        return fh, recording.content_type, recording.filename

    # -- soft delete -------------------------------------------------------------

    async def delete(
        self,
        session: AsyncSession,
        recording_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        recording = await self._get_scoped(session, recording_id, tenant_id)
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        if recording.deleted_at is None:
            recording.deleted_at = now
            await AuditService.record(
                session,
                actor_user_id=actor_user_id,
                tenant_id=tenant_id,
                action="recording.delete",
                resource="recording",
                resource_id=recording.id,
                ip=ip,
                user_agent=user_agent,
            )
            await session.commit()
        # soft delete idempotent — never raise on a second call

    # -- helpers ---------------------------------------------------------------

    def _public(self, r: Recording) -> RecordingResponse:
        return RecordingResponse(
            id=r.id,
            meeting_id=r.meeting_id,
            tenant_id=r.tenant_id,
            filename=r.filename,
            content_type=r.content_type,
            size_bytes=r.size_bytes,
            sha256=r.sha256,
            status=r.status,
            duration_seconds=r.duration_seconds,
            uploaded_by=r.uploaded_by,
            created_at=r.created_at,
        )
