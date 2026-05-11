"""Orquestador principal del agente IA."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from .ollama_client import OllamaClient
from .prompt_templates import SYSTEM_PROMPT_NO_TOOLS

LOGGER = logging.getLogger("[AgentService]")


class AgentService:
    """Fase 1: Chat simple con Ollama sin tool calling.

    En Fase 2 se expande con tool_registry y ciclo de tools.
    """

    def __init__(self) -> None:
        self._ollama = OllamaClient()

    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[int] = None,
        client_id: Optional[int] = None,
    ) -> dict:
        """Procesa un mensaje de usuario y devuelve la respuesta del modelo."""
        start_time = time.perf_counter()
        conv_id = conversation_id or str(uuid.uuid4())

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_NO_TOOLS},
            {"role": "user", "content": message},
        ]

        try:
            response = await self._ollama.chat(messages=messages, tools=None, stream=False)
            assistant_message = response.get("message", {}).get("content", "")
            processing_time_ms = int((time.perf_counter() - start_time) * 1000)

            LOGGER.info(
                "Chat completado conv_id=%s user_id=%s tiempo=%dms",
                conv_id,
                user_id,
                processing_time_ms,
            )

            return {
                "response": assistant_message,
                "conversation_id": conv_id,
                "tools_used": [],
                "processing_time_ms": processing_time_ms,
            }
        except Exception as exc:
            LOGGER.exception("Error en chat conv_id=%s: %s", conv_id, exc)
            raise
