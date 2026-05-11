"""
Script de prueba para el microservicio PaddleOCR.
Uso:
  python test_ocr.py <ruta_imagen>

Ejemplo:
  python test_ocr.py C:\\Users\\TuUsuario\\Pictures\\ine_frontal.jpg
"""
from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

import requests


SERVICE_URL = "http://localhost:8001"


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python test_ocr.py <ruta_imagen>")
        return 1

    image_path = Path(sys.argv[1])
    if not image_path.exists():
        print(f"ERROR: archivo no encontrado: {image_path}")
        return 1

    print(f"Probando OCR con: {image_path}")
    print("-" * 60)

    # 1. Health check
    try:
        health = requests.get(f"{SERVICE_URL}/health", timeout=5)
        print(f"Health check: {health.status_code} → {health.json()}")
    except requests.exceptions.ConnectionError:
        print(f"ERROR: el servicio no responde en {SERVICE_URL}")
        print("Asegúrate de que el servicio está corriendo (start.bat)")
        return 1

    # 2. Leer imagen y codificar a base64
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode("ascii")
    print(f"Imagen: {len(image_bytes):,} bytes → base64 {len(image_base64):,} chars")

    # 3. Enviar al endpoint /ocr
    print("\nEnviando a /ocr...")
    start = time.perf_counter()

    response = requests.post(
        f"{SERVICE_URL}/ocr",
        json={"image_base64": image_base64, "language": "spa+eng"},
        timeout=60,
    )
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    if response.status_code != 200:
        print(f"ERROR HTTP {response.status_code}: {response.text}")
        return 1

    data = response.json()

    # 4. Mostrar resultados
    print(f"\n{'=' * 60}")
    print(f"RESULTADO (tomó {elapsed_ms} ms en cliente)")
    print(f"{'=' * 60}")
    print(f"Confianza promedio: {data['confidence']:.2f}%")
    print(f"Tiempo procesamiento servidor: {data['processing_time_ms']} ms")
    print(f"Líneas detectadas: {len(data['lines'])}")
    print(f"\n--- TEXTO EXTRAÍDO ---")
    print(data["text"])
    print(f"\n--- DETALLE POR LÍNEA ---")
    for i, line in enumerate(data["lines"], 1):
        print(f"  {i:2d}. [{line['confidence']:5.1f}%] {line['text']}")

    # 5. Guardar JSON completo en archivo
    output_file = image_path.parent / f"{image_path.stem}_ocr_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nResultado completo guardado en: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
