"""Worker implementations for async job processing (Phase 3)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import async_session_factory
from app.core.security import JWTService, PasswordHasher
from app.modules.jobs.service import JobService
from app.modules.recordings.models import Job
from app.modules.recordings.providers import LocalStorageProvider
from app.modules.recordings.service import RecordingService
from app.modules.transcription import SpeechToTextProvider, FasterWhisperProvider
from app.modules.transcription.service import TranscriptionService
from app.modules.ocr.providers import OCRProvider, TesseractOCRProvider
from app.modules.ocr.service import OCRService
from app.modules.documents.providers import DocumentStorageProvider, LocalStorageProvider
from app.modules.ai.providers import AIProvider, NemotronAIProvider
from app.modules.ai.service import AIService
from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.security import JWTService, PasswordHasher
from app.core.exceptions import APIError


class TranscriptionWorker:
    """Worker that processes audio transcription jobs using faster-whisper."""

    def __init__(
        self,
        provider: Optional[SpeechToTextProvider] = None,
        storage: Optional[Any] = None,
    ) -> None:
        self._provider = provider or FasterWhisperProvider()
        self._storage = storage
        self._transcription_service = TranscriptionService(provider=self._provider)

    async def process(self, session: AsyncSession, job: Job) -> dict[str, Any]:
        """Process a transcription job."""
        payload = job.payload
        recording_id = payload.get("recording_id")
        meeting_id = payload.get("meeting_id")
        language = payload.get("language", "es")
        diarize = payload.get("diarize", True)

        # Fetch recording
        from app.modules.recordings.models import Recording
        recording = (await session.execute(
            select(Recording).where(Recording.id == uuid.UUID(recording_id))
        )).scalar_one_or_none()
        if not recording:
            raise APIError(404, "RECORDING_NOT_FOUND", f"Recording {recording_id} not found")

        # Download file from storage
        file_handle = await self._download_recording(recording.storage_path)

        # Create transcription draft
        from app.modules.transcription.service import TranscriptionService
        service = TranscriptionService(self._provider)
        transcript = await service.create_draft(
            session,
            recording_id=recording.id,
            tenant_id=recording.tenant_id,
            language=language,
            diarize=diarize,
            audio_handle=file_handle,
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
        provider: Optional[Any] = None,
        storage: Optional[Any] = None,
    ) -> None:
        self._provider = provider
        self._storage = None  # Would use DocumentStorageProvider

    async def process(self, session, job: Job) -> dict[str, Any]:
        payload = job.payload
        document_id = payload.get("document_id")

        # Fetch document
        from app.modules.documents.models import Document
        doc = (await session.execute(
            select(Document).where(Document.id == uuid.UUID(document_id))
        )).scalar_one_or_none()
        if not doc:
            raise APIError(404, "DOCUMENT_NOT_FOUND", f"Document {document_id} not found")

        # Download file
        file_handle = await self._download_document(doc.file_path)

        # Run OCR
        from app.modules.ocr.service import OCRService
        from app.modules.ocr.providers import TesseractOCRProvider
        ocr_service = OCRService()
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


class AIProcessingWorker:
    """Worker that processes AI jobs (summarization, decisions, tasks extraction)."""

    def __init__(self, provider: Optional[Any] = None) -> None:
        self._provider = None  # Would use AIProvider

    async def process(self, session, job: Job) -> dict[str, Any]:
        payload = job.payload
        meeting_id = payload.get("meeting_id")
        transcription_id = payload.get("transcription_id")
        document_ids = payload.get("document_ids", [])

        # Fetch meeting
        from app.modules.meetings.models import Meeting
        meeting = (await session.execute(
            select(Meeting).where(Meeting.id == uuid.UUID(meeting_id))
        )).scalar_one_or_none()
        if not meeting:
            raise APIError(404, "MEETING_NOT_FOUND", f"Meeting {meeting_id} not found")

        # Fetch transcription
        from app.modules.transcription.models import Transcription
        transcript = (await session.execute(
            select(Transcription).where(Transcription.id == uuid.UUID(transcription_id))
        )).scalar_one_or_none()
        if not transcript:
            raise APIError(404, "TRANSCRIPTION_NOT_FOUND", f"Transcription {transcription_id} not found")

        # Fetch documents
        from app.modules.documents.models import Document
        docs = []
        if document_ids:
            docs = (await session.execute(
                select(Document).where(
                    Document.id.in_([uuid.UUID(d) for d in document_ids]),
                    Document.tenant_id == meeting.organization_id,
                )
            )).scalars().all()

        # Run AI processing
        from app.modules.ai.service import AIService
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
            "summary": result.get("summary"),
            "decisions": result.get("decisions", []),
            "tasks": result.get("tasks", []),
            "responsibles": result.get("responsibles", []),
        }