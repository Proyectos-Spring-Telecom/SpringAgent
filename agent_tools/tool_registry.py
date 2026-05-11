"""Registro central de herramientas disponibles para el agente."""

from __future__ import annotations

import logging
from typing import Any, Optional

from .base_tool import BaseTool

LOGGER = logging.getLogger("[ToolRegistry]")


class ToolRegistry:
    """Registra, busca y lista herramientas."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registra una herramienta."""
        LOGGER.info("Tool registrada: %s", tool.name)
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Busca una herramienta por nombre."""
        return self._tools.get(name)

    def get_all_definitions(self) -> list[dict[str, Any]]:
        """Retorna todas las tools en formato Ollama."""
        return [tool.to_ollama_tool() for tool in self._tools.values()]

    def list_names(self) -> list[str]:
        """Lista nombres de todas las tools registradas."""
        return list(self._tools.keys())

    async def execute(self, name: str, arguments: dict) -> dict[str, Any]:
        """Ejecuta una tool por nombre con los argumentos dados."""
        tool = self._tools.get(name)
        if not tool:
            LOGGER.warning("Tool no encontrada: %s", name)
            return {"error": f"Herramienta '{name}' no existe"}

        LOGGER.info("Ejecutando tool: %s con args: %s", name, arguments)
        try:
            result = await tool.execute(**arguments)
            LOGGER.info("Tool %s ejecutada exitosamente", name)
            return result
        except Exception as exc:
            LOGGER.exception("Error ejecutando tool %s: %s", name, exc)
            return {"error": f"Error ejecutando '{name}': {str(exc)}"}
