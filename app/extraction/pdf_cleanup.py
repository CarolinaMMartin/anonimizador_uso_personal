"""Limpieza de texto extraído de PDF (sin OCR)."""
from __future__ import annotations

import re
from unicodedata import normalize

# Pie de página típico: "1 | Página" con letras espaciadas por el PDF.
_PAGE_FOOTER_RE = re.compile(
    r"^[ \t]*\d+[ \t]*\|[ \t]*p[ \t]*[aá][ \t]*g[ \t]*i[ \t]*n[ \t]*a[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)

# Línea suelta con solo un número de página.
_LONE_PAGE_NUM_RE = re.compile(r"^\s*\d{1,4}\s*$", re.MULTILINE)


def clean_pdf_text(text: str) -> str:
    """Quita ruido de paginación y normaliza saltos de línea."""
    # Compose canonically equivalent letters before computing detection offsets.
    text = normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = _PAGE_FOOTER_RE.sub("", text)
    text = _LONE_PAGE_NUM_RE.sub("", text)
    # Colapsar muchas líneas vacías consecutivas.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def merge_lines_to_paragraphs(text: str) -> str:
    """Une líneas partidas del PDF en párrafos (mejora export Word/PDF).

    Muchos PDFs judiciales insertan una línea vacía entre cada renglón visual;
    primero se ignoran esas líneas vacías y luego se fusionan continuaciones.
    """
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    paragraphs: list[str] = []
    current = ""

    for line in lines:
        if not current:
            current = line
            continue

        if _line_continues(current, line):
            current = f"{current} {line}"
        else:
            paragraphs.append(current.strip())
            current = line

    if current:
        paragraphs.append(current.strip())

    return "\n\n".join(paragraphs)


def _line_continues(previous: str, nxt: str) -> bool:
    """Heurística: la línea siguiente sigue el mismo párrafo."""
    if re.match(r"^[\d\-•·–—]\s", nxt):
        return False
    if previous.endswith("-"):
        return True
    if previous.rstrip().endswith((",", ";", ":")):
        return True
    if previous.rstrip()[-1] not in ".!?":
        if nxt[0].islower() or nxt[0] in "([\"'":
            return True
    return False
