"""Normalización de menciones."""
import re
import unicodedata

TREATMENTS = re.compile(
    r"^(?:el|la|los|las)\s+"
    r"|(?:sr\.?|sra\.?|srta\.?|dr\.?|dra\.?|lic\.?|ing\.?|don|doña|señor|señora)\s+"
    r"|(?:imputad[oa]|víctima|victima|denunciante|testig[oa]|menor|niñ[oa])\s+",
    re.IGNORECASE,
)


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def normalize_text(s: str) -> str:
    s = s.lower().strip()
    s = strip_accents(s)
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_mention(surface: str) -> str:
    s = normalize_text(surface)
    s = TREATMENTS.sub("", s).strip()
    s = re.sub(r"[\.]", "", s)
    return s


def tokenize_name(s: str) -> list[str]:
    parts = re.split(r"\s+", s)
    skip = {"de", "del", "la", "las", "los", "y", "i"}
    return [p for p in parts if p and p not in skip]


def get_initials(tokens: list[str]) -> str:
    return "".join(t[0] for t in tokens if t)


def get_surnames(tokens: list[str]) -> set[str]:
    """Devuelve los tokens que probablemente son apellidos.

    En notación natural ("Alicia Carina Castro") el apellido está al final.
    En notación judicial ("CASTRO, ALICIA CARINA") está al principio. Para
    cubrir ambos casos usamos el diccionario de apellidos cuando está
    disponible y, si no hay match, devolvemos los dos extremos como
    candidatos (la intersección con otro mention sigue funcionando).
    """
    if len(tokens) <= 1:
        return set(tokens)
    try:
        from app.detection.dictionaries import get_apellidos

        apellidos = get_apellidos()
    except Exception:
        apellidos = set()
    matches = {t for t in tokens if t in apellidos}
    if matches:
        return matches
    if len(tokens) >= 2:
        return {tokens[0], tokens[-1]}
    return {tokens[-1]}
