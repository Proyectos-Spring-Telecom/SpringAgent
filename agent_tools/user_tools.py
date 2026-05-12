"""Herramientas de consulta de usuarios vía NestJS /api/ai-tools/."""

from __future__ import annotations

from typing import Any

from services.nestjs_client import NestJSClient

from .base_tool import BaseTool


class GetUserListTool(BaseTool):
    """Lista usuarios con filtros opcionales."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "getUserList"

    @property
    def description(self) -> str:
        return (
            "Obtiene la lista de usuarios del sistema. "
            "Puede filtrar por estatus (1=activo, 0=inactivo) y por cliente. "
            "Usa esta herramienta cuando el usuario pregunte cuántos usuarios hay, "
            "quién tiene acceso al sistema, o los usuarios de un cliente específico "
            "(usa el parámetro clienteId con el ID del cliente)."
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
                "clienteId": {
                    "type": "integer",
                    "description": "ID del cliente para filtrar sus usuarios",
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
        if kwargs.get("clienteId") is not None:
            params["clienteId"] = kwargs["clienteId"]
        if kwargs.get("limit") is not None:
            params["limit"] = kwargs["limit"]
        return await self._nestjs.get("/ai-tools/usuarios", params=params or None)


class GetUserDetailTool(BaseTool):
    """Obtiene detalle de un usuario específico."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "getUserDetail"

    @property
    def description(self) -> str:
        return (
            "Obtiene información detallada de un usuario específico: nombre, correo, rol, "
            "cliente al que pertenece, último login, estatus. "
            "Usa esta herramienta cuando el usuario pregunte por un usuario en particular por su ID."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "userId": {
                    "type": "integer",
                    "description": "ID numérico del usuario",
                },
            },
            "required": ["userId"],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        user_id = kwargs.get("userId")
        if user_id is None:
            return {"status": "error", "message": "Se requiere userId", "data": None}
        return await self._nestjs.get(f"/ai-tools/usuarios/{int(user_id)}")
