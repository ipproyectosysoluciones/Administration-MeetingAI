"""TASK-301: FasterWhisperProvider — adapter test with mocked faster-whisper boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.transcription.faster_whisper_provider import FasterWhisperProvider


class _FakeSegment:
    def __init__(self, start: float, end: float, text: str, avg_logprob: float) -> None:
        self.start = start
        self.end = end
        self.text = text
        self.avg_logprob = avg_logprob


class _FakeInfo:
    def __init__(self, language: str, language_probability: float) -> None:
        self.language = language
        self.language_probability = language_probability


class _FakeModel:
    def __init__(self, segments, info) -> None:
        self._segments = segments
        self._info = info
        self.calls: list[dict] = []

    def transcribe(self, audio: str, language: str | None = None):
        self.calls.append({"audio": audio, "language": language})
        return iter(self._segments), self._info


@pytest.fixture()
def fake_loader():
    """Return a provider whose model factory is a fake WhisperModel."""

    segments = [
        _FakeSegment(0.0, 1.5, " Hola", -0.1),
        _FakeSegment(1.5, 3.0, " mundo", -0.3),
    ]
    info = _FakeInfo(language="es", language_probability=0.9)
    model = _FakeModel(segments, info)
    return FasterWhisperProvider(model_loader=lambda *_a, **_kw: model), model


@pytest.mark.asyncio
async def test_transcribe_aggregates_text_and_segments(fake_loader, tmp_path: Path) -> None:
    provider, model = fake_loader
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"RIFF")

    result = await provider.transcribe(audio, language="es")

    assert result.text == "Hola mundo"
    assert [(s.start, s.end, s.text, s.speaker) for s in result.segments] == [
        (0.0, 1.5, "Hola", None),
        (1.5, 3.0, "mundo", None),
    ]
    assert model.calls == [{"audio": str(audio), "language": "es"}]


@pytest.mark.asyncio
async def test_avg_confidence_from_segment_logprobs(fake_loader, tmp_path: Path) -> None:
    provider, _ = fake_loader
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"RIFF")

    result = await provider.transcribe(audio)

    import math

    expected = (math.exp(-0.1) + math.exp(-0.3)) / 2
    assert result.avg_confidence == pytest.approx(expected, rel=1e-6)


@pytest.mark.asyncio
async def test_empty_segments_yield_zero_confidence(tmp_path: Path) -> None:
    model = _FakeModel([], _FakeInfo("es", 0.9))
    provider = FasterWhisperProvider(model_loader=lambda *_a, **_kw: model)
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"RIFF")

    result = await provider.transcribe(audio)

    assert result.text == ""
    assert result.segments == []
    assert result.avg_confidence is None


@pytest.mark.asyncio
async def test_missing_audio_raises_value_error(fake_loader, tmp_path: Path) -> None:
    provider, _ = fake_loader
    with pytest.raises(ValueError, match="not found"):
        await provider.transcribe(tmp_path / "nope.wav")


def test_env_defaults_for_model_and_device(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WHISPER_MODEL", raising=False)
    monkeypatch.delenv("WHISPER_DEVICE", raising=False)
    provider = FasterWhisperProvider()
    assert provider.model_name == "small"
    assert provider.device == "auto"

    monkeypatch.setenv("WHISPER_MODEL", "medium")
    monkeypatch.setenv("WHISPER_DEVICE", "cuda")
    provider = FasterWhisperProvider()
    assert provider.model_name == "medium"
    assert provider.device == "cuda"


@pytest.mark.asyncio
async def test_default_loader_surfaces_importerror(tmp_path: Path, monkeypatch) -> None:
    """Without faster-whisper installed (CI), transcribe raises a clear error."""

    provider = FasterWhisperProvider()
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"RIFF")

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "faster_whisper":
            raise ImportError("No module named 'faster_whisper'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(RuntimeError, match="faster-whisper is not installed"):
        await provider.transcribe(audio)
