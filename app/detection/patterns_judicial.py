"""Patrones judiciales adicionales (spaCy EntityRuler en MVP2)."""
import re
from app.detection.regex_ar import RawItem


JUDICIAL_ROLE_PATTERNS = [
    r"\bel\s+imputado\b",
    r"\bla\s+imputada\b",
    r"\bla\s+víctima\b",
    r"\bla\s+victima\b",
    r"\bel\s+denunciante\b",
    r"\bla\s+denunciante\b",
    r"\bel\s+testigo\b",
    r"\bla\s+testigo\b",
    r"\bel\s+menor\b",
    r"\bla\s+niña\b",
    r"\bel\s+adolescente\b",
]


def detect_role_phrases(text: str) -> list[RawItem]:
    """Detecta frases de rol sin nombre explícito (para contexto)."""
    items: list[RawItem] = []
    for pat in JUDICIAL_ROLE_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            items.append(
                RawItem(
                    cat="OTRO",
                    original=m.group(0),
                    start=m.start(),
                    end=m.end(),
                    source_layer="ruler",
                )
            )
    return items
