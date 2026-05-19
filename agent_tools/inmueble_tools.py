"""Herramientas de consulta de inmuebles."""

from __future__ import annotations

from typing import Any

from services.nestjs_client import NestJSClient

from .base_tool import BaseTool


class GetInmuebleListTool(BaseTool):
    """Lista inmuebles con filtros opcionales."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "getInmuebleList"

    @property
    def description(self) -> str:
        return (
            "Obtiene la lista de inmuebles (propiedades). Puede filtrar por arrendador (cliente dueño) "
            "y por estatus (1=activo, 0=inactivo). Usa esta herramienta cuando pregunten por inmuebles, "
            "propiedades, edificios, locales o cuántos inmuebles hay."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "idArrendador": {
                    "type": "integer",
                    "description": "ID del cliente arrendador (dueño) para filtrar sus inmuebles",
                },
                "estatus": {"type": "integer", "description": "1 para activos, 0 para inactivos"},
                "limit": {"type": "integer", "description": "Máximo de resultados (default 50)"},
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        params = {k: v for k, v in kwargs.items() if v is not None}
        return await self._nestjs.get("/ai-tools/inmuebles", params=params or None)


class GetInmuebleDetailTool(BaseTool):
    """Detalle de un inmueble por ID."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "getInmuebleDetail"

    @property
    def description(self) -> str:
        return (
            "Obtiene el detalle completo de un inmueble: dirección, representante, zonas con superficies, "
            "servicios contratados. Usa esta herramienta cuando pregunten por un inmueble específico por su ID."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "inmuebleId": {"type": "integer", "description": "ID del inmueble"},
            },
            "required": ["inmuebleId"],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        inmueble_id = kwargs.get("inmuebleId")
        if inmueble_id is None:
            return {"status": "error", "message": "Se requiere inmuebleId", "data": None}
        return await self._nestjs.get(f"/ai-tools/inmuebles/{int(inmueble_id)}")
