"""Jobs module."""

from app.modules.jobs.service import (
    JobService,
    JOB_TYPE_TRANSCRIBE,
    JOB_TYPE_OCR,
    JOB_TYPE_AI_PROCESS,
    JOB_TYPE_PROCESS_RECORDING,
)
from app.modules.jobs.workers import TranscriptionWorker, OCRWorker, AIProcessingWorker
from app.modules.jobs.router import router as jobs_router

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