from __future__ import annotations

import logging
import re
from typing import Final


LOGGER = logging.getLogger("[CurpDeriver]")

ESTADOS: Final[dict[str, str]] = {
    "01": "AS",
    "02": "BC",
    "03": "BS",
    "04": "CC",
    "05": "CL",
    "06": "CM",
    "07": "CS",
    "08": "CH",
    "09": "DF",
    "10": "DG",
    "11": "GT",
    "12": "GR",
    "13": "HG",
    "14": "JC",
    "15": "MC",
    "16": "MN",
    "17": "MS",
    "18": "NT",
    "19": "NL",
    "20": "OC",
    "21": "PL",
    "22": "QT",
    "23": "QR",
    "24": "SP",
    "25": "SL",
    "26": "SR",
    "27": "TC",
    "28": "TS",
    "29": "TL",
    "30": "VZ",
    "31": "YN",
    "32": "ZS",
}

STOP_WORDS: Final[set[str]] = {
    "DE",
    "LA",
    "EL",
    "DEL",
    "LOS",
    "LAS",
    "Y",
    "MC",
    "MAC",
    "VAN",
    "VON",
}

VOWELS: Final[set[str]] = {"A", "E", "I", "O", "U"}


class CurpDeriver:
    @staticmethod
    def _normalize_token(token: str | None) -> str:
        if not token:
            return ""
        cleaned = re.sub(r"[^A-Z ]", "", token.upper())
        parts = [part for part in cleaned.split() if part and part not in STOP_WORDS]
        return " ".join(parts).strip()

    @staticmethod
    def _first_internal_vowel(value: str) -> str:
        for char in value[1:]:
            if char in VOWELS:
                return char
        return "X"

    @staticmethod
    def _first_internal_consonant(value: str) -> str:
        for char in value[1:]:
            if char.isalpha() and char not in VOWELS:
                return char
        return "X"

    @staticmethod
    def _first_letter(value: str) -> str:
        for char in value:
            if char.isalpha():
                return char
        return "X"

    @staticmethod
    def _fecha_to_yymmdd(fecha: str) -> str | None:
        match = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", fecha)
        if not match:
            return None
        dd, mm, yyyy = match.groups()
        return f"{yyyy[-2:]}{mm}{dd}"

    @classmethod
    def derive_curp(
        cls,
        ap_pat: str | None,
        ap_mat: str | None,
        nombres: str | None,
        fecha: str | None,
        sexo: str | None,
        clave_elector: str | None,
    ) -> str | None:
        if not all([ap_pat, ap_mat, nombres, fecha, sexo, clave_elector]):
            return None

        clave_clean = re.sub(r"[^A-Z0-9]", "", str(clave_elector).upper())
        if len(clave_clean) < 14:
            return None

        estado_code = clave_clean[12:14]
        estado = ESTADOS.get(estado_code)
        if not estado:
            LOGGER.info("No se pudo mapear estado para clave %s", estado_code)
            return None

        ap_pat_norm = cls._normalize_token(ap_pat)
        ap_mat_norm = cls._normalize_token(ap_mat)
        nombres_norm = cls._normalize_token(nombres)
        if not ap_pat_norm or not ap_mat_norm or not nombres_norm:
            return None

        first_name = nombres_norm.split()[0]
        yymmdd = cls._fecha_to_yymmdd(str(fecha))
        if yymmdd is None:
            return None

        sexo_norm = str(sexo).upper()[:1]
        if sexo_norm not in {"H", "M"}:
            sexo_norm = "X"

        curp16 = (
            f"{cls._first_letter(ap_pat_norm)}"
            f"{cls._first_internal_vowel(ap_pat_norm)}"
            f"{cls._first_letter(ap_mat_norm)}"
            f"{cls._first_letter(first_name)}"
            f"{yymmdd}"
            f"{sexo_norm}"
            f"{estado}"
            f"{cls._first_internal_consonant(ap_pat_norm)}"
            f"{cls._first_internal_consonant(ap_mat_norm)}"
            f"{cls._first_internal_consonant(first_name)}"
        )
        return f"{curp16}??"
