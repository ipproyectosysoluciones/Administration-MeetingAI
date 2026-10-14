"""Jobs module."""

from app.modules.jobs.router import router as jobs_router
from app.modules.jobs.service import (
    JOB_TYPE_AI_PROCESS,
    JOB_TYPE_OCR,
    JOB_TYPE_PROCESS_RECORDING,
    JOB_TYPE_TRANSCRIBE,
    JobService,
)
from app.modules.jobs.workers import AIProcessingWorker, OCRWorker, TranscriptionWorker

__all__ = [
    "JobService",
    "JOB_TYPE_TRANSCRIBE",
    "JOB_TYPE_OCR",
    "JOB_TYPE_AI_PROCESS",
    "JOB_TYPE_PROCESS_RECORDING",
    "TranscriptionWorker",
    "OCRWorker",
    "AIProcessingWorker",
    "jobs_router",
]
