"""Character fidelity through upload, review and actual downloaded files."""
import io
from unicodedata import normalize

import pdfplumber
import pytest
from docx import Document
from fastapi.testclient import TestClient
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.main import app
from app.models.store import store
from app.runtime_paths import bundle_dir


def digital_pdf(text):
    font = TTFont("InputRoboto", str(bundle_dir() / "frontend/assets/fonts/Roboto.ttf"))
    pdfmetrics.registerFont(font)
    assert all(font.face.charToGlyph.get(ord(c)) for c in text)
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf)
    pdf.setFont("InputRoboto", 12)
    pdf.drawString(60, 720, text)
    pdf.save()
    return buf.getvalue()


@pytest.mark.parametrize('form', ['NFC', 'NFD'])
def test_pdf_accents_survive_anonymization_and_downloads(form):
    prefix = 'Acción, resolución, fiscalía, Muñoz. '
    email = 'caso@example.org'
    data = digital_pdf(normalize(form, prefix) + email)
    with TestClient(app) as client:
        upload = client.post('/api/upload', files={'file': ('ejemplo.pdf', data)})
        assert upload.status_code == 200
        session_id = upload.json()['session_id']
        payload = {'session_id': session_id}
        try:
            assert client.get('/api/preview', params=payload).json()['text'] == prefix + email
            assert client.post('/api/analyze', json={**payload, 'enabled_categories': ['EMAIL']}).is_success
            text = client.post('/api/export/preview', json=payload).json()['text']
            assert text == prefix + '[EMAIL_1]'
            word = client.post('/api/export/docx', json={**payload, 'text': text})
            assert Document(io.BytesIO(word.content)).paragraphs[0].text == text
            # Text pasted into the editor may also contain decomposed letters.
            extra = ' Pingüino, ¿qué? Dvořák y Łódź.'
            response = client.post('/api/export/pdf', json={**payload, 'text': normalize('NFD', text + extra)})
            assert response.is_success
            with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                assert pdf.pages[0].extract_text() == text + extra
        finally:
            store.delete(session_id)
