"""AI Service: meeting processing (summarization, decisions, tasks extraction)."""

from __future__ import annotations

from typing import Optional

from app.modules.ai.providers import AIProvider, AIResult, MockAIProvider, NemotronAIProvider


class AIService:
    def __init__(self, provider: Optional[AIProvider] = None) -> None:
        self._provider = provider or MockAIProvider()

    async def process_meeting(
        self,
        transcript: str,
        documents: list[str] = None,
        meeting_title: str = "",
        meeting_description: str = "",
    ) -> AIResult:
        """Process meeting content and return structured results."""
        return await self._provider.process_meeting(
            transcript=transcript,
            documents=documents or [],
            meeting_title=meeting_title,
            meeting_description=meeting_description,
        )