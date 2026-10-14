"""Provider IA real (OpenAI-compatible)."""

from __future__ import annotations

import httpx
import pytest

from app.modules.minutes.providers import OpenAICompatibleProvider


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://test")


async def test_summarize_returns_content():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(200, json={"choices": [{"message": {"content": "Resumen generado"}}]})

    p = OpenAICompatibleProvider(
        api_key="test-key",
        model="nvidia/nemotron-3-ultra-550b-a55b",
        base_url="https://test",
        client=_client(handler),
    )
    out = await p.summarize(transcript="Se acordó votar el presupuesto.", meeting_title="Junta")
    assert "Resumen generado" == out
    assert p.model_name


async def test_summarize_empty_transcript_raises():
    p = OpenAICompatibleProvider(
        api_key="k",
        model="m",
        base_url="https://test",
        client=_client(lambda r: httpx.Response(500)),
    )
    with pytest.raises(ValueError, match="empty"):
        await p.summarize(transcript="   ", meeting_title="Junta")


async def test_summarize_http_5xx_raises():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    p = OpenAICompatibleProvider(
        api_key="k", model="m", base_url="https://test", client=_client(handler)
    )
    with pytest.raises(RuntimeError, match="AI provider"):
        await p.summarize(transcript="texto suficiente", meeting_title="Junta")


async def test_summarize_timeout_raises():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout!", request=request)

    p = OpenAICompatibleProvider(
        api_key="k",
        model="m",
        base_url="https://test",
        client=_client(handler),
        timeout_seconds=1,
    )
    with pytest.raises(RuntimeError, match="AI provider"):
        await p.summarize(transcript="texto suficiente", meeting_title="Junta")
