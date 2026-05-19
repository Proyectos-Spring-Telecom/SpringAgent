"""Middleware de autenticación por X-Service-Key."""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings

LOGGER = logging.getLogger("[AuthMiddleware]")

# Rutas que NO requieren autenticación
EXCLUDED_PATHS = ["/docs", "/openapi.json", "/redoc"]


class ServiceKeyMiddleware(BaseHTTPMiddleware):
    """Valida X-Service-Key en todas las peticiones.

    Si el header no está presente o no coincide con SERVICE_API_KEY,
    retorna 401 Unauthorized.
    """

    async def dispatch(self, request: Request, call_next):
        # Permitir CORS preflight (OPTIONS) sin key
        if request.method == "OPTIONS":
            return await call_next(request)

        # Permitir Swagger y OpenAPI schema
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        service_key = request.headers.get("X-Service-Key") or request.headers.get("x-service-key")
        expected_key = settings.service_api_key

        if not service_key or service_key != expected_key:
            client_ip = request.client.host if request.client else "unknown"
            LOGGER.warning(
                "Acceso no autorizado: %s %s desde %s",
                request.method,
                request.url.path,
                client_ip,
            )
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "message": "No autorizado. Se requiere X-Service-Key válida.",
                },
            )

        return await call_next(request)
