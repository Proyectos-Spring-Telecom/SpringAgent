"""Cliente async para la API de Ollama."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from config import settings

LOGGER = logging.getLogger("[OllamaClient]")


class OllamaClient:
    """Comunicación con Ollama vía HTTP (POST /api/chat)."""

    def __init__(self) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._timeout = settings.ollama_timeout
        self._num_ctx = settings.ollama_num_ctx

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Envía mensajes a Ollama y retorna la respuesta completa."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": stream,
            "options": {
                "num_ctx": self._num_ctx,
            },
        }
        if tools:
            payload["tools"] = tools

        url = f"{self._base_url}/api/chat"
        LOGGER.info(
            "POST %s model=%s messages=%d tools=%d",
            url,
            self._model,
            len(messages),
            len(tools or []),
        )

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        msg = data.get("message", {})
        LOGGER.info(
            "Ollama respondió: role=%s tool_calls=%s",
            msg.get("role"),
            bool(msg.get("tool_calls")),
        )
        return data

    async def is_healthy(self) -> bool:
        """Verifica que Ollama esté respondiendo."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except Exception as exc:
            LOGGER.warning("Ollama health check falló: %s", exc)
            return False
