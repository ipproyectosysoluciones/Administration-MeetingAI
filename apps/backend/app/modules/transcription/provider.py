"""SpeechToTextProvider port + result types (TASK-301).

Domain-neutral port: business logic depends only on this protocol, so STT
vendors (faster-whisper, cloud APIs) can be swapped without touching the
transcription service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class Segment:
    """One transcript segment. `speaker` is reserved for diarization (v2)."""

    start: float
    end: float
    text: str
    speaker: str | None = None


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    segments: list[Segment] = field(default_factory=list)
    avg_confidence: float | None = None
    language: str | None = None


class SpeechToTextProvider(Protocol):
    """Async STT port: implementations must offload blocking work to threads."""

    async def transcribe(
        self, audio_path: str | Path, language: str | None = None
    ) -> TranscriptionResult: ...
