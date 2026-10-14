"""AIProvider port + MockProvider (MIN-101).

El dominio ignora SDKs externos; sólo el protocolo.
"""

from __future__ import annotations

from typing import Protocol

import httpx


class AIProvider(Protocol):
    """Puerto para rellenar el borrador de minuta a partir de una transcripción."""

    async def summarize(self, *, transcript: str, meeting_title: str) -> str: ...


class MockProvider:
    """Provider determinístico para tests y dev local."""

    def __init__(self, *, model_name: str = "mock") -> None:
        self.model_name = model_name

    async def summarize(self, *, transcript: str, meeting_title: str) -> str:
        if not transcript or not transcript.strip():
            raise ValueError("transcript is empty or required")
        return f"Resumen ({meeting_title}): {transcript.strip()[:60]}"


class OpenAICompatibleProvider:
    """Provider real vía chat completions OpenAI-compatible (NVIDIA NIM, OpenAI, Ollama HTTP, …).

    Config por Settings (`AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL`, `AI_TIMEOUT_SECONDS`).
    Un timeout o error HTTP del servicio IA se superficia como RuntimeError (fail-closed).
    """

    _SYSTEM = (
        "Sos un redactor de actas. Devolvé SOLO el texto del borrador del acta "
        "con secciones: Resumen, Decisiones, Tareas. Sin comentarios ni markdown extra."
    )

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        timeout_seconds: int = 60,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self.model_name = model
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout_seconds, connect=5.0),
        )

    async def summarize(self, *, transcript: str, meeting_title: str) -> str:
        if not transcript or not transcript.strip():
            raise ValueError("transcript is empty or required")

        user = f"Reunión: {meeting_title}\n\nTranscripción:\n{transcript[:14000]}"
        try:
            r = await self._client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": self._SYSTEM},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": 1024,
                    "temperature": 0.2,
                },
            )
        except (httpx.TransportError, httpx.TimeoutException) as e:
            raise RuntimeError(f"AI provider unreachable: {e}") from e

        if r.status_code != 200:
            raise RuntimeError(f"AI provider error {r.status_code}: {r.text[:500]}")
        return r.json()["choices"][0]["message"]["content"]
