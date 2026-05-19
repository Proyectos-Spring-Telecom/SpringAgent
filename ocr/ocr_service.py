from __future__ import annotations

import gc
import io
import logging
import threading
import time
from typing import TYPE_CHECKING, Any

import numpy as np
from PIL import Image

from config import settings

if TYPE_CHECKING:
    from paddleocr import PaddleOCR

LOGGER = logging.getLogger("[OcrService]")


class OcrService:
    _instance: "OcrService | None" = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._ocr_lock = threading.Lock()
        self._ocr: PaddleOCR | None = None
        self._unload_timer: threading.Timer | None = None
        self._unload_timeout: int = settings.ocr_unload_timeout
        self._last_used: float = 0.0
        LOGGER.info(
            "OcrService creado (lazy load, auto-descarga después de %ds de inactividad)",
            self._unload_timeout,
        )

    def _ensure_ocr(self) -> PaddleOCR:
        """Carga PaddleOCR solo cuando se necesita (lazy loading)."""
        if self._ocr is None:
            LOGGER.info("Cargando PaddleOCR por primera vez...")
            start = time.perf_counter()
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang="es",
                use_gpu=False,
                show_log=False,
            )
            elapsed = time.perf_counter() - start
            LOGGER.info("PaddleOCR cargado en %.1fs", elapsed)
        self._reset_unload_timer()
        return self._ocr

    def _reset_unload_timer(self) -> None:
        """Reinicia el timer de auto-descarga cada vez que se usa OCR."""
        self._last_used = time.time()

        if self._unload_timer is not None:
            self._unload_timer.cancel()

        self._unload_timer = threading.Timer(
            self._unload_timeout,
            self._unload_ocr,
        )
        self._unload_timer.daemon = True
        self._unload_timer.start()

    def _unload_ocr(self) -> None:
        """Descarga PaddleOCR de RAM después del timeout de inactividad."""
        with self._ocr_lock:
            if self._ocr is not None:
                idle_time = time.time() - self._last_used
                LOGGER.info(
                    "Descargando PaddleOCR de RAM (inactivo %.0fs)",
                    idle_time,
                )
                self._ocr = None
                gc.collect()
                LOGGER.info("PaddleOCR descargado. RAM liberada.")

    @classmethod
    def get_instance(cls) -> "OcrService":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def is_loaded(self) -> bool:
        """True si PaddleOCR está cargado en RAM."""
        return self._ocr is not None

    def extract_text(self, image_bytes: bytes) -> dict[str, Any]:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = image.size

        if width < 600:
            image = image.resize((width * 3, height * 3), Image.Resampling.LANCZOS)

        img_array = np.array(image)

        with self._ocr_lock:
            ocr = self._ensure_ocr()
            raw_result = ocr.ocr(img_array, cls=True)

        lines: list[dict[str, Any]] = []
        confidences: list[float] = []

        if raw_result and raw_result[0]:
            for item in raw_result[0]:
                bbox, text_conf = item
                text, confidence = text_conf
                confidence_percent = float(confidence) * 100.0
                confidences.append(confidence_percent)
                lines.append(
                    {
                        "text": str(text),
                        "confidence": round(confidence_percent, 2),
                        "bbox": [[float(point[0]), float(point[1])] for point in bbox],
                    }
                )

        full_text = "\n".join(line["text"] for line in lines)
        avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

        return {
            "text": full_text,
            "confidence": avg_confidence,
            "lines": lines,
        }
