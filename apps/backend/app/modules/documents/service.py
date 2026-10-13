"""Documents service: CRUD, versioning, upload, OCR integration."""

from __future__ import annotations

import hashlib
import mimetypes
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import BinaryIO

from fastapi import UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.exceptions import APIError
from app.modules.audit.models import AuditEvent
from app.modules.documents.models import Document, DocumentStatus, DocumentType, DocumentVersion, OcrStatus
from app.modules.documents.providers import DocumentStorageProvider, LocalStorageProvider
from app.modules.ocr.providers import OCRProvider, TesseractOCRProvider
from app.modules.ocr.service import OCRService


@dataclass
class DocumentUploadResult:
    id: uuid.UUID
    tenant_id: uuid.UUID
    meeting_id: uuid.UUID | None
    title: str
    description: str | None
    type: str
    status: str
    file_path: str
    file_size: int
    sha256: str
    mime_type: str
    version: int
    ocr_text: str | None
    ocr_confidence: float | None
    ocr_status: str
    ocr_error: str | None
    pages: int | None
    uploaded_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    _status: int = 201


class DocumentService:
    def __init__(
        self,
        storage: DocumentStorageProvider | None = None,
        ocr_provider: OCRProvider | None = None,
    ) -> None:
        self._storage = storage or LocalStorageProvider()
        self._ocr_provider = ocr_provider or TesseractOCRProvider()
        self._ocr_service = OCRService(self._ocr_provider)

    # -- create ---------------------------------------------------------------

    async def create(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        payload,
        ip: str | None,
        user_agent: str | None,
    ) -> DocumentUploadResult:
        """Create a document record (without file upload)."""
        doc = Document(
            tenant_id=tenant_id,
            meeting_id=payload.meeting_id,
            title=payload.title,
            description=payload.description,
            type=payload.type,
            status=DocumentStatus.PENDING,
            file_path="",
            file_size=0,
            sha256="",
            mime_type="",
            version=1,
            ocr_status=OcrStatus.PENDING,
            uploaded_by=payload.meeting_id is not None and user_id,  # simplified
        )
        session.add(doc)
        await session.flush()

        self._record_audit(
            session, user_id, tenant_id, "document.create", "document", doc.id
        )
        await session.commit()

        return DocumentUploadResult(
            id=doc.id,
            tenant_id=doc.tenant_id,
            meeting_id=doc.meeting_id,
            title=doc.title,
            description=doc.description,
            type=doc.type.value,
            status=doc.status.value,
            file_path=doc.file_path,
            file_size=doc.file_size,
            sha256=doc.sha256,
            mime_type=doc.mime_type,
            version=doc.version,
            ocr_text=doc.ocr_text,
            ocr_confidence=doc.ocr_confidence,
            ocr_status=doc.ocr_status.value,
            ocr_error=doc.ocr_error,
            pages=doc.pages,
            uploaded_by=doc.uploaded_by,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    # -- list -----------------------------------------------------------------

    async def list(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        page: int,
        page_size: int,
        status: str | None,
        doc_type: str | None,
        search: str | None,
    ) -> tuple[list, int]:
        stmt = select(Document).where(
            Document.tenant_id == tenant_id,
            Document.deleted_at.is_(None),
        )
        if status:
            stmt = stmt.where(Document.status == status)
        if doc_type:
            stmt = stmt.where(Document.type == doc_type)
        if search:
            stmt = stmt.where(Document.title.ilike(f"%{search}%"))

        total_stmt = select(Document).where(
            Document.tenant_id == tenant_id,
            Document.deleted_at.is_(None),
        )
        if status:
            total_stmt = total_stmt.where(Document.status == status)
        if doc_type:
            total_stmt = total_stmt.where(Document.type == doc_type)
        if search:
            total_stmt = total_stmt.where(Document.title.ilike(f"%{search}%"))

        total = len((await session.execute(total_stmt)).scalars().all())
        stmt = stmt.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await session.execute(stmt)).scalars().all()
        return items, total

    # -- get ------------------------------------------------------------------

    async def get(self, session: AsyncSession, document_id: uuid.UUID, tenant_id: uuid.UUID):
        stmt = select(Document).where(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
            Document.deleted_at.is_(None),
        )
        doc = (await session.execute(stmt)).scalar_one_or_none()
        if doc is None:
            raise APIError(404, "DOCUMENT_NOT_FOUND", "Document not found")
        return doc

    # -- update ---------------------------------------------------------------

    async def update(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        payload,
        ip: str | None,
        user_agent: str | None,
    ):
        doc = await self.get(session, document_id, tenant_id)
        if payload.title is not None:
            doc.title = payload.title
        if payload.description is not None:
            doc.description = payload.description
        if payload.meeting_id is not None:
            doc.meeting_id = payload.meeting_id
        doc.updated_at = datetime.now(UTC)
        session.add(doc)
        self._record_audit(session, user_id, tenant_id, "document.update", "document", doc.id)
        await session.commit()
        return doc

    # -- soft delete ----------------------------------------------------------

    async def soft_delete(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        doc = await self.get(session, document_id, tenant_id)
        doc.deleted_at = datetime.now(UTC)
        session.add(doc)
        self._record_audit(session, user_id, tenant_id, "document.delete", "document", doc.id)
        await session.commit()

    # -- versioning -----------------------------------------------------------

    async def create_version(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        payload,
        ip: str | None,
        user_agent: str | None,
    ):
        doc = await self.get(session, document_id, tenant_id)

        # Verify version matches
        expected_version = doc.version + 1
        if payload.version != expected_version:
            raise APIError(409, "VERSION_CONFLICT", f"Expected version {expected_version}, got {payload.version}")

        # Store current state as version
        version = DocumentVersion(
            document_id=document_id,
            version=doc.version,
            file_path=doc.file_path,
            file_size=doc.file_size,
            sha256=doc.sha256,
            ocr_text=doc.ocr_text,
            ocr_confidence=doc.ocr_confidence,
            ocr_status=doc.ocr_status,
            pages=doc.pages,
            metadata_json={},
            created_by=user_id,
        )
        session.add(version)

        # Update document with new version
        doc.version = expected_version
        doc.file_path = payload.file_path
        doc.file_size = payload.file_size
        doc.sha256 = payload.sha256
        doc.ocr_text = payload.ocr_text
        doc.ocr_confidence = payload.ocr_confidence
        doc.ocr_status = OcrStatus(payload.ocr_status) if payload.ocr_status else OcrStatus.PENDING
        doc.pages = payload.pages
        doc.updated_at = datetime.now(UTC)
        session.add(doc)

        self._record_audit(session, user_id, tenant_id, "document.version.create", "document", document_id)
        await session.commit()

        return DocumentVersionResponse(
            id=version.id,
            document_id=version.document_id,
            version=version.version,
            file_path=version.file_path,
            file_size=version.file_size,
            sha256=version.sha256,
            ocr_text=version.ocr_text,
            ocr_confidence=version.ocr_confidence,
            ocr_status=version.ocr_status.value,
            pages=version.pages,
            metadata_json=version.metadata_json,
            created_by=version.created_by,
            created_at=version.created_at,
        )

    async def list_versions(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> tuple[list, int]:
        doc = await self.get(session, document_id, tenant_id)
        stmt = select(DocumentVersion).where(DocumentVersion.document_id == document_id)
        total_stmt = select(DocumentVersion).where(DocumentVersion.document_id == document_id)
        total = len((await session.execute(total_stmt)).scalars().all())
        stmt = stmt.order_by(DocumentVersion.version.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await session.execute(stmt)).scalars().all()
        return items, total

    # -- upload ---------------------------------------------------------------

    async def upload(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        upload: UploadFile,
        title: str,
        doc_type: str,
        meeting_id: uuid.UUID | None,
        description: str | None,
        ip: str | None,
        user_agent: str | None,
    ) -> DocumentUploadResult:
        # Validate file type
        try:
            doc_type = DocumentType(doc_type.lower())
        except ValueError:
            raise APIError(400, "INVALID_DOCUMENT_TYPE", f"Unsupported type: {doc_type}")

        # Read file and compute SHA256
        content = await upload.read()
        sha256_hash = hashlib.sha256(content).hexdigest()
        file_size = len(content)
        mime_type = upload.content_type or mimetypes.guess_type(upload.filename or "")[0] or "application/octet-stream"

        # Check for duplicate
        existing = (
            await session.execute(
                select(Document).where(
                    Document.tenant_id == tenant_id,
                    Document.sha256 == sha256_hash,
                    Document.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise APIError(409, "DUPLICATE_DOCUMENT", "Document with same content already exists")

        # Store file
        file_path = await self._storage.store(tenant_id, sha256_hash, content)

        # Create document
        doc = Document(
            tenant_id=tenant_id,
            meeting_id=meeting_id,
            title=title,
            description=description,
            type=doc_type,
            status=DocumentStatus.COMPLETED,
            file_path=file_path,
            file_size=file_size,
            sha256=sha256_hash,
            mime_type=mime_type,
            version=1,
            ocr_status=OcrStatus.PENDING,
            uploaded_by=user_id,
        )
        session.add(doc)
        await session.flush()

        # Create initial version
        version = DocumentVersion(
            document_id=doc.id,
            version=1,
            file_path=file_path,
            file_size=file_size,
            sha256=sha256_hash,
            ocr_status=OcrStatus.PENDING,
            metadata_json={},
            created_by=user_id,
        )
        session.add(version)

        self._record_audit(
            session, user_id, tenant_id, "document.upload", "document", doc.id
        )
        await session.commit()

        return DocumentUploadResult(
            id=doc.id,
            tenant_id=doc.tenant_id,
            meeting_id=doc.meeting_id,
            title=doc.title,
            description=doc.description,
            type=doc.type.value,
            status=doc.status.value,
            file_path=doc.file_path,
            file_size=doc.file_size,
            sha256=doc.sha256,
            mime_type=doc.mime_type,
            version=doc.version,
            ocr_text=doc.ocr_text,
            ocr_confidence=doc.ocr_confidence,
            ocr_status=doc.ocr_status.value,
            ocr_error=doc.ocr_error,
            pages=doc.pages,
            uploaded_by=doc.uploaded_by,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    # -- download -------------------------------------------------------------

    async def stream(
        self,
        session: AsyncSession,
        document_id: uuid.UUID,
        tenant_id: uuid.UUID,
        version: int | None,
        actor_user_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> tuple[BinaryIO, str, str]:
        if version:
            stmt = select(DocumentVersion).where(
                DocumentVersion.document_id == document_id,
                DocumentVersion.version == version,
            )
            ver = (await session.execute(stmt)).scalar_one_or_none()
            if ver is None:
                raise APIError(404, "VERSION_NOT_FOUND", "Version not found")
            file_path = ver.file_path
            filename = f"doc_v{ver.version}_{uuid.uuid4().hex[:8]}"
        else:
            doc = await self.get(session, document_id, tenant_id)
            file_path = doc.file_path
            filename = f"{doc.title}_{doc.id}"

        file_handle = await self._storage.retrieve(file_path)
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

        self._record_audit(
            session,
            actor_user_id,
            tenant_id,
            "document.download",
            "document",
            document_id,
            ip,
            user_agent,
        )
        return file_handle, content_type, filename

    # -- OCR ------------------------------------------------------------------

    async def trigger_ocr(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ):
        doc = await self.get(session, document_id, tenant_id)
        if doc.ocr_status == OcrStatus.PROCESSING:
            raise APIError(409, "OCR_IN_PROGRESS", "OCR already in progress")

        doc.ocr_status = OcrStatus.PROCESSING
        doc.ocr_error = None
        session.add(doc)
        await session.commit()

        # Run OCR asynchronously (in background)
        # For now, run synchronously
        try:
            file_handle = await self._storage.retrieve(doc.file_path)
            result = await self._ocr_service.process(file_handle, doc.mime_type)
            file_handle.close()

            doc.ocr_text = result.text
            doc.ocr_confidence = result.confidence
            doc.ocr_status = OcrStatus.COMPLETED if result.confidence > 0.5 else OcrStatus.FAILED
            doc.pages = result.pages
            doc.updated_at = datetime.now(UTC)
        except Exception as e:
            doc.ocr_status = OcrStatus.FAILED
            doc.ocr_error = str(e)
            doc.updated_at = datetime.now(UTC)

        session.add(doc)
        self._record_audit(
            session, user_id, tenant_id, "document.ocr", "document", document_id
        )
        await session.commit()

        return await self.get(session, document_id, tenant_id)

    # -- audit ----------------------------------------------------------------

    def _record_audit(
        self,
        session: AsyncSession,
        actor_user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        action: str,
        resource: str,
        resource_id: uuid.UUID | None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        session.add(
            AuditEvent(
                actor_user_id=actor_user_id,
                tenant_id=tenant_id,
                action=action,
                resource=resource,
                resource_id=resource_id,
                ip=ip,
                user_agent=user_agent,
                metadata_json={},
            )
        )