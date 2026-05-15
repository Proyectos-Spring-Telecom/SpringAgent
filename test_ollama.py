"""
Test de comunicación con Ollama.
Ejecutar: python test_ollama.py
"""
from __future__ import annotations

import asyncio
import sys
import time

import httpx

try:
    from config import settings

    OLLAMA_URL = settings.ollama_base_url.rstrip("/")
    MODEL = settings.ollama_model
except Exception:
    OLLAMA_URL = "http://localhost:11434"
    MODEL = "qwen2.5:7b"


async def test_connection():
    """Paso 1: Verificar que Ollama está corriendo."""
    print("=" * 60)
    print("TEST DE COMUNICACIÓN CON OLLAMA")
    print("=" * 60)
    print(f"\nURL: {OLLAMA_URL}")
    print(f"Modelo: {MODEL}\n")

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                print("✅ Paso 1: Ollama está corriendo")
                return response.json()
            print(f"❌ Paso 1: Ollama respondió con status {response.status_code}")
            return None
    except httpx.ConnectError:
        print(f"❌ Paso 1: No se puede conectar a {OLLAMA_URL}")
        print("   → ¿Está corriendo 'ollama serve' en otra terminal?")
        return None
    except Exception as e:
        print(f"❌ Paso 1: Error inesperado: {e}")
        return None


async def test_model_available(tags_data):
    """Paso 2: Verificar que el modelo está descargado."""
    if not tags_data:
        print("⏭️  Paso 2: Saltado (Ollama no disponible)")
        return False

    models = [m.get("name", "") for m in tags_data.get("models", [])]
    model_names = [m.split(":")[0] for m in models]

    print(f"\nModelos instalados: {models if models else 'Ninguno'}")

    target_base = MODEL.split(":")[0]
    if target_base in model_names or MODEL in models:
        print(f"✅ Paso 2: Modelo '{MODEL}' está disponible")
        return True
    print(f"❌ Paso 2: Modelo '{MODEL}' NO está instalado")
    print(f"   → Ejecuta: ollama pull {MODEL}")
    return False


async def test_simple_chat():
    """Paso 3: Enviar un mensaje simple y verificar respuesta."""
    print(f"\nEnviando pregunta simple a {MODEL}...")
    start = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "user", "content": "Responde solo con: CONEXIÓN EXITOSA"}
                    ],
                    "stream": False,
                    "options": {"num_ctx": 512},
                },
            )
            elapsed = time.perf_counter() - start

            if response.status_code == 200:
                data = response.json()
                content = data.get("message", {}).get("content", "")
                print(f"✅ Paso 3: Respuesta recibida en {elapsed:.1f}s")
                print(f"   Ollama dice: \"{content.strip()[:200]}\"")
                return True
            print(f"❌ Paso 3: Status {response.status_code}")
            print(f"   Body: {response.text[:300]}")
            return False
    except httpx.ReadTimeout:
        elapsed = time.perf_counter() - start
        print(f"❌ Paso 3: Timeout después de {elapsed:.1f}s")
        print("   → El modelo puede estar cargándose por primera vez. Intenta de nuevo.")
        return False
    except Exception as e:
        print(f"❌ Paso 3: Error: {e}")
        return False


async def test_tool_calling():
    """Paso 4: Verificar que Tool Calling funciona."""
    print(f"\nProbando Tool Calling con {MODEL}...")
    start = time.perf_counter()

    tools = [
        {
            "type": "function",
            "function": {
                "name": "getClientList",
                "description": "Obtiene la lista de clientes activos del sistema",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "estatus": {
                            "type": "integer",
                            "description": "1 para activos, 0 para inactivos",
                        }
                    },
                    "required": [],
                },
            },
        }
    ]

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Eres un asistente empresarial. Usa las herramientas disponibles para responder.",
                        },
                        {
                            "role": "user",
                            "content": "¿Cuántos clientes activos tenemos?",
                        },
                    ],
                    "tools": tools,
                    "stream": False,
                    "options": {"num_ctx": 2048},
                },
            )
            elapsed = time.perf_counter() - start

            if response.status_code == 200:
                data = response.json()
                message = data.get("message", {})
                tool_calls = message.get("tool_calls")

                if tool_calls:
                    tc = tool_calls[0]
                    func_name = tc.get("function", {}).get("name", "")
                    func_args = tc.get("function", {}).get("arguments", {})
                    print(f"✅ Paso 4: Tool Calling funciona ({elapsed:.1f}s)")
                    print(f"   Tool seleccionada: {func_name}")
                    print(f"   Argumentos: {func_args}")
                    return True
                content = message.get("content", "")
                print(f"⚠️  Paso 4: Ollama NO usó tool calling ({elapsed:.1f}s)")
                print(f"   Respondió directo: \"{content.strip()[:200]}\"")
                print("   → Esto puede pasar. Intenta de nuevo o ajusta el prompt.")
                return False
            print(f"❌ Paso 4: Status {response.status_code}")
            return False
    except httpx.ReadTimeout:
        elapsed = time.perf_counter() - start
        print(f"❌ Paso 4: Timeout después de {elapsed:.1f}s")
        return False
    except Exception as e:
        print(f"❌ Paso 4: Error: {e}")
        return False


async def test_spanish():
    """Paso 5: Verificar que responde bien en español."""
    print("\nProbando respuesta en español...")
    start = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Responde siempre en español. Sé breve.",
                        },
                        {
                            "role": "user",
                            "content": "¿Qué es un RFC en México?",
                        },
                    ],
                    "stream": False,
                    "options": {"num_ctx": 1024},
                },
            )
            elapsed = time.perf_counter() - start

            if response.status_code == 200:
                data = response.json()
                content = data.get("message", {}).get("content", "").strip()
                is_spanish = any(
                    w in content.lower()
                    for w in [
                        "registro",
                        "federal",
                        "contribuyente",
                        "fiscal",
                        "méxico",
                        "impuestos",
                        "sat",
                    ]
                )

                if is_spanish:
                    print(f"✅ Paso 5: Español correcto ({elapsed:.1f}s)")
                    print(f"   Respuesta: \"{content[:200]}...\"")
                else:
                    print(f"⚠️  Paso 5: Respondió pero posiblemente no en español ({elapsed:.1f}s)")
                    print(f"   Respuesta: \"{content[:200]}\"")
                return True
            print(f"❌ Paso 5: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Paso 5: Error: {e}")
        return False


async def main():
    results = {}

    tags = await test_connection()
    results["conexión"] = tags is not None

    if not results["conexión"]:
        print("\n" + "=" * 60)
        print("RESULTADO: ❌ No se pudo conectar a Ollama")
        print("Asegúrate de tener 'ollama serve' corriendo.")
        print("=" * 60)
        sys.exit(1)

    results["modelo"] = await test_model_available(tags)

    if not results["modelo"]:
        print("\n" + "=" * 60)
        print(f"RESULTADO: ❌ Modelo {MODEL} no disponible")
        print(f"Ejecuta: ollama pull {MODEL}")
        print("=" * 60)
        sys.exit(1)

    results["chat"] = await test_simple_chat()

    results["tool_calling"] = await test_tool_calling()

    results["español"] = await test_spanish()

    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    for test, passed in results.items():
        icon = "✅" if passed else "❌"
        print(f"  {icon} {test}")

    total = sum(results.values())
    print(f"\n  {total}/{len(results)} tests pasaron")

    if total == len(results):
        print("\n🟢 Todo listo. SpringAgent puede comunicarse con Ollama.")
    elif total >= 3:
        print("\n🟡 Funciona parcialmente. Revisa los tests que fallaron.")
    else:
        print("\n🔴 Hay problemas de comunicación con Ollama.")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
