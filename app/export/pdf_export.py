"""Exportación a PDF con ReportLab."""
from __future__ import annotations

import io
import re
from functools import lru_cache
from unicodedata import combining, name, normalize
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer

from app.runtime_paths import bundle_dir
from app.export.docx_format import DEFAULT_DOCX_FORMAT, DocxExportFormat

_ALIGN_MAP = {
    "left": TA_LEFT,
    "justify": TA_JUSTIFY,
    "center": TA_CENTER,
    "right": TA_RIGHT,
}


# Keep a base letter and its diacritical marks in the same font run.
_WORD = re.compile(r"(?:[^\W\d_]|[\u0300-\u036f])+")


class UnsupportedPdfLetter(ValueError):
    pass


@lru_cache(maxsize=1)
def _latin_font() -> TTFont:
    font = TTFont("IALAB-Roboto", str(bundle_dir() / "frontend/assets/fonts/Roboto.ttf"))
    pdfmetrics.registerFont(font)
    return font


def _format_word(match: re.Match[str]) -> str:
    word = match.group()
    if not any(ord(c) > 255 and (name(c, "").startswith("LATIN ") or combining(c)) for c in word):
        return word
    font = _latin_font()
    if any(not font.face.charToGlyph.get(ord(c)) for c in word):
        raise UnsupportedPdfLetter("La fuente del PDF no puede representar una letra del texto. "
                                   "Exportá a Word para conservar la escritura original.")
    return f'<font name="{font.fontName}">{word}</font>'


def _paragraph_markup(raw: str) -> str:
    # Normalize only the output copy; manual selections refer to the reviewed text.
    text = escape(normalize("NFC", raw))
    if not text.isascii():
        text = _WORD.sub(_format_word, text)
    return text.replace("\n", "<br/>")


def _paragraph_style(fmt: DocxExportFormat) -> ParagraphStyle:
    return ParagraphStyle(
        name="AnonBody",
        fontName="Times-Roman",
        fontSize=fmt.font_size_pt,
        leading=fmt.font_size_pt * fmt.line_spacing,
        alignment=_ALIGN_MAP.get(fmt.alignment, TA_JUSTIFY),
        spaceAfter=fmt.space_after_pt,
    )


def build_pdf_bytes(
    paragraphs: list[str],
    fmt: DocxExportFormat | None = None,
) -> bytes:
    fmt = fmt or DEFAULT_DOCX_FORMAT
    style = _paragraph_style(fmt)
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=fmt.margin_cm * cm,
        rightMargin=fmt.margin_cm * cm,
        topMargin=fmt.margin_top_bottom_cm * cm,
        bottomMargin=fmt.margin_top_bottom_cm * cm,
    )

    story: list[Flowable] = []
    for raw in paragraphs:
        if not raw.strip():
            story.append(Spacer(1, style.leading * (raw.count("\n") + 1) + style.spaceAfter))
            continue
        story.append(Paragraph(_paragraph_markup(raw), style))

    if not story:
        story.append(Paragraph(escape("(documento vacío)"), style))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
