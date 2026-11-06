"""A completed review may legitimately contain no detections."""
import io

import pdfplumber
import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import AnalyzeResponse
from app.models.store import store


@pytest.fixture
def review():
    sid = store.create()
    state = store.get(sid)
    state.doc_text = 'Texto sintético sin datos.'
    with TestClient(app) as client:
        yield client, state
    store.delete(sid)


def export_text(response, extension):
    assert response.status_code == 200, response.text
    if extension == 'preview':
        return response.json()['text']
    if extension == 'docx':
        return '\n'.join(p.text for p in Document(io.BytesIO(response.content)).paragraphs)
    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        return '\n'.join(p.extract_text() or '' for p in pdf.pages)


@pytest.mark.parametrize('extension', ['preview', 'docx', 'pdf'])
def test_loaded_but_unreviewed_is_blocked_even_with_supplied_text(review, extension):
    client, state = review
    response = client.post('/api/export/' + extension,
                           json={'session_id': state.session_id, 'text': 'No habilita revisión'})
    assert response.status_code == 400


@pytest.mark.parametrize('extension', ['preview', 'docx', 'pdf'])
def test_reviewed_document_without_detections_is_exportable(review, extension):
    client, state = review
    state.has_review = True
    response = client.post('/api/export/' + extension, json={'session_id': state.session_id})
    assert export_text(response, extension) == state.doc_text


@pytest.mark.parametrize('extension', ['docx', 'pdf'])
@pytest.mark.parametrize('edited', ['Texto corregido por la persona.', ''])
def test_empty_review_preserves_editor_text_including_empty(review, extension, edited):
    client, state = review
    state.has_review = True
    response = client.post('/api/export/' + extension,
                           json={'session_id': state.session_id, 'text': edited})
    assert export_text(response, extension) == edited


def test_successful_empty_analysis_marks_review_and_failed_analysis_does_not(review, monkeypatch):
    from app.api import routes_analyze
    from app.detection.dictionaries import CatalogLoadError

    client, state = review
    def fail(_state):
        raise CatalogLoadError('catálogo sintético inválido')
    monkeypatch.setattr(routes_analyze, 'run_full_analysis', fail)
    payload = {'session_id': state.session_id, 'enabled_categories': ['EMAIL']}
    assert client.post('/api/analyze', json=payload).status_code == 503
    assert not store.get(state.session_id).has_review
    monkeypatch.setattr(routes_analyze, 'run_full_analysis', lambda s: AnalyzeResponse(
        session_id=s.session_id, detections=[], clusters=[], stats={'TOTAL': 0}))
    assert client.post('/api/analyze', json=payload).status_code == 200
    assert store.get(state.session_id).has_review
    assert client.get('/api/session/' + state.session_id).json()['has_review'] is True
    monkeypatch.setattr(routes_analyze, 'run_full_analysis', fail)
    assert client.post('/api/analyze', json=payload).status_code == 503
    assert store.get(state.session_id).has_review


def test_manual_review_remains_reviewed_after_last_detection_is_deleted(review):
    client, state = review
    response = client.post('/api/manual-detection', json={
        'session_id': state.session_id, 'cat': 'OTRO', 'start': 0, 'end': 5, 'original': 'Texto'})
    assert response.status_code == 200
    det_id = response.json()['detection']['id']
    assert client.delete(f'/api/detections/{det_id}', params={'session_id': state.session_id}).status_code == 200
    assert state.detections == [] and state.has_review
    for extension in ('preview', 'docx', 'pdf'):
        assert export_text(client.post('/api/export/' + extension,
            json={'session_id': state.session_id}), extension) == state.doc_text


@pytest.mark.parametrize('previously_reviewed', [False, True])
def test_cancelled_analysis_preserves_review_state(review, monkeypatch, previously_reviewed):
    from app.api import routes_analyze
    from app.services.analysis_cancel import AnalysisCancelledError

    client, state = review
    state.has_review = previously_reviewed
    before = state.model_dump()
    def cancel(copy):
        copy.has_review = not previously_reviewed
        raise AnalysisCancelledError('cancelación sintética')
    monkeypatch.setattr(routes_analyze, 'run_full_analysis', cancel)
    response = client.post('/api/analyze', json={
        'session_id': state.session_id, 'enabled_categories': ['EMAIL']})
    assert response.status_code == 409
    assert store.get(state.session_id).model_dump() == before
