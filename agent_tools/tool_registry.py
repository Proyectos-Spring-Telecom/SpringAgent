"""Registro central de herramientas disponibles para el agente."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from .base_tool import BaseTool

LOGGER = logging.getLogger("[ToolRegistry]")


def coerce_tool_arguments(raw: Any) -> dict[str, Any]:
    """Normaliza argumentos de tool_calls (dict o JSON string desde Ollama)."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            parsed: Any = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            LOGGER.warning("Arguments de tool no son JSON válido: %s", text[:200])
            return {}
    return {}


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

    async def execute(self, name: str, arguments: Any) -> dict[str, Any]:
        """Ejecuta una tool por nombre con los argumentos dados."""
        tool = self._tools.get(name)
        if not tool:
            LOGGER.warning("Tool no encontrada: %s", name)
            return {"status": "error", "message": f"Herramienta '{name}' no existe", "data": None}

        args = coerce_tool_arguments(arguments)
        LOGGER.info("Ejecutando tool: %s con args: %s", name, args)
        try:
            result = await tool.execute(**args)
            LOGGER.info("Tool %s ejecutada exitosamente", name)
            return result
        except TypeError as exc:
            LOGGER.warning("Argumentos inválidos para tool %s: %s", name, exc)
            return {"status": "error", "message": f"Argumentos inválidos para '{name}': {exc}", "data": None}
        except Exception as exc:
            LOGGER.exception("Error ejecutando tool %s: %s", name, exc)
            return {"status": "error", "message": f"Error ejecutando '{name}': {exc}", "data": None}
