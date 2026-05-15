"""Servicio mejorado de extracción de INE: OCR + regex + Ollama."""

from __future__ import annotations

import logging
import time
from typing import Any

from .ine_parser import IneParser
from .ollama_ine_analyzer import OllamaIneAnalyzer
from .ocr_service import OcrService

LOGGER = logging.getLogger("[IneEnhancedService]")


class IneEnhancedService:
    """Extracción de INE: PaddleOCR → regex → Ollama y merge."""

    def __init__(self, ocr_service: OcrService) -> None:
        self._ocr = ocr_service
        self._regex_parser = IneParser()
        self._ollama_analyzer = OllamaIneAnalyzer()

    async def extract_from_images(
        self,
        frente_bytes: bytes,
        reverso_bytes: bytes | None,
    ) -> dict[str, Any]:
        """OCR en imágenes, parse regex, análisis Ollama y merge."""
        total_start = time.perf_counter()
        fields_from_ollama: list[str] = []

        LOGGER.info("Paso 1: Ejecutando PaddleOCR (frente%s)", " y reverso" if reverso_bytes else "")
        ocr_start = time.perf_counter()

        frente_result = self._ocr.extract_text(image_bytes=frente_bytes)
        reverso_result: dict[str, Any] | None = None
        if reverso_bytes is not None:
            reverso_result = self._ocr.extract_text(image_bytes=reverso_bytes)

        if reverso_result is not None:
            combined_text = (
                "=== FRENTE ===\n"
                f"{frente_result['text']}\n\n"
                "=== REVERSO ===\n"
                f"{reverso_result['text']}"
            )
        else:
            combined_text = f"=== FRENTE ===\n{frente_result['text']}\n"

        ocr_time = int((time.perf_counter() - ocr_start) * 1000)
        LOGGER.info("PaddleOCR completado en %dms", ocr_time)

        LOGGER.info("Paso 2: Ejecutando parser regex")
        regex_start = time.perf_counter()
        regex_data = self._regex_parser.parse(combined_text)
        regex_time = int((time.perf_counter() - regex_start) * 1000)

        regex_nulls = sum(
            1
            for k, v in regex_data.items()
            if v is None and k not in ("curpDerivado", "fuenteExtraccion")
        )
        LOGGER.info("Parser regex completado en %dms. Campos null: %d", regex_time, regex_nulls)

        LOGGER.info("Paso 3: Enviando texto a Ollama para análisis inteligente")
        ollama_result = await self._ollama_analyzer.analyze(combined_text)
        ollama_data = ollama_result.get("data") or {}
        if not isinstance(ollama_data, dict):
            ollama_data = {}
        ollama_time = int(ollama_result.get("processing_time_ms", 0) or 0)
        ollama_success = bool(ollama_result.get("success")) and bool(ollama_data)

        if ollama_success:
            LOGGER.info("Paso 4: Merge inteligente regex + Ollama")
            final_data = OllamaIneAnalyzer.merge_results(regex_data, ollama_data)

            for key in final_data:
                if key in ("curpDerivado", "fuenteExtraccion"):
                    continue
                regex_val = regex_data.get(key)
                final_val = final_data.get(key)
                if (regex_val is None or regex_val == "") and final_val not in (None, ""):
                    fields_from_ollama.append(key)

            if fields_from_ollama:
                final_data["fuenteExtraccion"] = "OCR_OLLAMA_MIXTO"
                LOGGER.info("Ollama completó %d campos: %s", len(fields_from_ollama), fields_from_ollama)
            else:
                final_data["fuenteExtraccion"] = regex_data.get("fuenteExtraccion") or "OCR"
        else:
            LOGGER.warning("Ollama no disponible o falló, usando solo regex")
            final_data = dict(regex_data)
            if not ollama_result.get("success"):
                LOGGER.debug("Detalle Ollama: %s", ollama_result.get("error"))

        total_time = int((time.perf_counter() - total_start) * 1000)

        final_nulls = sum(
            1
            for k, v in final_data.items()
            if v is None and k not in ("curpDerivado", "fuenteExtraccion")
        )
        LOGGER.info(
            "Extracción completada: total=%dms (ocr=%dms, regex=%dms, ollama=%dms). Campos null: %d→%d",
            total_time,
            ocr_time,
            regex_time,
            ollama_time,
            regex_nulls,
            final_nulls,
        )

        return {
            "success": True,
            "data": final_data,
            "debug": {
                "ocr_time_ms": ocr_time,
                "regex_time_ms": regex_time,
                "ollama_time_ms": ollama_time,
                "total_time_ms": total_time,
                "ollama_used": ollama_success,
                "fields_completed_by_ollama": fields_from_ollama if ollama_success else [],
                "ocr_confidence": {
                    "frente": float(frente_result.get("confidence", 0.0)),
                    "reverso": float(reverso_result.get("confidence", 0.0)) if reverso_result else None,
                },
            },
            "raw_text": combined_text,
            "processing_time_ms": total_time,
        }
