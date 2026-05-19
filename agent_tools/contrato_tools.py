"""Herramientas de consulta de contratos de arrendamiento."""

from __future__ import annotations

from typing import Any

from services.nestjs_client import NestJSClient

from .base_tool import BaseTool


class GetContratoListTool(BaseTool):
    """Lista contratos con filtros opcionales."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "getContratoList"

    @property
    def description(self) -> str:
        return (
            "Obtiene la lista de contratos de arrendamiento. Puede filtrar por arrendatario, "
            "inmueble o estatus. Usa esta herramienta cuando pregunten por contratos, rentas vigentes, "
            "condiciones de arrendamiento."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "idArrendatario": {"type": "integer", "description": "Filtrar contratos de un arrendatario"},
                "idInmueble": {"type": "integer", "description": "Filtrar contratos de un inmueble"},
                "estatus": {"type": "integer", "description": "1=activo, 0=inactivo"},
                "limit": {"type": "integer", "description": "Máximo resultados"},
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        params = {k: v for k, v in kwargs.items() if v is not None}
        return await self._nestjs.get("/ai-tools/contratos", params=params or None)


class GetContratoDetailTool(BaseTool):
    """Detalle de un contrato por ID."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "getContratoDetail"

    @property
    def description(self) -> str:
        return (
            "Obtiene detalle completo de un contrato: metros rentados, costo por m², renta total, "
            "mantenimiento, depósito, adelanto, años forzosos, IVA, observaciones. "
            "Usa esta herramienta cuando pregunten por los detalles financieros de un contrato."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "contratoId": {"type": "integer", "description": "ID del contrato"},
            },
            "required": ["contratoId"],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        cid = kwargs.get("contratoId")
        if cid is None:
            return {"status": "error", "message": "Se requiere contratoId", "data": None}
        return await self._nestjs.get(f"/ai-tools/contratos/{int(cid)}")
