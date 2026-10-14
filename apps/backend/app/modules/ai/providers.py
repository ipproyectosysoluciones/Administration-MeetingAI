"""AI Provider abstraction (Phase 3)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AIResult:
    summary: str
    decisions: list[str] = None
    tasks: list[dict] = None
    responsibles: list[str] = None
    key_points: list[str] = None
    action_items: list[dict] = None


class AIProvider(ABC):
    """Abstract AI provider for meeting processing."""

    @abstractmethod
    async def process_meeting(
        self,
        transcript: str,
        documents: list[str] = None,
        meeting_title: str = "",
        meeting_description: str = "",
    ) -> AIResult:
        """Process meeting content and return structured results."""
        ...


class NemotronAIProvider(AIProvider):
    """Nemotron 3 Ultra provider (via NVIDIA API)."""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url or "https://integrate.api.nvidia.com/v1"
        # In production, would initialize OpenAI-compatible client

    async def process_meeting(
        self,
        transcript: str,
        documents: list[str] = None,
        meeting_title: str = "",
        meeting_description: str = "",
    ) -> dict:
        # Mock implementation - in production would call NVIDIA API
        return {
            "summary": f"Resumen de la reunión: {meeting_title}. Se discutieron temas principales y se tomaron decisiones.",
            "decisions": [
                "Decisión 1: Aprobar el presupuesto para el próximo trimestre",
                "Decisión 2: Asignar responsable para el proyecto X",
            ],
            "tasks": [
                {"description": "Preparar reporte financiero", "assignee": "Juan Pérez", "due_date": "2024-01-15"},
                {"description": "Revisar contrato", "assignee": "María García", "due_date": "2024-01-20"},
            ],
            "responsibles": ["Juan Pérez", "María García"],
            "key_points": [
                "Presupuesto aprobado",
                "Nuevo responsable asignado",
            ],
            "action_items": [
                {"action": "Enviar reporte", "owner": "Juan Pérez", "deadline": "2024-01-15"},
            ],
        }


class MockAIProvider(AIProvider):
    """Mock AI provider for testing."""

    async def process_meeting(
        self,
        transcript: str,
        documents: list[str] = None,
        meeting_title: str = "",
        meeting_description: str = "",
    ) -> dict:
        return {
            "summary": f"[MOCK] Resumen de {meeting_title}: {transcript[:100]}...",
            "decisions": ["Decisión simulada 1", "Decisión simulada 2"],
            "tasks": [
                {"description": "Tarea 1", "assignee": "Usuario 1", "due_date": "2024-01-15"},
            ],
            "responsibles": ["Usuario 1", "Usuario 2"],
            "key_points": ["Punto clave 1", "Punto clave 2"],
            "action_items": [
                {"action": "Acción 1", "owner": "Usuario 1", "deadline": "2024-01-15"},
            ],
        }