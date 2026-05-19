"""Herramientas de consulta de pagos."""

from __future__ import annotations

from typing import Any

from services.nestjs_client import NestJSClient

from .base_tool import BaseTool


class GetPagoListTool(BaseTool):
    """Lista pagos con filtros opcionales."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "getPagoList"

    @property
    def description(self) -> str:
        return (
            "Obtiene la lista de pagos. Puede filtrar por inmueble y estatus "
            "(2=pendiente, 1=pagado, 0=cancelado). Usa esta herramienta cuando pregunten "
            "por pagos, cobros, mensualidades o adeudos."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "idInmueble": {"type": "integer", "description": "Filtrar pagos de un inmueble"},
                "estatus": {"type": "integer", "description": "2=pendiente, 1=pagado, 0=cancelado"},
                "limit": {"type": "integer", "description": "Máximo resultados"},
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        params = {k: v for k, v in kwargs.items() if v is not None}
        return await self._nestjs.get("/ai-tools/pagos", params=params or None)


class GetPagoResumenTool(BaseTool):
    """Resumen financiero de pagos por inmueble."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "getPagoResumen"

    @property
    def description(self) -> str:
        return (
            "Obtiene el resumen financiero de pagos de un inmueble: total pagado, total pendiente, "
            "cantidad de pagos por estatus. Usa esta herramienta cuando pregunten cuánto se debe, "
            "cuánto se ha pagado, o el estado financiero de un inmueble."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "idInmueble": {"type": "integer", "description": "ID del inmueble"},
            },
            "required": ["idInmueble"],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        iid = kwargs.get("idInmueble")
        if iid is None:
            return {"status": "error", "message": "Se requiere idInmueble", "data": None}
        return await self._nestjs.get(f"/ai-tools/pagos/resumen/{int(iid)}")
