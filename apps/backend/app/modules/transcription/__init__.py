"""Transcription module (meetings-transcription)."""

from app.modules.transcription.provider import (
    PermanentTranscriptionError,
    Segment,
    SpeechToTextProvider,
    TranscriptionResult,
)
from app.modules.transcription.faster_whisper_provider import FasterWhisperProvider
from app.modules.transcription.service import TranscriptionService
from app.modules.transcription.router import router as transcriptions_router

__all__ = [
    "PermanentTranscriptionError",
    "Segment",
    "SpeechToTextProvider",
    "TranscriptionResult",
    "FasterWhisperProvider",
    "TranscriptionService",
    "transcriptions_router",
]