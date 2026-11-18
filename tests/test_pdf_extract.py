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
        assert "documentos escaneados todavía no está disponible" in str(e)


def test_pages_without_text_go_through_the_recognition_hook(monkeypatch):
    from app.extraction import pdf

    seen = []
    monkeypatch.setattr(pdf, "recognize_page_without_text",
                        lambda page, page_number: seen.append(page_number) or "")
    text = extract_pdf(_make_mixed_pdf())
    assert seen == [1, 2, 3], "Solo las páginas sin texto pasan por el enganche"
    assert "Juan Carlos Perez" in text


def test_text_returned_by_the_hook_is_kept_in_page_order(monkeypatch):
    from app.extraction import pdf

    monkeypatch.setattr(
        pdf, "recognize_page_without_text",
        lambda page, page_number: f"Texto reconocido de la portada número {page_number}."
        if page_number == 1 else "")
    text = extract_pdf(_make_mixed_pdf())
    assert text.index("portada número 1") < text.index("Juan Carlos Perez")
    assert "número 2" not in text


def test_recognition_hook_does_nothing_yet_and_adds_no_ocr_dependency():
    from pathlib import Path

    from app.extraction import pdf

    assert pdf.recognize_page_without_text(object(), 1) == ""
    requirements = (Path(__file__).resolve().parent.parent / "requirements.txt").read_text(encoding="utf-8").lower()
    for name in ("tesseract", "easyocr", "rapidocr", "paddleocr", "ocrmypdf"):
        assert name not in requirements
