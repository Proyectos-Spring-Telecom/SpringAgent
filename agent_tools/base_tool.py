"""Clase base abstracta para herramientas del agente."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Toda herramienta del agente debe heredar de esta clase."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre único de la herramienta (ej: getClientSummary)."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción para que Ollama sepa cuándo usar esta herramienta."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """Esquema JSON de parámetros (formato OpenAI function calling)."""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> dict[str, Any]:
        """Ejecuta la herramienta y retorna resultado."""
        ...

    def to_ollama_tool(self) -> dict[str, Any]:
        """Convierte a formato de tool que Ollama espera."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
