"""Paquete OCR: PaddleOCR, parser INE y derivación CURP."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .curp_deriver import CurpDeriver
from .ine_parser import IneParser

__all__ = ["OcrService", "IneParser", "CurpDeriver"]


def __getattr__(name: str) -> Any:
    """Carga diferida de `OcrService` para evitar importar PaddleOCR al importar solo el parser."""
    if name == "OcrService":
        from .ocr_service import OcrService

        return OcrService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    from .ocr_service import OcrService as OcrService
