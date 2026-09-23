"""FasterWhisperProvider: SpeechToTextProvider backed by faster-whisper (TASK-301).

The domain never imports faster_whisper; only this adapter does, and lazily,
so test/CI environments work without the heavy dependency installed.
Model/device come from WHISPER_MODEL / WHISPER_DEVICE env vars.
"""

from __future__ import annotations

import asyncio
import math
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.modules.transcription.provider import Segment, SpeechToTextProvider, TranscriptionResult

ModelLoader = Callable[..., Any]


class FasterWhisperProvider(SpeechToTextProvider):
    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        model_loader: ModelLoader | None = None,
    ) -> None:
        self.model_name = model_name or os.environ.get("WHISPER_MODEL", "small")
        self.device = device or os.environ.get("WHISPER_DEVICE", "auto")
        self._model_loader = model_loader
        self._model: Any | None = None

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        if self._model_loader is not None:
            self._model = self._model_loader(self.model_name, device=self.device)
            return self._model
        try:
            from faster_whisper import (  # type: ignore[import-not-found]  # noqa: PLC0415
                WhisperModel,
            )
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is not installed; install it (pip install faster-whisper) "
                "or inject a model_loader compatible with WhisperModel"
            ) from exc
        self._model = WhisperModel(self.model_name, device=self.device)
        return self._model

    async def transcribe(
        self, audio_path: str | Path, language: str | None = None
    ) -> TranscriptionResult:
        path = Path(audio_path)
        if not path.is_file():
            raise ValueError(f"audio file not found: {path}")
        return await asyncio.to_thread(self._transcribe_sync, path, language)

    def _transcribe_sync(self, path: Path, language: str | None) -> TranscriptionResult:
        model = self._load_model()
        segments_iter, info = model.transcribe(str(path), language=language)

        segments: list[Segment] = []
        logprobs: list[float] = []
        for s in segments_iter:
            segments.append(
                Segment(start=float(s.start), end=float(s.end), text=s.text.strip(), speaker=None)
            )
            lp = getattr(s, "avg_logprob", None)
            if lp is not None:
                logprobs.append(float(lp))

        # faster-whisper segment text usually starts with a space; join stripped parts.
        text = " ".join(s.text for s in segments).strip()
        avg_confidence = sum(math.exp(lp) for lp in logprobs) / len(logprobs) if logprobs else None
        detected_language = getattr(info, "language", None) if info is not None else None

        return TranscriptionResult(
            text=text,
            segments=segments,
            avg_confidence=avg_confidence,
            language=detected_language,
        )
