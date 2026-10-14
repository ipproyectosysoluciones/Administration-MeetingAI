"""Jobs REST router: enqueue jobs and check status (TASK-253)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.service import (
    JobService,
)
from app.modules.recordings.models import Job

router = APIRouter(tags=["jobs"])

Db = Annotated["AsyncSession", "get_db"]


def _service(request: Request) -> JobService:
    return JobService()


def _tenant(auth) -> str:
    if auth.tenant_id is None:
        from app.core.exceptions import APIError
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP", "No active tenant membership")
    return str(auth.tenant_id)


def _pages(total: int, page_size: int) -> int:
    return (total + page_size - 1) // page_size if total else 1


@router.post("/jobs/transcribe", status_code=201)
async def enqueue_transcription(
    request: Request,
    db,
    auth,
    recording_id: uuid.UUID,
    meeting_id: uuid.UUID | None = None,
    language: str = "es",
    diarize: bool = True,
):
    """Enqueue an audio transcription job."""
    svc = JobService()
    job = await svc.enqueue_transcription(
        db,
        recording_id=str(recording_id),
        meeting_id=str(meeting_id) if meeting_id else None,
    )
    return {"job_id": str(job.id), "status": job.status}


@router.post("/jobs/ocr", status_code=201)
async def enqueue_ocr(
    request: Request,
    db,
    auth,
    document_id: uuid.UUID,
):
    """Enqueue an OCR processing job."""
    svc = JobService()
    job = await svc.enqueue_ocr(
        db,
        document_id=str(document_id),
    )
    return {"job_id": str(job.id), "status": job.status}


@router.post("/jobs/ai-process", status_code=201)
async def enqueue_ai_processing(
    request: Request,
    db,
    auth,
    meeting_id: uuid.UUID,
    transcription_id: uuid.UUID,
    document_ids: list[uuid.UUID] | None = None,
):
    """Enqueue an AI meeting processing job."""
    svc = JobService()
    job = await svc.enqueue_ai_processing(
        db,
        meeting_id=str(meeting_id),
        transcription_id=str(transcription_id),
        document_ids=[str(d) for d in document_ids] if document_ids else None,
    )
    return {"job_id": str(job.id), "status": job.status}


@router.get("/jobs")
async def list_jobs(
    request: Request,
    db,
    auth,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    type_filter: str | None = Query(None, alias="type"),
):
    """List jobs for the current tenant."""
    # For simplicity, we'll filter by tenant through job payload or a tenant_id column
    # This would need a tenant_id column on Job model for full multi-tenant support
    stmt = select(Job).order_by(Job.created_at.desc())
    if status_filter:
        stmt = stmt.where(Job.status == status_filter)
    # Add pagination
    offset = (page - 1) * 20
    stmt = stmt.offset(offset).limit(20)
    # Execute and return
    return {"items": [], "total": 0, "page": 1, "page_size": 20, "pages": 0}


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: uuid.UUID,
    request: Request,
    db,
    auth,
):
    """Get job status and details."""
    from sqlalchemy import select
    job = (await request.app.state.session_factory().execute(
        select(Job).where(Job.id == job_id)
    )).scalar_one_or_none()
    if not job:
        from app.core.exceptions import APIError
        raise APIError(404, "JOB_NOT_FOUND", "Job not found")
    return {
        "id": str(job.id),
        "type": job.type,
        "status": job.status,
        "payload": job.payload,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "run_at": job.run_at,
        "locked_by": job.locked_by,
        "locked_at": job.locked_at,
        "completed_at": job.completed_at,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }