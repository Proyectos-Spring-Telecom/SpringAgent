from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import APIKeyHeader

from agent.agent_service import AgentService
from agent.ollama_client import OllamaClient
from config import settings
from middleware.auth_middleware import ServiceKeyMiddleware
from schemas.chat import ChatRequest, ChatResponse


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOGGER = logging.getLogger("[API]")

api_key_header = APIKeyHeader(name="X-Service-Key", auto_error=False)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    root_path=settings.app_root_path,
    swagger_ui_parameters={"persistAuthorization": True},
)


def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})["X-Service-Key"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-Service-Key",
    }
    openapi_schema["security"] = [{"X-Service-Key": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = _custom_openapi
AGENT = AgentService()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ServiceKeyMiddleware)


@app.on_event("startup")
def startup_event() -> None:
    LOGGER.info("SpringAgent iniciado")


@app.get("/health")
async def health() -> dict:
    ollama_ok = await OllamaClient().is_healthy()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "ollama": "connected" if ollama_ok else "disconnected",
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    LOGGER.info(
        "POST /chat desde NestJS: user_id=%s client_id=%s message='%s'",
        request.user_id,
        request.client_id,
        (request.message or "")[:100],
    )
    try:
        result = await AGENT.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            client_id=request.client_id,
        )
        return ChatResponse(**result)
    except Exception as exc:
        LOGGER.exception("Error en /chat")
        raise HTTPException(status_code=500, detail="Error procesando solicitud de chat") from exc
