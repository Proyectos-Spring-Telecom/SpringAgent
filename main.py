from __future__ import annotations

import base64
import binascii
import logging
import time
import uuid
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import APIKeyHeader

from agent.agent_service import AgentService
from agent.ollama_client import OllamaClient
from config import settings
from ocr.ine_enhanced_service import IneEnhancedService
from ocr.ine_parser import IneParser
from ocr.ocr_schemas import (
    BatchOcrRequest,
    BatchOcrResponse,
    IneExtractData,
    IneExtractResponse,
    IneOcrResponse,
    OcrConfidence,
    OcrRequest,
    OcrResponse,
)
from ocr.ocr_service import OcrService
from middleware.auth_middleware import ServiceKeyMiddleware
from schemas.chat import ChatRequest, ChatResponse


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOGGER = logging.getLogger("[API]")
INE_EXTRACT_LOGGER = logging.getLogger("[IneExtract]")
MAX_UPLOAD_SIZE_BYTES = settings.ocr_max_upload_size

api_key_header = APIKeyHeader(name="X-Service-Key", auto_error=False)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
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
INE_PARSER = IneParser()
INE_ENHANCED: IneEnhancedService | None = None
AGENT = AgentService()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ServiceKeyMiddleware)


def _normalize_language(language: str) -> Literal["es", "en"]:
    normalized = (language or "spa+eng").strip().lower()
    if normalized in {"spa+eng", "es", "spa"}:
        return "es"
    if normalized == "en":
        return "en"
    return "es"


def _decode_base64_image(image_base64: str) -> bytes:
    try:
        payload = image_base64.split(",", 1)[1] if "," in image_base64 else image_base64
        return base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Imagen base64 inválida") from exc


async def _read_upload_image(file: UploadFile, field_name: str) -> bytes:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Archivo no es imagen")

    try:
        image_bytes = await file.read()
    except Exception as exc:
        LOGGER.exception("Error leyendo archivo multipart (%s)", field_name)
        raise HTTPException(status_code=500, detail="Error leyendo archivo") from exc

    if len(image_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Archivo demasiado grande")

    return image_bytes


def _has_upload_file(file: UploadFile | None) -> bool:
    """True si el cliente envió un archivo multipart con nombre (no solo el campo vacío)."""
    if file is None:
        return False
    name = getattr(file, "filename", None)
    return bool(name and str(name).strip())


async def _read_reverso_image_optional(reverso: UploadFile | None) -> bytes | None:
    """Lee la imagen del reverso si se envió; si no, retorna None."""
    if not _has_upload_file(reverso):
        return None
    assert reverso is not None
    return await _read_upload_image(file=reverso, field_name="reverso")


@app.on_event("startup")
def startup_event() -> None:
    global INE_ENHANCED
    LOGGER.info("Inicializando singleton de OcrService")
    ocr_singleton = OcrService.get_instance()
    INE_ENHANCED = IneEnhancedService(ocr_singleton)
    LOGGER.info("IneEnhancedService inicializado (OCR + regex + Ollama)")


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


@app.post("/ocr", response_model=OcrResponse)
def ocr_endpoint(request: OcrRequest) -> OcrResponse:
    _ = _normalize_language(request.language)
    start_time = time.perf_counter()

    image_bytes = _decode_base64_image(request.image_base64)
    service = OcrService.get_instance()

    try:
        result = service.extract_text(image_bytes=image_bytes)
        processing_time_ms = int((time.perf_counter() - start_time) * 1000)
        result["processing_time_ms"] = processing_time_ms
        return OcrResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.exception("Error interno en /ocr")
        raise HTTPException(status_code=500, detail="Error interno del servicio OCR") from exc


@app.post("/ocr/batch", response_model=BatchOcrResponse)
def ocr_batch_endpoint(request: BatchOcrRequest) -> BatchOcrResponse:
    _ = _normalize_language(request.language)
    service = OcrService.get_instance()
    results: list[dict[str, object]] = []

    for item in request.images:
        image_id = str(item.get("id", ""))
        image_base64 = item.get("image_base64")
        if not isinstance(image_base64, str):
            raise HTTPException(status_code=400, detail="Imagen base64 inválida en batch")

        image_bytes = _decode_base64_image(image_base64)
        try:
            extracted = service.extract_text(image_bytes=image_bytes)
            results.append(
                {
                    "id": image_id,
                    "text": extracted["text"],
                    "confidence": extracted["confidence"],
                }
            )
        except HTTPException:
            raise
        except Exception as exc:
            LOGGER.exception("Error interno en /ocr/batch para id=%s", image_id)
            raise HTTPException(status_code=500, detail="Error interno del servicio OCR") from exc

    return BatchOcrResponse(results=results)


@app.post("/ocr/upload", response_model=OcrResponse)
async def ocr_upload_endpoint(
    file: UploadFile = File(...),
    language: str = Form("spa+eng"),
) -> OcrResponse:
    _ = _normalize_language(language)
    start_time = time.perf_counter()
    image_bytes = await _read_upload_image(file=file, field_name="file")
    service = OcrService.get_instance()

    try:
        result = service.extract_text(image_bytes=image_bytes)
        processing_time_ms = int((time.perf_counter() - start_time) * 1000)
        result["processing_time_ms"] = processing_time_ms
        return OcrResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.exception("Error interno en /ocr/upload")
        raise HTTPException(status_code=500, detail="Error interno del servicio OCR") from exc


@app.post("/ocr/upload-ine", response_model=IneOcrResponse)
async def ocr_upload_ine_endpoint(
    frente: UploadFile = File(...),
    reverso: UploadFile | None = File(default=None),
    language: str = Form("spa+eng"),
) -> IneOcrResponse:
    _ = _normalize_language(language)
    start_time = time.perf_counter()
    service = OcrService.get_instance()

    frente_bytes = await _read_upload_image(file=frente, field_name="frente")
    reverso_bytes = await _read_reverso_image_optional(reverso)

    try:
        frente_start = time.perf_counter()
        frente_result = service.extract_text(image_bytes=frente_bytes)
        frente_result["processing_time_ms"] = int((time.perf_counter() - frente_start) * 1000)

        reverso_result: dict | None = None
        if reverso_bytes is not None:
            reverso_start = time.perf_counter()
            reverso_result = service.extract_text(image_bytes=reverso_bytes)
            reverso_result["processing_time_ms"] = int((time.perf_counter() - reverso_start) * 1000)

        if reverso_result is not None:
            combined_text = (
                "=== FRENTE ===\n"
                f"{frente_result['text']}\n\n"
                "=== REVERSO ===\n"
                f"{reverso_result['text']}"
            )
        else:
            combined_text = f"=== FRENTE ===\n{frente_result['text']}\n"

        total_processing_time_ms = int((time.perf_counter() - start_time) * 1000)

        return IneOcrResponse(
            frente=OcrResponse(**frente_result),
            reverso=OcrResponse(**reverso_result) if reverso_result is not None else None,
            combined_text=combined_text,
            processing_time_ms=total_processing_time_ms,
        )
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.exception("Error interno en /ocr/upload-ine")
        raise HTTPException(status_code=500, detail="Error interno del servicio OCR") from exc


@app.post("/ine/extract", response_model=IneExtractResponse)
async def ine_extract_endpoint(
    frente: UploadFile = File(...),
    reverso: UploadFile | None = File(default=None),
) -> IneExtractResponse:
    start_time = time.perf_counter()
    service = OcrService.get_instance()

    frente_bytes = await _read_upload_image(file=frente, field_name="frente")
    reverso_bytes = await _read_reverso_image_optional(reverso)

    try:
        frente_result = service.extract_text(image_bytes=frente_bytes)
        reverso_result: dict | None = None
        if reverso_bytes is not None:
            reverso_result = service.extract_text(image_bytes=reverso_bytes)

        if reverso_result is not None:
            raw_text = (
                "=== FRENTE ===\n"
                f"{frente_result['text']}\n\n"
                "=== REVERSO ===\n"
                f"{reverso_result['text']}"
            )
        else:
            raw_text = f"=== FRENTE ===\n{frente_result['text']}\n"

        parsed_data = INE_PARSER.parse(raw_text)
        total_processing_time_ms = int((time.perf_counter() - start_time) * 1000)

        response = IneExtractResponse(
            success=True,
            extraction_id=str(uuid.uuid4()),
            data=IneExtractData(**parsed_data),
            ocr_confidence=OcrConfidence(
                frente=float(frente_result.get("confidence", 0.0)),
                reverso=float(reverso_result.get("confidence", 0.0)) if reverso_result is not None else None,
            ),
            raw_text=raw_text,
            processing_time_ms=total_processing_time_ms,
            upload_method="multipart",
        )
        INE_EXTRACT_LOGGER.info("Extraccion completada id=%s", response.extraction_id)
        return response
    except HTTPException:
        raise
    except Exception as exc:
        INE_EXTRACT_LOGGER.exception("Error interno en /ine/extract")
        raise HTTPException(status_code=500, detail="Error interno del extractor INE") from exc


@app.post("/ine/extract-enhanced")
async def ine_extract_enhanced_endpoint(
    frente: UploadFile = File(..., description="Imagen del frente de la INE"),
    reverso: UploadFile | None = File(default=None, description="Imagen del reverso de la INE (opcional)"),
) -> dict:
    """Extracción mejorada: PaddleOCR + regex + Ollama (merge). Si Ollama falla, solo regex."""
    if INE_ENHANCED is None:
        raise HTTPException(status_code=503, detail="Servicio de extracción INE mejorada no disponible")

    frente_bytes = await _read_upload_image(file=frente, field_name="frente")
    reverso_bytes = await _read_reverso_image_optional(reverso)

    try:
        return await INE_ENHANCED.extract_from_images(frente_bytes, reverso_bytes)
    except HTTPException:
        raise
    except Exception as exc:
        INE_EXTRACT_LOGGER.exception("Error interno en /ine/extract-enhanced")
        raise HTTPException(status_code=500, detail="Error interno del extractor INE mejorado") from exc
