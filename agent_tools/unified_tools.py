"""Tools unificadas para qwen2.5:3b — una tool por dominio."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from services.nestjs_client import NestJSClient

from .base_tool import BaseTool


class BuscarClientesTool(BaseTool):
    """Busca clientes. Con ID o RFC da detalle, sin ellos da la lista."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "buscarClientes"

    @property
    def description(self) -> str:
        return (
            "Busca clientes. Si das id o rfc, retorna detalle de ese cliente. "
            "Si no, retorna la lista de clientes."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID del cliente para ver detalle"},
                "rfc": {"type": "string", "description": "RFC del cliente para buscar"},
                "estatus": {"type": "integer", "description": "1=activos, 0=inactivos"},
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        rfc = kwargs.get("rfc")
        if rfc is not None and str(rfc).strip():
            encoded = quote(str(rfc).strip(), safe="")
            return await self._nestjs.get(f"/ai-tools/clientes/rfc/{encoded}")
        if kwargs.get("id") is not None:
            return await self._nestjs.get(f"/ai-tools/clientes/{int(kwargs['id'])}")
        params = {k: v for k, v in kwargs.items() if v is not None and k in ("estatus",)}
        return await self._nestjs.get("/ai-tools/clientes", params=params or None)


class BuscarUsuariosTool(BaseTool):
    """Busca usuarios. Con ID da detalle, sin él da la lista."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "buscarUsuarios"

    @property
    def description(self) -> str:
        return (
            "Busca usuarios del sistema. Si das id, retorna detalle. "
            "Si no, retorna lista. Puede filtrar por clienteId."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID del usuario para ver detalle"},
                "clienteId": {"type": "integer", "description": "Filtrar usuarios de un cliente"},
                "estatus": {"type": "integer", "description": "1=activos, 0=inactivos"},
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        if kwargs.get("id") is not None:
            return await self._nestjs.get(f"/ai-tools/usuarios/{int(kwargs['id'])}")
        params = {
            k: v for k, v in kwargs.items() if v is not None and k in ("clienteId", "estatus")
        }
        return await self._nestjs.get("/ai-tools/usuarios", params=params or None)


class BuscarInmueblesTool(BaseTool):
    """Busca inmuebles. Con ID da detalle, sin él da la lista."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "buscarInmuebles"

    @property
    def description(self) -> str:
        return (
            "Busca inmuebles/propiedades. Si das id, retorna detalle con zonas y servicios. "
            "Si no, retorna lista. Filtra por idArrendador."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID del inmueble para ver detalle"},
                "idArrendador": {
                    "type": "integer",
                    "description": "Filtrar inmuebles de un cliente/arrendador",
                },
                "estatus": {"type": "integer", "description": "1=activos, 0=inactivos"},
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        if kwargs.get("id") is not None:
            return await self._nestjs.get(f"/ai-tools/inmuebles/{int(kwargs['id'])}")
        params = {
            k: v for k, v in kwargs.items() if v is not None and k in ("idArrendador", "estatus")
        }
        return await self._nestjs.get("/ai-tools/inmuebles", params=params or None)


class BuscarArrendatariosTool(BaseTool):
    """Busca arrendatarios/inquilinos. Con ID da detalle, sin él da la lista."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "buscarArrendatarios"

    @property
    def description(self) -> str:
        return (
            "Busca arrendatarios (inquilinos). Si das id, retorna detalle con contratos y socios. "
            "Si no, retorna lista. Filtra por idArrendador."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID del arrendatario para ver detalle"},
                "idArrendador": {
                    "type": "integer",
                    "description": "Filtrar arrendatarios de un cliente",
                },
                "estatus": {"type": "integer", "description": "1=activos, 0=inactivos"},
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        if kwargs.get("id") is not None:
            return await self._nestjs.get(f"/ai-tools/arrendatarios/{int(kwargs['id'])}")
        params = {
            k: v for k, v in kwargs.items() if v is not None and k in ("idArrendador", "estatus")
        }
        return await self._nestjs.get("/ai-tools/arrendatarios", params=params or None)


class BuscarContratosTool(BaseTool):
    """Busca contratos de arrendamiento. Con ID da detalle, sin él da la lista."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "buscarContratos"

    @property
    def description(self) -> str:
        return (
            "Busca contratos de arrendamiento. Si das id, retorna detalle financiero completo. "
            "Si no, retorna lista. Filtra por idArrendatario o idInmueble."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID del contrato para ver detalle"},
                "idArrendatario": {
                    "type": "integer",
                    "description": "Filtrar contratos de un arrendatario",
                },
                "idInmueble": {"type": "integer", "description": "Filtrar contratos de un inmueble"},
                "estatus": {"type": "integer", "description": "1=activos, 0=inactivos"},
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        if kwargs.get("id") is not None:
            return await self._nestjs.get(f"/ai-tools/contratos/{int(kwargs['id'])}")
        params = {
            k: v
            for k, v in kwargs.items()
            if v is not None and k in ("idArrendatario", "idInmueble", "estatus")
        }
        return await self._nestjs.get("/ai-tools/contratos", params=params or None)


class BuscarPagosTool(BaseTool):
    """Busca pagos. Con idInmueble puede dar resumen financiero."""

    def __init__(self, nestjs: NestJSClient) -> None:
        self._nestjs = nestjs

    @property
    def name(self) -> str:
        return "buscarPagos"

    @property
    def description(self) -> str:
        return (
            "Busca pagos. Si das resumen=true con idInmueble, retorna resumen financiero "
            "(total pagado vs pendiente). Si no, retorna lista de pagos. "
            "Estatus: 2=pendiente, 1=pagado, 0=cancelado."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "idInmueble": {"type": "integer", "description": "Filtrar pagos de un inmueble"},
                "resumen": {
                    "type": "boolean",
                    "description": "true para resumen financiero del inmueble",
                },
                "estatus": {
                    "type": "integer",
                    "description": "2=pendiente, 1=pagado, 0=cancelado",
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        if kwargs.get("resumen") and kwargs.get("idInmueble") is not None:
            return await self._nestjs.get(f"/ai-tools/pagos/resumen/{int(kwargs['idInmueble'])}")
        params = {
            k: v for k, v in kwargs.items() if v is not None and k in ("idInmueble", "estatus")
        }
        return await self._nestjs.get("/ai-tools/pagos", params=params or None)
