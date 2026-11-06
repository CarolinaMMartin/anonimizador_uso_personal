import io

import pdfplumber
import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.export.export_utils import text_to_paragraphs
from app.main import app
from app.models.schemas import Detection, Position
from app.models.store import store


TEXT = (
    'Empresa: [EMPRESA_1]\n[ORGANISMO_1]\ntexto separado por la persona revisora.\n\n'
    'Otro párrafo.\n\n\n\nCierre del documento.\nFecha: 05/10/2026\nNúmero: 0007-004211'
)
PARAGRAPHS = [
    'Empresa: [EMPRESA_1]\n[ORGANISMO_1]\ntexto separado por la persona revisora.',
    'Otro párrafo.', '', 'Cierre del documento.\nFecha: 05/10/2026\nNúmero: 0007-004211',
]


@pytest.mark.parametrize('separator', ['\n', '\r\n', '\r'])
def test_text_to_paragraphs_preserves_explicit_breaks_and_empty_paragraphs(separator):
    assert text_to_paragraphs(TEXT.replace('\n', separator)) == PARAGRAPHS


@pytest.mark.parametrize('text', [
    '\nInicio\n', '\n\nInicio\n\n', 'Título:\n\nlínea independiente',
    'Primero,\nsegundo', 'Primero-\nsegundo', '  Sangría\n\n  cierre  ',
    'Primero\n\n\nsegundo',
])
def test_paragraph_conversion_is_lossless_except_newline_encoding(text):
    assert '\n\n'.join(text_to_paragraphs(text)) == text


@pytest.fixture
def review():
    sid = store.create()
    state = store.get(sid)
    original = 'Entidad de ejemplo'
    state.doc_text = TEXT.replace('[EMPRESA_1]', original)
    start = state.doc_text.index(original)
    state.detections = [Detection(id=0, cat='EMPRESA', original=original,
        placeholder='[EMPRESA_1]', positions=[Position(start=start, end=start + len(original), raw=original)])]
    with TestClient(app) as client:
        yield client, state
    store.delete(sid)


@pytest.mark.parametrize('edited', [False, True])
def test_word_and_pdf_keep_reviewed_line_boundaries(review, edited):
    client, state = review
    payload = {'session_id': state.session_id}
    if edited:
        payload['text'] = TEXT.replace('\n', '\r\n')
    word_response = client.post('/api/export/docx', json=payload)
    assert word_response.status_code == 200, word_response.text
    word = Document(io.BytesIO(word_response.content))
    assert [paragraph.text for paragraph in word.paragraphs] == PARAGRAPHS
    assert len(word.paragraphs[0]._p.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br')) == 2

    pdf_response = client.post('/api/export/pdf', json=payload)
    assert pdf_response.status_code == 200, pdf_response.text
    with pdfplumber.open(io.BytesIO(pdf_response.content)) as pdf:
        assert len(pdf.pages) == 1
        text = pdf.pages[0].extract_text()
        words = pdf.pages[0].extract_words()
    assert text.splitlines() == [line for paragraph in PARAGRAPHS for line in paragraph.splitlines() if line]
    tops = {word['text']: word['top'] for word in words}
    assert tops['[EMPRESA_1]'] < tops['[ORGANISMO_1]'] < tops['texto'] < tops['Otro'] < tops['Cierre']
    simple_break = tops['[ORGANISMO_1]'] - tops['[EMPRESA_1]']
    paragraph_break = tops['Otro'] - tops['texto']
    with_empty_paragraph = tops['Cierre'] - tops['Otro']
    assert simple_break == pytest.approx(18)
    assert paragraph_break > simple_break
    assert with_empty_paragraph > paragraph_break + simple_break


def test_export_uses_editor_breaks_instead_of_rebuilding_original_layout(review):
    client, state = review
    edited = 'Empresa: [EMPRESA_1]\n\n[ORGANISMO_1]\nCierre.'
    response = client.post('/api/export/docx', json={'session_id': state.session_id, 'text': edited})
    assert response.status_code == 200
    assert [p.text for p in Document(io.BytesIO(response.content)).paragraphs] == [
        'Empresa: [EMPRESA_1]', '[ORGANISMO_1]\nCierre.',
    ]
