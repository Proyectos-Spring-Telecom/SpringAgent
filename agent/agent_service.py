"""Orquestador principal del agente IA con Tool Calling."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Optional

from agent_tools.client_tools import GetClientListTool, GetClientSummaryTool
from agent_tools.tool_registry import ToolRegistry
from agent_tools.user_tools import GetUserDetailTool, GetUserListTool
from services.nestjs_client import NestJSClient

from .ollama_client import OllamaClient
from .prompt_templates import SYSTEM_PROMPT

LOGGER = logging.getLogger("[AgentService]")

_MAX_TOOL_ITERATIONS = 5


def _build_tool_result_message(tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Construye el mensaje role=tool que Ollama espera tras ejecutar una función."""
    body: dict[str, Any] = {
        "role": "tool",
        "content": json.dumps(payload, ensure_ascii=False, default=str),
    }
    if tool_name:
        body["name"] = tool_name
    return body


class AgentService:
    """Agente IA con Tool Calling hacia NestJS (clientes y usuarios)."""

    def __init__(self) -> None:
        self._ollama = OllamaClient()
        self._nestjs = NestJSClient()
        self._registry = ToolRegistry()
        self._register_tools()

    def _register_tools(self) -> None:
        """Registra todas las herramientas disponibles."""
        self._registry.register(GetClientSummaryTool(self._nestjs))
        self._registry.register(GetClientListTool(self._nestjs))
        self._registry.register(GetUserListTool(self._nestjs))
        self._registry.register(GetUserDetailTool(self._nestjs))
        LOGGER.info("Tools registradas: %s", self._registry.list_names())

    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[int] = None,
        client_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Ejecuta el ciclo de chat con Ollama y tools hasta respuesta final o límite de iteraciones."""
        start_time = time.perf_counter()
        conv_id = conversation_id or str(uuid.uuid4())
        tools_used: list[str] = []

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]

        tool_definitions = self._registry.get_all_definitions()

        try:
            response = await self._ollama.chat(
                messages=messages,
                tools=tool_definitions if tool_definitions else None,
                stream=False,
            )

            assistant_message: dict[str, Any] = dict(response.get("message", {}))
            tool_calls = assistant_message.get("tool_calls")

            iteration = 0
            while tool_calls and iteration < _MAX_TOOL_ITERATIONS:
                iteration += 1
                LOGGER.info("Tool calling iteración %d: %d tools", iteration, len(tool_calls))

                messages.append(assistant_message)

                for tool_call in tool_calls:
                    func = tool_call.get("function") or {}
                    tool_name = func.get("name") or ""
                    tool_args = func.get("arguments", {})
                    LOGGER.info("Ejecutando tool: %s args: %s", tool_name, tool_args)
                    tools_used.append(tool_name)

                    result = await self._registry.execute(tool_name, tool_args)
                    messages.append(_build_tool_result_message(tool_name, result))

                response = await self._ollama.chat(
                    messages=messages,
                    tools=tool_definitions,
                    stream=False,
                )

                assistant_message = dict(response.get("message", {}))
                tool_calls = assistant_message.get("tool_calls")

            final_response = assistant_message.get("content") or ""
            processing_time_ms = int((time.perf_counter() - start_time) * 1000)

            LOGGER.info(
                "Chat completado conv_id=%s tools_used=%s tiempo=%dms",
                conv_id,
                tools_used,
                processing_time_ms,
            )

            return {
                "response": final_response,
                "conversation_id": conv_id,
                "tools_used": tools_used,
                "processing_time_ms": processing_time_ms,
            }

        except Exception as exc:
            LOGGER.exception("Error en chat conv_id=%s: %s", conv_id, exc)
            processing_time_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "response": "Ocurrió un error procesando tu solicitud. Por favor intenta de nuevo.",
                "conversation_id": conv_id,
                "tools_used": tools_used,
                "processing_time_ms": processing_time_ms,
            }
