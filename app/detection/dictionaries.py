"""Carga de diccionarios de nombres y apellidos."""
import json

from app.config import DATA_DIR, RESOURCE_DATA_DIR

_nombres: set[str] | None = None
_apellidos: set[str] | None = None


def _load_json(name: str) -> set[str]:
    # Buscar primero en los recursos embebidos (BUNDLE_DIR/_internal en el .exe)
    # y luego junto al ejecutable, por si se agregan diccionarios personalizados.
    for base in (RESOURCE_DATA_DIR, DATA_DIR):
        path = base / "dictionaries" / name
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return set(json.load(f))
    return set()


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
