"""Analizador de INE con Ollama — complementa al parser regex."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from agent.ollama_client import OllamaClient

LOGGER = logging.getLogger("[OllamaIneAnalyzer]")

INE_EXTRACTION_PROMPT = """Eres un experto en documentos de identidad mexicanos (INE/IFE).

Te voy a dar el texto crudo extraído por OCR de una credencial INE (frente y reverso). El texto puede tener errores de OCR: palabras pegadas, caracteres mal reconocidos, líneas desordenadas.

Tu trabajo es extraer los siguientes campos. Si no puedes identificar un campo con certeza, usa null. NO inventes datos.

CAMPOS A EXTRAER (JSON con estas claves exactas):
- nombre: Solo el/los nombre(s) de pila (sin apellidos). Ejemplo: "MARIA GUADALUPE"
- apellidoPaterno: Primer apellido. Ejemplo: "GARCIA"
- apellidoMaterno: Segundo apellido. Ejemplo: "LOPEZ"
- curp: CURP completa (18 caracteres, formato: 4 letras + 6 dígitos + 6 alfanuméricos + 2 dígitos). Ejemplo: "GALM850101MDFRPRA09"
- claveElector: Clave de elector (18 caracteres alfanuméricos). Ejemplo: "GRCLPR85010109H200"
- fechaNacimiento: Fecha de nacimiento en formato DD/MM/YYYY. Ejemplo: "01/01/1985"
- sexo: "H" para hombre, "M" para mujer
- domicilio: Calle y número completos. Ejemplo: "AV REFORMA 123 INT 4"
- colonia: Nombre de la colonia sin prefijo "COL" o "FRACC". Ejemplo: "CENTRO"
- codigoPostal: Código postal (5 dígitos). Ejemplo: "06600"
- municipio: Municipio o alcaldía. Ejemplo: "CUAUHTEMOC"
- estado: Estado (abreviatura o nombre completo). Ejemplo: "CDMX" o "DF"
- seccion: Sección electoral (4 dígitos). Ejemplo: "0901"
- vigencia: Año de vigencia (4 dígitos). Ejemplo: "2029"
- anioRegistro: Año de registro (4 dígitos). Ejemplo: "2019"
- emision: Año de emisión (4 dígitos). Ejemplo: "2019"
- estadoClave: Clave numérica del estado (2 dígitos) o null
- municipioClave: Clave numérica del municipio (3 dígitos) o null
- localidad: Clave de localidad (4 dígitos) o null

REGLAS:
1. Las palabras pegadas son comunes en OCR. "LAZAROCARDENAS" = "LAZARO CARDENAS", "BENITOJUAREZ" = "BENITO JUAREZ".
2. La CURP tiene exactamente 18 caracteres. Si ves algo parecido pero con errores (O vs 0, I vs 1), corrígelo solo si estás seguro.
3. La fecha de nacimiento aparece en el frente de la INE cerca de "FECHA DE NACIMIENTO" o se puede derivar de la CURP (posiciones 5-10: AAMMDD).
4. El sexo aparece cerca de "SEXO" en el frente, o en la CURP posición 11 (H o M).
5. El domicilio está en el frente, debajo de "DOMICILIO". Incluye calle, número exterior e interior.
6. El reverso contiene: CURP, clave de elector, sección, vigencia, año de registro, emisión, y la zona MRZ.
7. La zona MRZ (3 líneas con <<) contiene apellidos y nombres separados por <<. Ejemplo: "GARCIA<LOPEZ<<MARIA<GUADALUPE"
8. Si hay conflicto entre frente y reverso, el reverso (especialmente MRZ) es más confiable para nombres.

Responde ÚNICAMENTE con un JSON válido, sin explicaciones, sin markdown, sin backticks. Solo el JSON."""

_CURP_PATTERN = re.compile(r"^[A-ZÑ]{4}\d{6}[HM][A-ZÑ0-9]{7}$")


def _parse_ollama_json(content: str) -> dict[str, Any]:
    """Parsea JSON desde la respuesta del modelo, tolerando fences o texto alrededor."""
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()
    try:
        parsed: Any = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            LOGGER.warning("No se pudo extraer JSON de la respuesta de Ollama")
    return {}


def _curp_plausible(value: Any) -> bool:
    """Validación básica de formato CURP (18 caracteres alfanumérico típico)."""
    if not value or not isinstance(value, str):
        return False
    s = value.strip().upper()
    if len(s) != 18:
        return False
    return bool(_CURP_PATTERN.match(s))


class OllamaIneAnalyzer:
    """Usa Ollama para extraer datos de INE desde texto crudo de OCR."""

    def __init__(self) -> None:
        self._ollama = OllamaClient()

    async def analyze(self, raw_ocr_text: str) -> dict[str, Any]:
        """Envía el texto crudo del OCR a Ollama y retorna datos estructurados."""
        start = time.perf_counter()

        messages = [
            {"role": "system", "content": INE_EXTRACTION_PROMPT},
            {"role": "user", "content": f"Texto OCR de la INE:\n\n{raw_ocr_text}"},
        ]

        try:
            response = await self._ollama.chat(messages=messages, tools=None, stream=False)
            content = response.get("message", {}).get("content", "") or ""
            data = _parse_ollama_json(content)
            elapsed = int((time.perf_counter() - start) * 1000)

            non_null = sum(1 for v in data.values() if v is not None and v != "")
            LOGGER.info("Ollama INE análisis completado en %dms. Campos con valor: %d", elapsed, non_null)

            return {
                "data": data,
                "processing_time_ms": elapsed,
                "success": bool(data),
            }

        except Exception as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            LOGGER.exception("Error en análisis Ollama INE: %s", exc)
            return {
                "data": {},
                "processing_time_ms": elapsed,
                "success": False,
                "error": str(exc),
            }

    @staticmethod
    def merge_results(regex_data: dict[str, Any], ollama_data: dict[str, Any]) -> dict[str, Any]:
        """Merge: regex prioridad en patrones claros; Ollama rellena null; nombres/domicilio elige el más largo si ambos tienen valor."""
        merged: dict[str, Any] = {}

        regex_priority_fields = [
            "curp",
            "claveElector",
            "seccion",
            "vigencia",
            "anioRegistro",
            "emision",
            "estadoClave",
            "municipioClave",
            "localidad",
            "codigoPostal",
            "fechaNacimiento",
            "sexo",
        ]

        longest_wins_fields = [
            "nombre",
            "apellidoPaterno",
            "apellidoMaterno",
            "domicilio",
            "colonia",
            "municipio",
            "estado",
        ]

        def _truthy(val: Any) -> bool:
            return val is not None and val != ""

        for field in regex_priority_fields:
            regex_val = regex_data.get(field)
            ollama_val = ollama_data.get(field)
            if _truthy(regex_val):
                merged[field] = regex_val
            elif field == "curp" and _truthy(ollama_val):
                merged[field] = ollama_val if _curp_plausible(ollama_val) else None
            else:
                merged[field] = ollama_val if _truthy(ollama_val) else regex_val

        for field in longest_wins_fields:
            regex_val = regex_data.get(field)
            ollama_val = ollama_data.get(field)
            if _truthy(regex_val) and _truthy(ollama_val):
                merged[field] = (
                    regex_val if len(str(regex_val)) >= len(str(ollama_val)) else ollama_val
                )
            else:
                merged[field] = regex_val if _truthy(regex_val) else ollama_val

        merged["curpDerivado"] = regex_data.get("curpDerivado", False)
        merged["fuenteExtraccion"] = regex_data.get("fuenteExtraccion")

        return merged
