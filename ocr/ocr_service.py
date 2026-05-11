from __future__ import annotations

import io
import logging
import threading
from typing import Any

import numpy as np
from PIL import Image
from paddleocr import PaddleOCR


LOGGER = logging.getLogger("[OcrService]")


class OcrService:
    _instance: "OcrService | None" = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._ocr_lock = threading.Lock()
        self._ocr = PaddleOCR(
            use_angle_cls=True,
            lang="es",
            use_gpu=False,
            show_log=False,
        )
        LOGGER.info("Instancia de PaddleOCR inicializada")

    @classmethod
    def get_instance(cls) -> "OcrService":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def extract_text(self, image_bytes: bytes) -> dict[str, Any]:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = image.size

        if width < 600:
            image = image.resize((width * 3, height * 3), Image.Resampling.LANCZOS)

        img_array = np.array(image)

        with self._ocr_lock:
            raw_result = self._ocr.ocr(img_array, cls=True)

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
