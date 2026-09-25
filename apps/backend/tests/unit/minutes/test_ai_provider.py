"""MIN-101: AIProvider port + mock provider (unit)."""

from __future__ import annotations

import pytest

from app.modules.minutes.providers import AIProvider, MockProvider


async def test_mock_provider_generates_summary() -> None:
    provider: AIProvider = MockProvider(model_name="mock")
    text = await provider.summarize(transcript="Se acordó votar", meeting_title="Junta ordinaria")
    assert isinstance(text, str)
    assert len(text) > 0


async def test_mock_provider_is_deterministic() -> None:
    provider: AIProvider = MockProvider(model_name="mock")
    a = await provider.summarize(transcript="Se aprobó", meeting_title="Junta")
    b = await provider.summarize(transcript="Se aprobó", meeting_title="Junta")
    assert a == b


async def test_mock_provider_rejects_empty_transcript() -> None:
    provider: AIProvider = MockProvider(model_name="mock")
    with pytest.raises(ValueError, match="empty|required"):
        await provider.summarize(transcript="   ", meeting_title="Ok")
