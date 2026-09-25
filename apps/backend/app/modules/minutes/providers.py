"""AIProvider port + MockProvider (MIN-101).

El dominio ignora SDKs externos; sólo el protocolo.
"""

from __future__ import annotations

from typing import Protocol


class AIProvider(Protocol):
    """Puerto para rellenar el borrador de minuta a partir de una transcripción."""

    async def summarize(self, *, transcript: str, meeting_title: str) -> str:
        ...


class MockProvider:
    """Provider determinístico para tests y dev local."""

    def __init__(self, *, model_name: str = "mock") -> None:
        self.model_name = model_name

    async def summarize(self, *, transcript: str, meeting_title: str) -> str:
        if not transcript or not transcript.strip():
            raise ValueError("transcript is empty or required")
        return f"Resumen ({meeting_title}): {transcript.strip()[:60]}"
