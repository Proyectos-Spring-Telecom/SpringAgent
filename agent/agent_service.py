"""Orquestador principal del agente IA con Tool Calling."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Optional

from agent_tools.tool_registry import ToolRegistry
from agent_tools.unified_tools import (
    BuscarArrendatariosTool,
    BuscarClientesTool,
    BuscarContratosTool,
    BuscarInmueblesTool,
    BuscarPagosTool,
    BuscarUsuariosTool,
)
from services.nestjs_client import NestJSClient

from .ollama_client import OllamaClient
from .prompt_templates import build_system_prompt

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
    """Agente IA con Tool Calling hacia NestJS (clientes, inmobiliario y catálogos)."""

    def __init__(self) -> None:
        self._ollama = OllamaClient()
        self._nestjs = NestJSClient()
        self._registry = ToolRegistry()
        self._register_tools()

    def _register_tools(self) -> None:
        """Registra las 6 herramientas unificadas."""
        self._registry.register(BuscarClientesTool(self._nestjs))
        self._registry.register(BuscarUsuariosTool(self._nestjs))
        self._registry.register(BuscarInmueblesTool(self._nestjs))
        self._registry.register(BuscarArrendatariosTool(self._nestjs))
        self._registry.register(BuscarContratosTool(self._nestjs))
        self._registry.register(BuscarPagosTool(self._nestjs))
        LOGGER.info("Tools registradas: %s", self._registry.list_names())

    async def _fetch_user_context(
        self,
        user_id: Optional[int],
        client_id: Optional[int],
    ) -> dict[str, Any]:
        """Consulta NestJS para obtener datos completos del usuario y su cliente.

        Retorna un diccionario con toda la info disponible.
        Si falla, retorna dict vacío sin bloquear el chat.
        """
        context: dict[str, Any] = {}

        if user_id:
            try:
                user_data = await self._nestjs.get(f"/ai-tools/usuarios/{user_id}")
                if user_data.get("status") == "success":
                    data = user_data.get("data", {}) or {}

                    nombre = data.get("nombre", "")
                    apellido_p = data.get("apellidoPaterno", "")
                    apellido_m = data.get("apellidoMaterno", "")
                    parts = [p for p in [nombre, apellido_p, apellido_m] if p]

                    context["user_id"] = user_id
                    context["user_name"] = " ".join(parts) if parts else None
                    context["user_nombre"] = nombre or None
                    context["user_apellido_paterno"] = apellido_p or None
                    context["user_apellido_materno"] = apellido_m or None
                    context["user_username"] = data.get("userName") or None
                    context["user_telefono"] = data.get("telefono") or None
                    context["user_rol_id"] = data.get("idRol")
                    context["user_rol_nombre"] = data.get("rolNombre") or None
                    context["user_estatus"] = "activo" if data.get("estatus") == 1 else "inactivo"
                    context["user_ultimo_login"] = data.get("ultimoLogin") or None
                    context["user_email_confirmado"] = data.get("emailConfirmado")
                    context["client_id"] = data.get("idCliente") or client_id
                    context["client_name"] = data.get("clienteNombre") or None
                    context["client_rfc"] = data.get("clienteRfc") or None

                    LOGGER.info(
                        "Contexto usuario: %s | rol: %s | cliente: %s",
                        context.get("user_name"),
                        context.get("user_rol_nombre"),
                        context.get("client_name"),
                    )
            except Exception as exc:
                LOGGER.warning("No se pudo obtener datos del usuario %s: %s", user_id, exc)

        if not context.get("client_name") and client_id:
            try:
                client_data = await self._nestjs.get(f"/ai-tools/clientes/{client_id}")
                if client_data.get("status") == "success":
                    data = client_data.get("data", {}) or {}
                    context["client_id"] = client_id
                    context["client_name"] = data.get("nombre") or None
                    context["client_rfc"] = data.get("rfc") or None
                    LOGGER.info("Contexto cliente: %s", context.get("client_name"))
            except Exception as exc:
                LOGGER.warning("No se pudo obtener datos del cliente %s: %s", client_id, exc)

        return context

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

        LOGGER.info(
            "Chat request: user_id=%s client_id=%s message='%s'",
            user_id,
            client_id,
            (message or "")[:100],
        )

        user_context = await self._fetch_user_context(user_id, client_id)
        system_prompt = build_system_prompt(user_context=user_context)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
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
                "Chat completado conv_id=%s user=%s tools_used=%s tiempo=%dms",
                conv_id,
                user_context.get("user_name") or user_id,
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
