"""Herramientas de consulta de clientes vía NestJS /api/ai-tools/."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from services.nestjs_client import NestJSClient

from .base_tool import BaseTool


class GetClientSummaryTool(BaseTool):
    """Obtiene el resumen completo de un cliente por ID o RFC."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "getClientSummary"

    @property
    def description(self) -> str:
        return (
            "Obtiene información detallada de un cliente específico: nombre, RFC, contacto, "
            "dirección, total de equipos, instalaciones y usuarios. "
            "Usa esta herramienta cuando el usuario pregunte por un cliente en particular, "
            "ya sea por su nombre, RFC o ID."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "clienteId": {
                    "type": "integer",
                    "description": "ID numérico del cliente",
                },
                "rfc": {
                    "type": "string",
                    "description": "RFC del cliente (12-13 caracteres)",
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        cliente_id = kwargs.get("clienteId")
        rfc = kwargs.get("rfc")
        if rfc is not None and str(rfc).strip():
            encoded = quote(str(rfc).strip(), safe="")
            return await self._nestjs.get(f"/ai-tools/clientes/rfc/{encoded}")
        if cliente_id is not None:
            return await self._nestjs.get(f"/ai-tools/clientes/{int(cliente_id)}")
        return {"status": "error", "message": "Se requiere clienteId o rfc", "data": None}


class GetClientListTool(BaseTool):
    """Lista clientes con filtros opcionales."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "getClientList"

    @property
    def description(self) -> str:
        return (
            "Obtiene la lista de clientes registrados. "
            "Puede filtrar por estatus (1=activo, 0=inactivo). "
            "Usa esta herramienta cuando el usuario pregunte cuántos clientes hay, "
            "quiera ver la lista o pregunte por clientes activos/inactivos."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "estatus": {
                    "type": "integer",
                    "description": "1 para activos, 0 para inactivos. Sin valor retorna todos.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Cantidad máxima de resultados (default 50)",
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if kwargs.get("estatus") is not None:
            params["estatus"] = kwargs["estatus"]
        if kwargs.get("limit") is not None:
            params["limit"] = kwargs["limit"]
        return await self._nestjs.get("/ai-tools/clientes", params=params or None)
