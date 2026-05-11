from __future__ import annotations

import logging
import re
from typing import Any, Final

from .curp_deriver import CurpDeriver


LOGGER = logging.getLogger("[IneParser]")

JOINED_WORD_RULES: Final[list[tuple[str, str]]] = [
    (r"\bCURP([A-Z]{4}\d{6}[A-Z]{6,8}\d{1,2})\b", r"CURP \1"),
    (r"\bCLAVED?EELECTOR\s*([A-Z0-9]{16,20})\b", r"CLAVE DE ELECTOR \1"),
    (r"\bCAVEDEELECTOR\s*([A-Z0-9]{16,20})\b", r"CLAVE DE ELECTOR \1"),
    (r"\bCLAVEDEELECT0R([A-Z0-9]{16,20})\b", r"CLAVE DE ELECTOR \1"),
    (r"\bA[ÑN]ODE\s*REGISTRO\s*(\d{4})\s*(\d{2})", r"AÑO DE REGISTRO \1 \2"),
    (r"\bANODEREGISTRO\s*(\d{4})\s*(\d{2})", r"AÑO DE REGISTRO \1 \2"),
    (r"\bAFODEREGSTRO\s*(\d{4})", r"AÑO DE REGISTRO \1"),
    (r"\bEMISION(\d{4})VIGENCIA(\d{4})", r"EMISION \1 VIGENCIA \2"),
    (r"\bMUNICIPIO(\d{3})SECCION(\d{4})", r"MUNICIPIO \1 SECCION \2"),
    (r"\bESTADO(\d{2})\b", r"ESTADO \1"),
    (r"\bSECCION(\d{4})\b", r"SECCION \1"),
    (r"\bLOCALIDAD(\d{4})\b", r"LOCALIDAD \1"),
    (r"\bVIGENCIA(\d{4})", r"VIGENCIA \1"),
    (r"\bEMISION(\d{4})", r"EMISION \1"),
    (r"\bESTADODE([A-Z]{3,})", r"ESTADO DE \1"),
    (r"\bCIUDADDE([A-Z]{3,})", r"CIUDAD DE \1"),
    (r"\bPUEBLODE([A-Z]{3,})", r"PUEBLO DE \1"),
    (r"\bDE([A-Z]{4,})\b", r"DE \1"),
    (r"\bAV([A-Z]{2,})", r"AV \1"),
    (r"\bCOL([A-Z]{2,})", r"COL \1"),
    (r"\bFRACC([A-Z]{2,})", r"FRACC \1"),
    (r"\bUHAB([A-Z]{2,})", r"U HAB \1"),
    (r"\bCDEL([A-Z]{2,})", r"C DEL \1"),
    (r"\b([A-ZÑ]{5,})(\d{3})\b", r"\1 \2"),
]

KNOWN_REPLACEMENTS: Final[dict[str, str]] = {
    "LAZAROCARDENAS": "LAZARO CARDENAS",
    "BENITOJUAREZ": "BENITO JUAREZ",
    "EMILIANOZAPATA": "EMILIANO ZAPATA",
    "FRANCISCOVILLA": "FRANCISCO VILLA",
    "PORFIRIODIAZ": "PORFIRIO DIAZ",
    "JOSEFAORTIZ": "JOSEFA ORTIZ",
    "SANJUANDEARAGON": "SAN JUAN DE ARAGON",
    "GUSTAVOA": "GUSTAVO A",
    "DELAREFORMA": "DE LA REFORMA",
    "PASEODELA": "PASEO DE LA",
}

NAME_BLOCK_STOP: Final[re.Pattern[str]] = re.compile(
    r"^(SEXO|FECHA|DOMICI|D[oO]MIC|CLAVE|CURP|A[ÑN]O|ANO|SECCI|VIGENC|EMISI|ESTADO|MUNICIPIO|LOCALIDAD|INSTITUTO|CREDENCIAL|MEXICO|MÉXICO)",
    re.I,
)

OUTPUT_KEYS: Final[list[str]] = [
    "nombre",
    "apellidoPaterno",
    "apellidoMaterno",
    "curp",
    "curpDerivado",
    "claveElector",
    "fechaNacimiento",
    "sexo",
    "domicilio",
    "colonia",
    "codigoPostal",
    "municipio",
    "estado",
    "seccion",
    "vigencia",
    "anioRegistro",
    "emision",
    "estadoClave",
    "municipioClave",
    "localidad",
    "fuenteExtraccion",
]

class IneParser:
    def parse(self, combined_text: str) -> dict[str, Any]:
        preview = repr(combined_text[:800]) + ("..." if len(combined_text) > 800 else "")
        LOGGER.debug("TEXTO_CRUDO_INE (primeros 800 chars): %s", preview)

        mrz_data = self.detect_mrz(combined_text)
        LOGGER.info(
            "[IneParser] PASO 1 MRZ detectado: %s",
            "si" if mrz_data else "no",
        )

        if mrz_data and mrz_data.get("nombre"):
            frente_raw = combined_text.split("=== REVERSO ===")[0]
            mrz_data["nombre"] = self.complete_truncated(mrz_data["nombre"], frente_raw)

        cleaned = self.split_joined_words(combined_text.upper())
        ocr_data = self.extract_from_ocr(cleaned)
        nombres_frente = self.extract_nombres_from_frente(cleaned)
        LOGGER.info(
            "[IneParser] PASO 4 Nombres del frente: paterno=%s materno=%s nombres=%s",
            nombres_frente.get("apellidoPaterno"),
            nombres_frente.get("apellidoMaterno"),
            nombres_frente.get("nombre"),
        )

        domicilio_block = self.extract_domicilio(cleaned)

        curp_from_ocr = ocr_data.get("curp")
        curp_val = curp_from_ocr
        curp_derivado = False

        if not curp_val and mrz_data:
            derived = CurpDeriver.derive_curp(
                ap_pat=mrz_data.get("apellidoPaterno") or nombres_frente.get("apellidoPaterno"),
                ap_mat=mrz_data.get("apellidoMaterno") or nombres_frente.get("apellidoMaterno"),
                nombres=mrz_data.get("nombre") or nombres_frente.get("nombre"),
                fecha=mrz_data.get("fechaNacimiento") or ocr_data.get("fechaNacimiento"),
                sexo=mrz_data.get("sexo") or ocr_data.get("sexo"),
                clave_elector=ocr_data.get("claveElector"),
            )
            if derived:
                curp_val = derived
                curp_derivado = True

        LOGGER.info(
            "[IneParser] PASO 6 CURP derivado: %s",
            "si" if curp_derivado else "no",
        )

        ap_pat = (
            (mrz_data.get("apellidoPaterno") if mrz_data else None)
            or nombres_frente.get("apellidoPaterno")
            or ocr_data.get("apellidoPaterno")
        )
        ap_mat = (
            (mrz_data.get("apellidoMaterno") if mrz_data else None)
            or nombres_frente.get("apellidoMaterno")
            or ocr_data.get("apellidoMaterno")
        )
        nombre_val = (mrz_data.get("nombre") if mrz_data else None) or nombres_frente.get("nombre")

        fecha_final = None
        if mrz_data and mrz_data.get("fechaNacimiento"):
            fecha_final = mrz_data["fechaNacimiento"]
        elif ocr_data.get("fechaNacimiento"):
            fecha_final = ocr_data["fechaNacimiento"]

        sexo_final = None
        if mrz_data and mrz_data.get("sexo"):
            sexo_final = mrz_data["sexo"]
        elif ocr_data.get("sexo"):
            sexo_final = ocr_data["sexo"]

        seccion_final = None
        if mrz_data and mrz_data.get("seccion"):
            seccion_final = mrz_data["seccion"]
        elif ocr_data.get("seccion"):
            seccion_final = ocr_data["seccion"]

        vigencia_final = None
        if mrz_data and mrz_data.get("vigencia"):
            vigencia_final = mrz_data["vigencia"]
        elif ocr_data.get("vigencia"):
            vigencia_final = ocr_data["vigencia"]

        result: dict[str, Any] = {key: None for key in OUTPUT_KEYS}
        result["apellidoPaterno"] = ap_pat
        result["apellidoMaterno"] = ap_mat
        result["nombre"] = nombre_val
        result["curp"] = curp_val
        result["curpDerivado"] = curp_derivado
        result["claveElector"] = ocr_data.get("claveElector")
        result["fechaNacimiento"] = fecha_final
        result["sexo"] = sexo_final
        result["domicilio"] = domicilio_block.get("domicilio")
        result["colonia"] = domicilio_block.get("colonia")
        result["codigoPostal"] = domicilio_block.get("codigoPostal")
        result["municipio"] = domicilio_block.get("municipio")
        result["estado"] = domicilio_block.get("estado")
        result["seccion"] = seccion_final
        result["vigencia"] = vigencia_final
        result["anioRegistro"] = ocr_data.get("anioRegistro")
        result["emision"] = ocr_data.get("emision")
        result["estadoClave"] = ocr_data.get("estadoClave")
        result["municipioClave"] = ocr_data.get("municipioClave")
        result["localidad"] = ocr_data.get("localidad")

        if mrz_data:
            result["fuenteExtraccion"] = "MRZ"
        else:
            result["fuenteExtraccion"] = "OCR"

        if mrz_data and (ocr_data.get("curp") or ocr_data.get("claveElector")):
            result["fuenteExtraccion"] = "OCR_MIXTO"

        LOGGER.info(
            "parse INE: fuente=%s curp=%s",
            result.get("fuenteExtraccion"),
            result.get("curp"),
        )
        return result

    def split_joined_words(self, text: str) -> str:
        result = text
        for pattern, replacement in JOINED_WORD_RULES:
            result = re.sub(pattern, replacement, result)
        for key in sorted(KNOWN_REPLACEMENTS.keys(), key=len, reverse=True):
            result = result.replace(key, KNOWN_REPLACEMENTS[key])
        return result

    @staticmethod
    def is_truncado(nombres_mrz: str | None) -> bool:
        if not nombres_mrz:
            return False
        palabras = nombres_mrz.split()
        ultima = palabras[-1] if palabras else ""
        return 3 <= len(ultima) <= 6

    def complete_truncated(self, nombres_mrz: str | None, frente_text: str) -> str | None:
        if not nombres_mrz:
            return None
        if not self.is_truncado(nombres_mrz):
            return nombres_mrz
        frente_u = frente_text.upper()
        palabras = nombres_mrz.split()
        if not palabras:
            return nombres_mrz
        ultima = palabras[-1]
        m = re.search(re.escape(ultima) + r"([A-ZÁÉÍÓÚÑ]{2,})", frente_u)
        if m:
            palabras[-1] = ultima + m.group(1)
            return " ".join(palabras)
        return nombres_mrz

    def normalize_mrz_line(self, line: str) -> str:
        normalized = re.sub(r"^[B|bi:\s\.]+", "", line.strip())
        normalized = normalized.replace("(", "I").replace("|", "I")
        normalized = re.sub(r"\s+", "", normalized)
        normalized = re.sub(r"[^A-Z0-9<]", "", normalized.upper())
        return normalized

    def _yy_to_full_year(self, yy: int) -> int:
        return 1900 + yy if yy > 30 else 2000 + yy

    def _parse_mrz_line2(self, line: str) -> dict[str, str | None]:
        line_fix = line.replace("O", "0")
        if len(line_fix) < 10:
            return {"fechaNacimiento": None, "sexo": None, "vigencia": None}

        birth_raw = line_fix[0:6]
        sex = line_fix[7:8] if len(line_fix) > 7 else ""
        vig_raw = line_fix[8:10] if len(line_fix) > 9 else ""

        fecha = None
        if re.fullmatch(r"\d{6}", birth_raw):
            yy = int(birth_raw[0:2])
            mm = int(birth_raw[2:4])
            dd = int(birth_raw[4:6])
            if 1 <= mm <= 12 and 1 <= dd <= 31:
                fecha = f"{dd:02d}/{mm:02d}/{self._yy_to_full_year(yy)}"

        vigencia = f"20{vig_raw}" if re.fullmatch(r"\d{2}", vig_raw) else None
        sexo = sex if sex in {"H", "M"} else None
        return {"fechaNacimiento": fecha, "sexo": sexo, "vigencia": vigencia}

    def _line_is_mrz_line3(self, line: str) -> bool:
        if "<<" not in line:
            return False
        if line.startswith("IDMEX"):
            return False
        tail = line.split("<<", 1)[-1]
        if not tail:
            return False
        letters_tail = len(re.findall(r"[A-Z]", tail.replace("<", "")))
        return letters_tail >= 4

    def detect_mrz(self, text: str) -> dict[str, Any] | None:
        normalized_lines: list[str] = []
        for raw_line in text.splitlines():
            norm = self.normalize_mrz_line(raw_line)
            if norm:
                normalized_lines.append(norm)

        line1 = next((ln for ln in normalized_lines if ln.startswith("IDMEX") and len(ln) >= 15), None)

        line3 = next((ln for ln in normalized_lines if self._line_is_mrz_line3(ln)), None)

        line2 = None
        for ln in normalized_lines:
            if ln == line1 or ln == line3:
                continue
            candidate = ln.replace("O", "0")
            if re.search(r"\d{6}\d?[HM]\d{6}", candidate):
                line2 = ln
                break

        if not (line1 and line2 and line3):
            LOGGER.debug(
                "MRZ líneas incompletas: L1=%s L2=%s L3=%s",
                line1 is not None,
                line2 is not None,
                line3 is not None,
            )
            return None

        section: str | None = None
        if len(line1) >= 21:
            cand_sec = line1[17:21]
            if re.fullmatch(r"\d{4}", cand_sec):
                section = cand_sec

        line2_data = self._parse_mrz_line2(line2)

        parts_all = line3.split("<<")
        ap_pat: str | None = None
        ap_mat: str | None = None
        nombres: str | None = None
        if len(parts_all) >= 2:
            ap_part = parts_all[0]
            nom_part = "<<".join(parts_all[1:])
            ap_parts = [x for x in ap_part.split("<") if x]
            ap_pat = ap_parts[0] if len(ap_parts) > 0 else None
            ap_mat = ap_parts[1] if len(ap_parts) > 1 else None
            nom_parts = [x for x in nom_part.split("<") if x]
            nombres = " ".join(nom_parts).strip() if nom_parts else None

        return {
            "apellidoPaterno": ap_pat,
            "apellidoMaterno": ap_mat,
            "nombre": nombres,
            "seccion": section,
            "fechaNacimiento": line2_data["fechaNacimiento"],
            "sexo": line2_data["sexo"],
            "vigencia": line2_data["vigencia"],
        }

    def _extract_front_section(self, text: str) -> str:
        front_match = re.search(r"=== FRENTE ===\n(.*?)(?:\n=== REVERSO ===|\Z)", text, flags=re.DOTALL)
        return front_match.group(1) if front_match else text

    def extract_nombres_from_frente(self, cleaned_upper: str) -> dict[str, str | None]:
        frente_section = cleaned_upper.split("=== REVERSO ===")[0]
        lines = frente_section.split("\n")
        idx_nombre: int | None = None
        for i, line in enumerate(lines):
            if line.strip().upper() == "NOMBRE":
                idx_nombre = i
                break
        if idx_nombre is None:
            return {"apellidoPaterno": None, "apellidoMaterno": None, "nombre": None}

        validas: list[str] = []
        for raw_line in lines[idx_nombre + 1 :]:
            line = raw_line.strip()
            if not line:
                continue
            if NAME_BLOCK_STOP.match(line):
                continue
            if not re.search(r"[A-ZÁÉÍÓÚÑ]{3,}", line):
                continue
            validas.append(line)
            if len(validas) >= 3:
                break

        return {
            "apellidoPaterno": validas[0] if len(validas) > 0 else None,
            "apellidoMaterno": validas[1] if len(validas) > 1 else None,
            "nombre": validas[2] if len(validas) > 2 else None,
        }

    @staticmethod
    def find_curp(text: str) -> str | None:
        u = text.upper()
        m = re.search(r"CURP\s*([A-Z]{4}\d{6}[A-Z]{6,8}\d{1,2})", u)
        if m:
            cand = m.group(1)
            normalized = cand[:4] + cand[4:10].replace("O", "0") + cand[10:]
            if re.match(r"^[A-Z]{4}\d{6}[A-Z]{6}\d{2}$", normalized):
                return normalized
        candidates = re.findall(r"\b([A-Z]{4}\d{6}[A-Z]{6,8}\d{1,2})\b", u)
        for c in candidates:
            normalized = c[:4] + c[4:10].replace("O", "0") + c[10:]
            if re.match(r"^[A-Z]{4}\d{6}[A-Z]{6}\d{2}$", normalized):
                return normalized
        return None

    def _match_group(self, text: str, pattern: str, group: int = 1) -> str | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return None
        return match.group(group).strip()

    def extract_from_ocr(self, text: str) -> dict[str, Any]:
        front = self._extract_front_section(text)
        back_match = re.search(r"=== REVERSO ===\n(.*)$", text, flags=re.DOTALL)
        back = back_match.group(1) if back_match else text
        full_text = text

        curp = self.find_curp(full_text)
        clave = self._match_group(full_text, r"CLAVE\s+DE\s+ELECTOR\s+([A-Z0-9]{16,20})\b")
        if clave is None:
            clave = self._match_group(full_text, r"CLAVE\s*DE\s*ELECTOR\s*([A-Z0-9]{16,20})\b")

        fecha_m = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", front)
        fecha = fecha_m.group(1) if fecha_m else None
        if fecha is None:
            fecha_m2 = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", full_text)
            fecha = fecha_m2.group(1) if fecha_m2 else None

        sexo = self._match_group(front, r"\bSEXO\s*[:\s]*([HM])\b")
        cp = self._match_group(front, r"\bC\.?\s*P\.?\s*(\d{5})\b")
        if cp is None:
            cp = self._match_group(front, r"\b(\d{5})\b")

        seccion = self._match_group(back, r"SECCI[OÓ]N\s+(\d{4})")
        if seccion is None:
            seccion = self._match_group(back, r"SECCION\s+(\d{4})")

        vigencia = self._match_group(back, r"VIGENCIA\s+\d{4}\s*[-–]?\s*(\d{4})")
        if vigencia is None:
            vm = re.search(r"\b(\d{4})\s*[-–]\s*(\d{4})\b", back)
            if vm:
                vigencia = vm.group(2)
        if vigencia is None:
            vigencia = self._match_group(back, r"VIGENCIA\s+(\d{4})")

        emision = self._match_group(back, r"EMISION\s+(\d{4})")
        anio_reg = self._match_group(back, r"A[ÑN]O\s+DE\s+REGISTRO\s+(\d{4})")
        estado_clave = self._match_group(back, r"ESTADO\s+(\d{2})\b")
        municipio_clave = self._match_group(back, r"MUNICIPIO\s+(\d{3})\b")
        localidad = self._match_group(back, r"LOCALIDAD\s+(\d{4})\b")

        return {
            "nombre": None,
            "apellidoPaterno": None,
            "apellidoMaterno": None,
            "curp": curp,
            "claveElector": clave,
            "fechaNacimiento": fecha,
            "sexo": sexo,
            "codigoPostal": cp,
            "municipio": None,
            "estado": None,
            "seccion": seccion,
            "vigencia": vigencia,
            "anioRegistro": anio_reg,
            "emision": emision,
            "estadoClave": estado_clave,
            "municipioClave": municipio_clave,
            "localidad": localidad,
        }

    def _normalize_municipio_parts(self, parts: list[str]) -> str:
        inner = " ".join(p.strip() for p in parts if p.strip())
        inner = re.sub(r"\s+", " ", inner)
        return inner.strip()

    def extract_domicilio(self, text: str) -> dict[str, Any]:
        front = self._extract_front_section(text)
        lines = [re.sub(r"\s+", " ", line).strip() for line in front.splitlines() if line.strip()]

        domicilio = None
        colonia = None
        codigo_postal = None
        municipio = None
        estado = None

        for idx, line in enumerate(lines):
            if re.search(r"\b(DOMICILIO|ADDRESS)\b", line, re.I):
                nxt = lines[idx + 1] if idx + 1 < len(lines) else None
                if nxt and re.search(r"\d", nxt):
                    domicilio = nxt

        if domicilio is None:
            for line in lines:
                if re.search(r"\b(C DEL|CALLE|AV\s|AVENIDA|FRACC|U HAB)\b", line) and re.search(r"\d", line):
                    domicilio = line
                    break

        for line in lines:
            u = line.upper().strip()
            if re.match(
                r"^(COL\s|COLONIA\s|FRACC\s|U HAB\s|BARRIO\s|PRIV\s)",
                u,
            ):
                colonia = re.sub(r"\s+\d{5}.*$", "", line).strip()

        cp_m = re.search(r"\b(\d{5})\b", front)
        if cp_m:
            codigo_postal = cp_m.group(1)

        dom_idx = next((i for i, ln in enumerate(lines) if domicilio and ln == domicilio), -1)
        search_from = dom_idx + 1 if dom_idx >= 0 else 0
        for j in range(search_from, len(lines)):
            ln = lines[j]
            if colonia and ln == colonia:
                continue
            mu, est = self._parse_municipio_estado_line(ln)
            if est:
                municipio, estado = mu, est
                break

        return {
            "domicilio": domicilio,
            "colonia": self._strip_colonia_prefix(colonia),
            "codigoPostal": codigo_postal,
            "municipio": municipio,
            "estado": estado,
        }

    @staticmethod
    def _strip_colonia_prefix(colonia: str | None) -> str | None:
        if not colonia:
            return colonia
        s = colonia.strip()
        upper = s.upper()
        for pref in ("COLONIA ", "COL ", "FRACC ", "U HAB ", "BARRIO ", "PRIV "):
            if upper.startswith(pref):
                return s[len(pref) :].strip()
        return s

    def _parse_municipio_estado_line(self, line: str) -> tuple[str | None, str | None]:
        s = line.strip()
        if "." in s:
            parts = [p.strip() for p in s.split(".") if p.strip()]
            if len(parts) >= 2:
                estado = parts[-1].upper()
                if re.fullmatch(r"[A-Z]{2,5}", estado):
                    municipio = self._normalize_municipio_parts(parts[:-1])
                    return municipio, estado
        m = re.match(r"^([A-ZÁÉÍÓÚÑ0-9\s]+)[,.]\s*([A-Z]{2,5})\.?$", s.upper())
        if m:
            mun = re.sub(r"\s+", " ", m.group(1).strip())
            est = m.group(2).strip()
            return mun, est
        return None, None
