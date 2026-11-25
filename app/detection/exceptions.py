"""Términos que la detección automática nunca anonimiza.

La lista vive en ``data/dictionaries/no_anonimizar.json``: una expresión por
entrada, sin distinguir mayúsculas ni acentos. Se aplica al final de todas las
capas (regex, catálogos, Presidio, spaCy y alias del documento):

- si una detección es el término (o queda dentro de él), se descarta;
- si el término está pegado a otro dato («Juan Pérez Conexidad Subjetiva»),
  se recorta y se conserva el resto cuando sigue siendo un dato válido.

La selección manual del usuario no pasa por esta lista.
"""
import json
import logging
import re
from functools import lru_cache

from app.detection.dictionaries import catalog_paths
from app.detection.regex_ar import RawItem

logger = logging.getLogger(__name__)

CATALOG = "no_anonimizar.json"
_EDGE = " \t\r\n ,.;:-–—/|()[]\"'"
_ACCENTS = {
    "a": "aáàäâ", "e": "eéèëê", "i": "iíìïî", "o": "oóòöô", "u": "uúùüû", "n": "nñ",
}


def _char_class(char: str) -> str:
    variants = _ACCENTS.get(char.lower())
    return f"[{variants}]" if variants else re.escape(char)


def _phrase_pattern(phrase: str) -> str:
    words = phrase.split()
    return r"\s+".join("".join(_char_class(c) for c in word) for word in words)


@lru_cache(maxsize=1)
def exception_pattern() -> re.Pattern[str] | None:
    phrases: list[str] = []
    for path in catalog_paths(CATALOG):
        try:
            with path.open(encoding="utf-8-sig") as stream:
                values = json.load(stream)
        except (OSError, UnicodeError, json.JSONDecodeError):
            logger.warning("No se pudo leer %s; se ignora", path)
            continue
        if isinstance(values, list):
            phrases.extend(v.strip() for v in values if isinstance(v, str) and v.strip())
    phrases = sorted(dict.fromkeys(p.lower() for p in phrases), key=len, reverse=True)
    if not phrases:
        return None
    body = "|".join(_phrase_pattern(p) for p in phrases)
    return re.compile(rf"(?<!\w)(?:{body})(?!\w)", re.IGNORECASE)


def exception_spans(text: str) -> list[tuple[int, int]]:
    pattern = exception_pattern()
    return [(m.start(), m.end()) for m in pattern.finditer(text)] if pattern else []


def _remaining_segments(start: int, end: int, blocked: list[tuple[int, int]]) -> list[tuple[int, int]]:
    segments, cursor = [], start
    for b_start, b_end in blocked:
        if b_end <= cursor or b_start >= end:
            continue
        if b_start > cursor:
            segments.append((cursor, b_start))
        cursor = max(cursor, b_end)
    if cursor < end:
        segments.append((cursor, end))
    return segments


def apply_exceptions(items: list[RawItem], text: str) -> list[RawItem]:
    """Quita o recorta las detecciones que tocan un término exceptuado."""
    spans = exception_spans(text)
    if not spans:
        return items
    from app.detection.filters import is_valid_detection

    out: list[RawItem] = []
    for item in items:
        blocked = [(s, e) for s, e in spans if s < item.end and e > item.start]
        if not blocked:
            out.append(item)
            continue
        best = None
        for seg_start, seg_end in _remaining_segments(item.start, item.end, blocked):
            raw = text[seg_start:seg_end]
            left = len(raw) - len(raw.lstrip(_EDGE))
            value = raw.strip(_EDGE)
            if len(value) < 2:
                continue
            candidate = RawItem(item.cat, value, seg_start + left, seg_start + left + len(value),
                                item.source_layer)
            if best is None or len(value) > len(best.original):
                best = candidate
        if best and is_valid_detection(best.cat, best.original, text, best.start):
            out.append(best)
    return out
