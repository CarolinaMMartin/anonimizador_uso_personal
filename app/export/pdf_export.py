"""Exportación a PDF con ReportLab."""
from __future__ import annotations

import io
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate

from app.export.docx_format import DEFAULT_DOCX_FORMAT, DocxExportFormat

_ALIGN_MAP = {
    "left": TA_LEFT,
    "justify": TA_JUSTIFY,
    "center": TA_CENTER,
    "right": TA_RIGHT,
}


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

    story: list[Paragraph] = []
    for raw in paragraphs:
        text = raw.strip()
        if not text:
            continue
        safe = escape(text).replace("\n", "<br/>")
        story.append(Paragraph(safe, style))

    if not story:
        story.append(Paragraph(escape("(documento vacío)"), style))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
