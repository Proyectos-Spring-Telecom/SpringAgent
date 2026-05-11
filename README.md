# SpringAgent

Microservicio **SpringAgent** (FastAPI): expone **PaddleOCR** por HTTP (misma API que antes) y añade un **chat** vía **Ollama** preparado para tool calling en fases posteriores. Pensado para integrarse con el backend NestJS (InmueblesAPI) en `localhost`.

## Requisitos

- Python 3.11+
- Entorno virtual (`venv`)
- Dependencias en `requirements.txt` (incluye `httpx`, `pydantic-settings`, `python-dotenv`)
- Archivo `.env` (copia desde `.env.example`). El archivo `.env` no debe versionarse.

## Configuración

1. Copia `.env.example` a `.env` y revisa puertos, CORS, Ollama y NestJS.
2. `CORS_ORIGINS` es una lista separada por comas (por ejemplo `http://localhost:3005,http://localhost:3000`).

## Inicio del servicio

### Windows (`start.bat`)

Usa el puerto definido en `APP_PORT` del `.env` (por defecto 8001).

```bat
start.bat
```

### Uvicorn manual

```powershell
venv\Scripts\activate
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Documentación interactiva: `http://localhost:8001/docs`

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado del servicio, versión y conexión a Ollama |
| POST | `/chat` | Chat con el agente (requiere Ollama) |
| POST | `/ocr` | OCR desde JSON base64 |
| POST | `/ocr/batch` | OCR por lote |
| POST | `/ocr/upload` | OCR multipart |
| POST | `/ocr/upload-ine` | OCR INE: frente obligatorio, reverso opcional |
| POST | `/ine/extract` | Extracción INE: frente obligatorio, reverso opcional |

### Health check

```bash
curl http://localhost:8001/health
```

Respuesta de ejemplo:

```json
{
  "status": "ok",
  "service": "SpringAgent",
  "version": "1.0.0",
  "ollama": "connected"
}
```

(`ollama` puede ser `disconnected` si el daemon no está en marcha.)

### Chat

```bash
curl -X POST http://localhost:8001/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\": \"Hola, ¿qué puedes hacer?\"}"
```

### OCR simple (`POST /ocr`)

Mismo contrato que antes: cuerpo JSON con `image_base64` y `language` (por compatibilidad se acepta `spa+eng`).

## Estructura del proyecto (Fase 1)

- `main.py` — aplicación FastAPI
- `config.py` — ajustes con `pydantic-settings`
- `ocr/` — servicio OCR, parser INE, esquemas OCR
- `agent/` — cliente Ollama y orquestador del agente
- `services/nestjs_client.py` — cliente HTTP hacia NestJS (Fase 2)
- `agent_tools/` — registro y base de herramientas del agente (Fase 2). El paquete no se llama `tools` para no chocar con el módulo interno `tools` de PaddleOCR.
- `schemas/chat.py` — modelos del endpoint `/chat`

## Integración NestJS

- NestJS puede seguir usando `PADDLEOCR_SERVICE_URL` apuntando a este servicio (por ejemplo `http://localhost:8001`).
- Las llamadas servidor-a-servidor con `X-Service-Key` se implementarán en NestJS y se consumirán desde `NestJSClient` en fases siguientes.

## Pruebas OCR locales

```bash
python test_ocr.py ruta\a\imagen.jpg
```

El script solo usa HTTP; no requiere imports internos del paquete.
