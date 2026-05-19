"""Herramientas de consulta de arrendatarios (inquilinos)."""

from __future__ import annotations

from typing import Any

from services.nestjs_client import NestJSClient

from .base_tool import BaseTool


class GetArrendatarioListTool(BaseTool):
    """Lista arrendatarios con filtros opcionales."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "getArrendatarioList"

    @property
    def description(self) -> str:
        return (
            "Obtiene la lista de arrendatarios (inquilinos/renteros). Puede filtrar por arrendador "
            "(cliente dueño) y estatus. Usa esta herramienta cuando pregunten por arrendatarios, "
            "inquilinos, renteros o quién renta qué."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "idArrendador": {"type": "integer", "description": "ID del cliente arrendador para filtrar"},
                "estatus": {"type": "integer", "description": "1=activo, 0=inactivo"},
                "limit": {"type": "integer", "description": "Máximo resultados (default 50)"},
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        params = {k: v for k, v in kwargs.items() if v is not None}
        return await self._nestjs.get("/ai-tools/arrendatarios", params=params or None)


class GetArrendatarioDetailTool(BaseTool):
    """Detalle de un arrendatario por ID."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "getArrendatarioDetail"

    @property
    def description(self) -> str:
        return (
            "Obtiene detalle completo de un arrendatario: datos de contacto, contratos vigentes, "
            "socios, servicios. Usa esta herramienta cuando pregunten por un arrendatario específico."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "arrendatarioId": {"type": "integer", "description": "ID del arrendatario"},
            },
            "required": ["arrendatarioId"],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        aid = kwargs.get("arrendatarioId")
        if aid is None:
            return {"status": "error", "message": "Se requiere arrendatarioId", "data": None}
        return await self._nestjs.get(f"/ai-tools/arrendatarios/{int(aid)}")
