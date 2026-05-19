"""Herramientas de consulta de catálogos: INPC, factores, fórmulas."""

from __future__ import annotations

from typing import Any

from services.nestjs_client import NestJSClient

from .base_tool import BaseTool


class GetInpcTool(BaseTool):
    """Consulta registros INPC."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "getInpc"

    @property
    def description(self) -> str:
        return (
            "Obtiene los registros del INPC (Índice Nacional de Precios al Consumidor). "
            "Puede filtrar por año. Usa esta herramienta cuando pregunten por INPC, "
            "inflación, índices de precios o ajustes de renta por inflación."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "anio": {"type": "integer", "description": "Año para filtrar (ej: 2026)"},
                "limit": {"type": "integer", "description": "Máximo resultados"},
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        params = {k: v for k, v in kwargs.items() if v is not None}
        return await self._nestjs.get("/ai-tools/inpc", params=params or None)


class GetFactoresTool(BaseTool):
    """Consulta factores de cálculo activos."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "getFactores"

    @property
    def description(self) -> str:
        return (
            "Obtiene los factores de cálculo activos (variables, valores, descripciones). "
            "Usa esta herramienta cuando pregunten por factores, variables de cálculo o parámetros."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        return await self._nestjs.get("/ai-tools/factores")


class GetFormulasTool(BaseTool):
    """Consulta fórmulas activas."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "getFormulas"

    @property
    def description(self) -> str:
        return (
            "Obtiene las fórmulas activas para cálculos de renta/mantenimiento. "
            "Usa esta herramienta cuando pregunten por fórmulas, cálculos o cómo se calcula la renta."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        return await self._nestjs.get("/ai-tools/formulas")
