import io

import pdfplumber
import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.anonymize.apply import anonymize_text
from app.anonymize.placeholders import build_detections_from_mentions
from app.detection import pipeline
from app.detection.dictionaries import CatalogLoadError
from app.detection.regex_ar import RawItem
from app.main import app
from app.models.store import store


def test_crossing_mentions_preserve_the_entire_sensitive_span(monkeypatch):
    text = 'Juan Perez Gomez declaró.'
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', False)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', False)
    monkeypatch.setattr(pipeline, 'detect_regex_ar', lambda _: [
        RawItem('PERSONA', 'Juan Perez', 0, 10),
        RawItem('PERSONA', 'Perez Gomez', 5, 16),
    ])
    mentions = pipeline.run_detection(text)
    assert [m.surface for m in mentions] == ['Juan Perez Gomez']
    assert anonymize_text(text, build_detections_from_mentions(mentions, 'cat')) == '[PERSONA_1] declaró.'


@pytest.mark.parametrize('spans', [
    [(0, 4), (2, 7), (6, 10)], [(0, 10), (2, 7)],
    [(0, 2), (2, 4), (7, 10)], [(1, 8), (0, 3), (8, 10)],
])
def test_overlap_resolution_preserves_coverage_and_original_offsets(spans):
    text = '0123456789'
    items = [RawItem('OTRO', text[a:b], a, b) for a, b in spans]
    expected = {i for a, b in spans for i in range(a, b)}
    for ordered in (items, list(reversed(items))):
        result = pipeline.resolve_overlaps(ordered, text)
        assert {i for item in result for i in range(item.start, item.end)} == expected
        assert all(item.original == text[item.start:item.end] for item in result)
        assert all(a.end <= b.start for a, b in zip(result, result[1:]))


PARAGRAPHS = [
    'Ministerio Publico Fiscal de la Caba',
    'Denunciante: María del Carmen Fernández de la Vega.',
    'D.N.I. Nro.: 30.456.789; indemnización solicitada: $ 10.000.',
    'Teléfono: 4301-5678. Celular: 1156789012.',
    'Domicilio: PASEO COLON 1333 4 A.',
    'Dirección: Tucumán 2345, piso 6, departamento B.',
    'Empresa: Transportes del Sur S.R.L.',
    'Expediente: EX-2026-98765432-GCABA-DG; patente AB 321 CD.',
    'Chasis: 8AFZZZ54Z6J123456; motor: QX-7890123.',
    'Póliza de seguro Nro. 0042-87654321.',
    'Nro de seguimiento de denuncias: MPF-2026-887766.',
    'Consulta: https://denuncias.example/consulta?seguimiento=MPF-2026-887766.',
    'Se incorpora la documentación presentada y se deja constancia de su recepción. ' * 4,
    'Se verificó nuevamente 30456789 y MPF-2026-887766. Se notificó a Transportes del Sur.',
    'Se deja constancia de lo informado. Ley 471, artículo 12.',
]
SECRETS = [
    'María', 'Carmen', 'Fernández', 'Vega', '30.456.789', '30456789', '4301-5678', '1156789012',
    'PASEO COLON', '1333', 'Tucumán', '2345', 'Transportes del Sur',
    'EX-2026-98765432-GCABA-DG', 'AB 321 CD', '8AFZZZ54Z6J123456',
    'QX-7890123', '0042-87654321', 'MPF-2026-887766', 'denuncias.example',
]


@pytest.mark.parametrize('nlp', [False, True])
def test_sensitive_fields_survive_review_and_all_document_exports(monkeypatch, nlp):
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', nlp)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', nlp)
    document = Document()
    document.sections[0].header.paragraphs[0].text = PARAGRAPHS[0]
    for paragraph in PARAGRAPHS[1:]:
        document.add_paragraph(paragraph)
    data = io.BytesIO()
    document.save(data)
    with TestClient(app) as client:
        uploaded = client.post('/api/upload', files={
            'file': ('regresion.docx', data.getvalue(),
                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
        })
        assert uploaded.status_code == 200, uploaded.text
        sid = uploaded.json()['session_id']
        try:
            analyzed = client.post('/api/analyze', json={'session_id': sid, 'label_mode': 'cat'})
            assert analyzed.status_code == 200, analyzed.text
            rows = analyzed.json()['detections']
            assert any(row['cat'] == 'ORGANISMO' and row['original'] == PARAGRAPHS[0] for row in rows)
            state = store.get(sid)
            for row in rows:
                for position in row['positions']:
                    assert state.doc_text[position['start']:position['end']] == position['raw']
            payload = {'session_id': sid, 'use_confirmed_only': False}
            preview = client.post('/api/export/preview', json=payload)
            assert preview.status_code == 200, preview.text
            texts = [preview.json()['text']]
            for extension in ('docx', 'pdf'):
                response = client.post('/api/export/' + extension, json=payload)
                assert response.status_code == 200, response.text
                if extension == 'docx':
                    exported = Document(io.BytesIO(response.content))
                    texts.append('\n'.join(paragraph.text for paragraph in exported.paragraphs))
                else:
                    with pdfplumber.open(io.BytesIO(response.content)) as exported:
                        texts.append('\n'.join(page.extract_text() or '' for page in exported.pages))
            for text in texts:
                assert not [secret for secret in SECRETS if secret in text], text
                assert 'Se deja constancia de lo informado.' in text
                assert 'Ley 471' in text
                assert '$ 10.000' in text
        finally:
            store.delete(sid)


def test_missing_catalog_is_reported_without_replacing_the_review(monkeypatch):
    from app.api import routes_analyze
    from app.models.schemas import Detection

    sid = store.create()
    state = store.get(sid)
    state.doc_text = 'Juan Perez declaró.'
    state.detections = [Detection(id=8, cat='PERSONA', original='Juan Perez', placeholder='[PERSONA_8]')]

    def unavailable(candidate):
        candidate.detections.clear()
        raise CatalogLoadError('Catálogo no encontrado: nombres.json')

    monkeypatch.setattr(routes_analyze, 'run_full_analysis', unavailable)
    try:
        with TestClient(app) as client:
            result = client.post('/api/analyze', json={
                'session_id': sid, 'label_mode': 'ini', 'enabled_categories': ['DNI'],
            })
        assert result.status_code == 503
        assert 'nombres.json' in result.json()['detail']
        assert state.detections[0].id == 8
        assert store.get(sid).label_mode == 'cat'
        assert store.get(sid).enabled_categories == []
    finally:
        store.delete(sid)
