"""Worker implementations for async job processing (Phase 3)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.modules.ai.service import AIService
from app.modules.recordings.models import Job
from app.modules.transcription import FasterWhisperProvider, SpeechToTextProvider
from app.modules.transcription.service import TranscriptionService


class TranscriptionWorker:
    """Worker that processes audio transcription jobs using faster-whisper."""

    def __init__(
        self,
        provider: SpeechToTextProvider | None = None,
        storage: Any | None = None,
    ) -> None:
        self._provider = provider or FasterWhisperProvider()
        self._storage = storage
        self._transcription_service = TranscriptionService()

    async def process(self, session: AsyncSession, job: Job) -> dict[str, Any]:
        """Process a transcription job."""
        payload = job.payload
        recording_id = payload.get("recording_id")
        meeting_id = payload.get("meeting_id")
        language = payload.get("language", "es")

        # Fetch recording
        from app.modules.recordings.models import Recording

        recording = (
            await session.execute(select(Recording).where(Recording.id == uuid.UUID(recording_id)))
        ).scalar_one_or_none()
        if not recording:
            raise APIError(404, "RECORDING_NOT_FOUND", f"Recording {recording_id} not found")

        # Download file from storage
        await self._download_recording(recording.storage_path)

        # Create transcription draft
        from app.modules.transcription.service import TranscriptionService

        service = TranscriptionService()
        result = await self._provider.transcribe(recording.storage_path, language=language)
        transcript = await service.create_draft(
            session,
            recording=recording,
            result=result,
            job_id=job.id,
            model_used=type(self._provider).__name__,
        )

        return {
            "transcription_id": str(transcript.id),
            "meeting_id": str(meeting_id) if meeting_id else None,
            "status": "completed",
        }

    async def _download_recording(self, storage_path: str):
        # This would download from the storage provider
        # For now, return a mock handle
        import io

        return io.BytesIO(b"mock audio data")


class OCRWorker:
    """Worker that processes document OCR jobs."""

    def __init__(
        self,
        provider: Any | None = None,
        storage: Any | None = None,
    ) -> None:
        self._ocr_provider: Any = provider
        self._storage = None  # Would use DocumentStorageProvider

    async def process(self, session, job: Job) -> dict[str, Any]:
        payload = job.payload
        document_id = payload.get("document_id")

        # Fetch document
        from app.modules.documents.models import Document

        doc = (
            await session.execute(select(Document).where(Document.id == uuid.UUID(document_id)))
        ).scalar_one_or_none()
        if not doc:
            raise APIError(404, "DOCUMENT_NOT_FOUND", f"Document {document_id} not found")

        # Download file
        file_handle = await self._download_document(doc.file_path)

        # Run OCR
        result = await self._ocr_provider.process(file_handle, doc.mime_type)

        # Update document
        doc.ocr_text = result.text
        doc.ocr_confidence = result.confidence
        doc.ocr_status = "completed" if result.confidence > 0.5 else "failed"
        doc.pages = result.pages

        return {
            "document_id": str(doc.id),
            "ocr_status": doc.ocr_status,
            "confidence": result.confidence,
        }

    async def _download_document(self, file_path: str):
        # This would download from the storage provider
        # For now, return a mock handle
        import io

        return io.BytesIO(b"mock document data")


class AIProcessingWorker:
    """Worker that processes AI jobs (summarization, decisions, tasks extraction)."""

    def __init__(self, provider: Any | None = None) -> None:
        self._provider = None  # Would use AIProvider

    async def process(self, session, job: Job) -> dict[str, Any]:
        payload = job.payload
        meeting_id = payload.get("meeting_id")
        transcription_id = payload.get("transcription_id")
        document_ids = payload.get("document_ids", [])

        # Fetch meeting
        from app.modules.meetings.models import Meeting

        meeting = (
            await session.execute(select(Meeting).where(Meeting.id == uuid.UUID(meeting_id)))
        ).scalar_one_or_none()
        if not meeting:
            raise APIError(404, "MEETING_NOT_FOUND", f"Meeting {meeting_id} not found")

        # Fetch transcription
        from app.modules.transcription.models import Transcript

        transcript = (
            await session.execute(
                select(Transcript).where(Transcript.id == uuid.UUID(transcription_id))
            )
        ).scalar_one_or_none()
        if not transcript:
            raise APIError(
                404, "TRANSCRIPTION_NOT_FOUND", f"Transcription {transcription_id} not found"
            )

        # Fetch documents
        from app.modules.documents.models import Document

        docs = []
        if document_ids:
            docs = (
                (
                    await session.execute(
                        select(Document).where(
                            Document.id.in_([uuid.UUID(d) for d in document_ids]),
                            Document.tenant_id == meeting.organization_id,
                        )
                    )
                )
                .scalars()
                .all()
            )

        # Run AI processing
        ai_service = AIService(self._provider)
        result = await ai_service.process_meeting(
            transcript=transcript.text,
            documents=[d.ocr_text for d in docs if d.ocr_text],
            meeting_title=meeting.title,
            meeting_description=meeting.description,
        )

        # Store AI results in meeting metadata or create a separate model
        # For now, return the result
        return {
            "meeting_id": str(meeting_id),
            "summary": result.summary,
            "decisions": result.decisions,
            "tasks": result.tasks,
            "responsibles": result.responsibles,
        }
