"""Tests de extracción PDF."""
import io

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.extraction.pdf import extract_pdf


def _make_mixed_pdf() -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    for _ in range(3):
        c.showPage()
    c.drawString(72, 750, "Expediente SAC 12345/2026. Imputado Juan Carlos Perez.")
    c.showPage()
    c.save()
    return buffer.getvalue()


def _make_empty_pdf() -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.showPage()
    c.showPage()
    c.save()
    return buffer.getvalue()


def test_extract_pdf_skips_leading_empty_pages():
    text = extract_pdf(_make_mixed_pdf())
    assert "Juan Carlos Perez" in text


def test_extract_pdf_rejects_all_empty():
    try:
        extract_pdf(_make_empty_pdf())
        assert False, "expected ValueError"
    except ValueError as e:
        assert "no tiene texto digital" in str(e).lower()
