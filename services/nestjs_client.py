"""Cliente HTTP para la API de NestJS (InmueblesAPI)."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from config import settings

LOGGER = logging.getLogger("[NestJSClient]")


class NestJSClient:
    """Llamadas autenticadas a NestJS usando X-Service-Key."""

    def __init__(self) -> None:
        self._base_url = settings.nestjs_base_url.rstrip("/")
        self._service_key = settings.nestjs_service_key
        self._timeout = settings.nestjs_timeout

    def _headers(self) -> dict[str, str]:
        return {
            "X-Service-Key": self._service_key,
            "Content-Type": "application/json",
        }

    async def get(self, path: str, params: Optional[dict] = None) -> dict[str, Any]:
        """GET request a NestJS."""
        url = f"{self._base_url}{path}"
        LOGGER.info("GET %s params=%s", url, params)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params, headers=self._headers())
            response.raise_for_status()
            data = response.json()

        LOGGER.info("NestJS respondió: status=%s", data.get("status"))
        return data

    async def post(self, path: str, body: Optional[dict] = None) -> dict[str, Any]:
        """POST request a NestJS."""
        url = f"{self._base_url}{path}"
        LOGGER.info("POST %s", url)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=body, headers=self._headers())
            response.raise_for_status()
            return response.json()

    async def is_healthy(self) -> bool:
        """Verifica que NestJS esté respondiendo."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self._base_url}/../health", headers=self._headers())
                return response.status_code == 200
        except Exception as exc:
            LOGGER.warning("NestJS health check falló: %s", exc)
            return False
