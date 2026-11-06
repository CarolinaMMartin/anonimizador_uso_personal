"""Claves exactas para identificadores que no admiten similitud difusa."""
import re


IDENTIFIER_CATEGORIES = frozenset({
    "DNI", "CUIT", "TELEFONO", "PATENTE", "EXPEDIENTE", "EMAIL", "OTRO",
})


def identifier_key(category: str, surface: str) -> str:
    value = surface.strip()
    if category in {"DNI", "CUIT", "TELEFONO", "PATENTE"}:
        return re.sub(r"[\s.()\-]", "", value).upper()
    return value
