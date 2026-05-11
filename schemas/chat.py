"""Esquemas de solicitud y respuesta para el endpoint de chat."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Cuerpo de una petición al agente de chat."""

    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[int] = None
    client_id: Optional[int] = None


class ToolUsed(BaseModel):
    """Metadatos de una herramienta invocada (uso futuro en tool calling)."""

    name: str
    parameters: dict
    result_summary: Optional[str] = None


class ChatResponse(BaseModel):
    """Respuesta del agente tras procesar un mensaje."""

    response: str
    conversation_id: str
    tools_used: List[str] = Field(default_factory=list)
    processing_time_ms: int
