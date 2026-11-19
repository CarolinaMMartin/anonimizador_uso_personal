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


def test_scanned_page_is_reported_and_partial_exports_require_acknowledgement():
    from PIL import Image, ImageDraw
    from fastapi.testclient import TestClient
    from reportlab.lib.utils import ImageReader
    from app.main import app
    from app.models.store import store

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.drawString(72, 750, 'Primera pagina digital del expediente.')
    pdf.showPage()
    scan = Image.new('RGB', (400, 80), 'white')
    ImageDraw.Draw(scan).text((5, 5), 'Acta adjunta escaneada', fill='black')
    pdf.drawImage(ImageReader(scan), 72, 650)
    pdf.showPage()
    pdf.save()
    with TestClient(app) as client:
        uploaded = client.post('/api/upload', files={'file': ('mixto.pdf', buffer.getvalue())})
        assert uploaded.is_success
        data = uploaded.json()
        assert data['pdf_page_count'] == 2 and data['omitted_pdf_pages'] == [2]
        payload = {'session_id': data['session_id']}
        try:
            assert client.post('/api/analyze', json=payload).is_success
            preview = client.post('/api/export/preview', json=payload).json()['text']
            for extension in ('docx', 'pdf'):
                uri = '/api/export/' + extension
                blocked = client.post(uri, json={**payload, 'text': preview})
                assert blocked.status_code == 409 and blocked.json()['detail']['omitted_pdf_pages'] == [2]
                assert client.post(uri, json={**payload, 'text': preview, 'acknowledge_partial_pdf': True}).is_success
        finally:
            store.delete(data['session_id'])
