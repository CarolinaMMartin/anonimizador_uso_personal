"""Carga de diccionarios de nombres y apellidos."""
import json
import logging
import re
from functools import lru_cache
from pathlib import Path

from app.config import DATA_DIR, RESOURCE_DATA_DIR
from app.resolution.normalize import normalize_text

logger = logging.getLogger(__name__)

_nombres: set[str] | None = None
_apellidos: set[str] | None = None
NAME_PARTICLES = frozenset({"de", "del", "la", "las", "los", "y", "e", "da", "das", "do", "dos", "van", "von", "der", "den", "ten", "ter"})


class CatalogLoadError(ValueError):
    """Un recurso obligatorio de detección falta o está dañado."""


def catalog_paths(name: str) -> tuple[Path, ...]:
    return tuple(dict.fromkeys(
        path.resolve() for base in (RESOURCE_DATA_DIR, DATA_DIR)
        if (path := base / "dictionaries" / name).is_file()
    ))


def _load_json(name: str) -> set[str]:
    paths = catalog_paths(name)
    if not paths:
        raise CatalogLoadError(f"Catálogo de personas no encontrado: {name}")
    merged: set[str] = set()
    for path in paths:
        try:
            with path.open(encoding="utf-8-sig") as stream:
                values = json.load(stream)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CatalogLoadError(f"No se pudo leer el catálogo: {name}") from exc
        if (not isinstance(values, list) or not values
                or not all(isinstance(value, str) and value.strip() for value in values)):
            raise CatalogLoadError(f"Catálogo inválido: {name}")
        merged.update(normalize_text(value) for value in values)
    logger.info("Catálogo %s cargado: %d entradas de %d archivo(s)", name, len(merged), len(paths))
    return merged


def get_nombres() -> set[str]:
    global _nombres
    if _nombres is None:
        _nombres = _load_json("nombres.json")
    return _nombres


def get_apellidos() -> set[str]:
    global _apellidos
    if _apellidos is None:
        _apellidos = _load_json("apellidos.json")
    return _apellidos


@lru_cache(maxsize=4)
def _catalog_words(values: frozenset[str]) -> frozenset[str]:
    words = {word for value in values for word in re.findall(r"[^\W\d_]+(?:[-'’ʼ][^\W\d_]+)*", value)}
    return frozenset(words - NAME_PARTICLES)


def get_person_anchors() -> tuple[frozenset[str], frozenset[str]]:
    return _catalog_words(frozenset(get_nombres())), _catalog_words(frozenset(get_apellidos()))


STOPWORDS_FRASE = {
    "el", "la", "los", "las", "un", "una", "y", "o", "de", "del", "que", "con",
    "por", "para", "en", "su", "sus", "se", "no", "si", "pero", "este", "esta",
    "tribunal", "supremo", "corte", "juzgado", "juzgados", "fiscalia", "fiscalía",
    "defensoria", "defensoría", "ministerio", "camara", "cámara", "sala", "articulo",
    "artículo", "codigo", "código", "ley", "decreto", "resolucion", "resolución",
    "sentencia", "auto", "providencia", "disposicion", "disposición", "nacion",
    "nación", "provincia", "provincial", "nacional", "federal", "capital",
    "buenos", "aires", "cordoba", "córdoba", "mendoza", "santa", "fe", "rosario",
    "según", "segun", "conforme", "mediante", "donde", "cuando", "como", "cual",
    "quien", "quienes", "cuyo", "cuya", "sr", "sra", "srta", "dr", "dra",
}

SUFIJOS_EMPRESA = (
    r"(?:"
    # Formas clásicas con/ sin puntos: S.A., S.R.L., S.A.S., S.A.U., S.C., S.C.A., S.H.
    r"S\.?\s?A\.?|S\.?\s?R\.?\s?L\.?|S\.?\s?A\.?\s?S\.?|S\.?\s?A\.?\s?U\.?"
    r"|S\.?\s?C\.?|S\.?\s?C\.?\s?A\.?|S\.?\s?H\.?"
    # Razones sociales argentinas compuestas (SACI / SAIC / SACIF / SACIFI /
    # SACIFIA / SAICF / SAICFI / SAICFA), con o sin puntos intermedios.
    r"|S\.?A\.?C\.?I\.?F\.?I\.?A\.?|S\.?A\.?I\.?C\.?F\.?I\.?A\.?"
    r"|S\.?A\.?C\.?I\.?F\.?I\.?|S\.?A\.?I\.?C\.?F\.?I\.?"
    r"|S\.?A\.?C\.?I\.?F\.?|S\.?A\.?I\.?C\.?F\.?"
    r"|S\.?A\.?C\.?I\.?|S\.?A\.?I\.?C\.?"
    # Cooperativas y mutuales.
    r"|Cooperativa|Coop\.?|Mutual|Asociaci[oó]n\s+Civil|Fundaci[oó]n"
    r")"
)
