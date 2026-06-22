"""Exportación a DOCX con formato judicial estándar."""
from __future__ import annotations

import io

from docx import Document

from app.export.docx_format import DEFAULT_DOCX_FORMAT, add_formatted_paragraph, apply_docx_format


def build_docx_bytes(
    paragraphs: list[str],
    fmt=DEFAULT_DOCX_FORMAT,
) -> bytes:
    doc = Document()
    apply_docx_format(doc, fmt)

    if paragraphs:
        for text in paragraphs:
            add_formatted_paragraph(doc, text, fmt)
    else:
        add_formatted_paragraph(doc, "(documento vacío)", fmt)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()
