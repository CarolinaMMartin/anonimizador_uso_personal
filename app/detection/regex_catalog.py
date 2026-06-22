"""Catálogo externo de regex judiciales (Regex_limpio_v2.json)."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache

from app.config import DATA_DIR, RESOURCE_DATA_DIR
from app.detection.regex_ar import RawItem, validate_cuit, validate_dni

logger = logging.getLogger(__name__)

ENTITY_TO_CAT: dict[str, str] = {
    "RGX_CARATULA": "PERSONA",
    "RGX_PERSONA_ROL": "PERSONA",
    "RGX_LUGAR": "EMPRESA",
    "RGX_DOMICILIO": "DOMICILIO",
    "RGX_EXPEDIENTE": "EXPEDIENTE",
    "RGX_DNI": "DNI",
    "RGX_PASAPORTE": "DNI",
    "RGX_CUIL_CUIT": "CUIT",
    "RGX_CBU": "OTRO",
    "RGX_CUENTA_BANC": "OTRO",
    "RGX_CUENTA_BANCARIA": "OTRO",
    "RGX_TERMINACION_TARJETA": "OTRO",
    "RGX_CHEQUE": "OTRO",
    "RGX_URL": "OTRO",
    "RGX_EMAIL": "EMAIL",
    "RGX_TELEFONO": "TELEFONO",
    "RGX_PATENTE": "PATENTE",
    "RGX_IP": "OTRO",
}

# Patrones demasiado amplios, redundantes con el motor actual, o con backtracking lento.
_SKIP_DESCRIPTION_MARKERS = (
    "desnudo",
    "desnudos",
    "nombres propios desnudos",
    "aspiradora de numeros sueltos",
    "nacionalidad",
    "direcciones ipv4",
    "domicilios contextuales",
)

_CARATULA_SPLIT_RE = re.compile(r"\s+(?:c\s*\.?/|contra)\s+", re.IGNORECASE)


@dataclass(frozen=True)
class CatalogPattern:
    name: str
    cat: str
    regex: re.Pattern[str]
    score: float
    description: str
    special: str | None = None  # "caratula" | "firma"


def _catalog_path() -> str | None:
    for base in (RESOURCE_DATA_DIR, DATA_DIR):
        path = base / "dictionaries" / "regex_limpio_v2.json"
        if path.exists():
            return str(path)
    return None


def _should_skip(entry: dict) -> bool:
    if not entry.get("activa", True):
        return True
    desc = (entry.get("descripcion") or "").lower()
    return any(marker in desc for marker in _SKIP_DESCRIPTION_MARKERS)


def _special_handler(entry: dict) -> str | None:
    name = entry.get("nombre_entidad", "")
    desc = (entry.get("descripcion") or "").lower()
    if name == "RGX_CARATULA":
        return "caratula"
    if name == "RGX_PERSONA_ROL" and "firma" in desc:
        return "firma"
    return None


@lru_cache(maxsize=1)
def load_catalog_patterns() -> tuple[CatalogPattern, ...]:
    path = _catalog_path()
    if not path:
        logger.debug("Catálogo regex_limpio_v2.json no encontrado")
        return ()

    try:
        with open(path, encoding="utf-8") as f:
            entries = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("No se pudo cargar %s: %s", path, e)
        return ()

    patterns: list[CatalogPattern] = []
    for entry in entries:
        if _should_skip(entry):
            continue
        entity = entry.get("nombre_entidad", "")
        cat = ENTITY_TO_CAT.get(entity)
        if not cat:
            continue
        raw = entry.get("regex")
        if not raw:
            continue
        try:
            compiled = re.compile(raw)
        except re.error as e:
            logger.warning("Regex inválida (%s): %s", entity, e)
            continue
        patterns.append(
            CatalogPattern(
                name=entity,
                cat=cat,
                regex=compiled,
                score=float(entry.get("score") or 0.8),
                description=entry.get("descripcion") or "",
                special=_special_handler(entry),
            )
        )

    # Mayor score primero dentro de cada categoría sensible.
    patterns.sort(key=lambda p: (-p.score, p.name))
    return tuple(patterns)


def _match_surface(match: re.Match[str]) -> tuple[str, int, int]:
    if match.lastindex and match.lastindex >= 1:
        for i in range(1, match.lastindex + 1):
            val = match.group(i)
            if val and val.strip():
                start = match.start(i)
                end = match.end(i)
                return val.strip(), start, end
    val = match.group(0).strip()
    return val, match.start(), match.end()


def _caratula_parties(match: re.Match[str]) -> list[tuple[str, int, int]]:
    full, base_start, _ = _match_surface(match)
    split = _CARATULA_SPLIT_RE.search(full)
    if not split:
        val = full.strip(" \"'.,;")
        if len(val) < 3:
            return []
        lead = full.find(val)
        start = base_start + max(lead, 0)
        return [(val, start, start + len(val))]

    spans: list[tuple[str, int, int]] = []
    actor_raw = full[: split.start()]
    demandado_raw = full[split.end() :]
    for raw, offset in ((actor_raw, 0), (demandado_raw, split.end())):
        val = raw.strip(" \"'.,;")
        if len(val) < 3:
            continue
        lead = raw.find(val)
        start = base_start + offset + max(lead, 0)
        spans.append((val, start, start + len(val)))
    return spans


def _normalize_ocr_digits(value: str) -> str:
    return value.replace("O", "0").replace("o", "0")


def _validate_catalog_match(cat: str, surface: str) -> bool:
    if cat == "CUIT":
        return validate_cuit(_normalize_ocr_digits(surface))
    if cat == "DNI":
        return validate_dni(_normalize_ocr_digits(surface))
    if cat == "TELEFONO":
        digits = re.sub(r"\D", "", surface)
        return 10 <= len(digits) <= 15
    if cat == "PATENTE":
        # Re-uso del filtro general para descartar "Ley 471", "Art 123", etc.
        from app.detection.filters import _is_valid_patente

        return _is_valid_patente(surface)
    return True


def detect_regex_catalog(text: str) -> list[RawItem]:
    """Aplica el catálogo Regex_limpio_v2 sobre el texto."""
    items: list[RawItem] = []
    seen: set[tuple[int, int, str]] = set()

    for pattern in load_catalog_patterns():
        for match in pattern.regex.finditer(text):
            if pattern.special == "caratula":
                spans = _caratula_parties(match)
            else:
                surface, start, end = _match_surface(match)
                spans = [(surface, start, end)]

            for surface, start, end in spans:
                if not surface or end <= start:
                    continue
                if not _validate_catalog_match(pattern.cat, surface):
                    continue
                key = (start, end, pattern.cat)
                if key in seen:
                    continue
                seen.add(key)
                items.append(
                    RawItem(
                        cat=pattern.cat,
                        original=surface,
                        start=start,
                        end=end,
                        source_layer="regex_v2",
                    )
                )

    return items
