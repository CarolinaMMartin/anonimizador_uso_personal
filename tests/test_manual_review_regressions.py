"""La revisión humana debe llegar intacta a la vista previa y las descargas."""
import io

import pdfplumber
import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Detection, Position
from app.models.store import store


@pytest.fixture
def review():
    sid = store.create()
    state = store.get(sid)
    with TestClient(app) as client:
        yield client, state
    store.delete(sid)


def exported_text(client, sid, extension):
    response = client.post('/api/export/' + extension, json={'session_id': sid})
    assert response.status_code == 200, response.text
    if extension == 'preview':
        return response.json()['text']
    if extension == 'docx':
        return '\n'.join(p.text for p in Document(io.BytesIO(response.content)).paragraphs)
    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        return '\n'.join(page.extract_text() or '' for page in pdf.pages)


@pytest.mark.parametrize('endpoint', ['/api/manual-detection', '/api/detections/manual'])
@pytest.mark.parametrize(('category', 'surface'), [
    ('DOMICILIO', 'Campana 39'), ('PERSONA', 'Fiscalina Zorvik'),
    ('OTRO', 'alias azul'), ('ORGANISMO', 'Unidad Zorvik'),
    ('EMPRESA', 'Zorvik'), ('DNI', 'AB-42'), ('TELEFONO', '123'),
    ('PATENTE', 'XX'), ('EXPEDIENTE', 'reservado'),
    ('EMAIL', 'correo reservado'), ('CUIT', 'CUIT reservado'),
])
def test_manual_category_is_accepted_and_exported(review, endpoint, category, surface):
    client, state = review
    state.doc_text = f'Inicio: {surface}\n\nRepite: {surface}\n\nFin.'
    start = state.doc_text.index(surface)
    response = client.post(endpoint, json={
        'session_id': state.session_id, 'cat': category,
        'start': start, 'end': start + len(surface), 'original': surface,
    })
    assert response.status_code == 200, response.text
    det = response.json()['detection']
    assert det['enabled'] and det['user_added']
    assert len(det['positions']) == 2
    for extension in ('preview', 'docx', 'pdf'):
        text = exported_text(client, state.session_id, extension)
        assert surface not in text
        assert text.count(det['placeholder']) == 2
        assert 'Inicio:' in text and 'Fin.' in text


@pytest.mark.parametrize('bulk', [False, True])
def test_manual_reselection_reactivates_existing_row(review, bulk):
    client, state = review
    state.doc_text = 'Campana 39'
    state.detections = [Detection(id=8, cat='DOMICILIO', original=state.doc_text,
        placeholder='[DOMICILIO_9]', enabled=False,
        positions=[Position(start=0, end=len(state.doc_text))])]
    payload = {'session_id': state.session_id, 'cat': 'DOMICILIO', 'original': state.doc_text}
    if bulk:
        endpoint = '/api/search-and-anonymize'
        payload['positions'] = [{'start': 0, 'end': len(state.doc_text), 'raw': state.doc_text}]
    else:
        endpoint = '/api/manual-detection'
        payload.update(start=0, end=len(state.doc_text))
    response = client.post(endpoint, json=payload)
    assert response.status_code == 200, response.text
    assert len(state.detections) == 1
    assert state.detections[0].id == 8
    assert state.detections[0].enabled and state.detections[0].user_added
    assert exported_text(client, state.session_id, 'preview') == '[DOMICILIO_9]'


def test_category_correction_is_not_reclassified_during_export(review):
    client, state = review
    state.doc_text = 'Campana 39'
    state.detections = [Detection(id=5, cat='PERSONA', original=state.doc_text,
        placeholder='[PERSONA_1]', positions=[Position(start=0, end=10)])]
    response = client.patch('/api/detections/5', json={'session_id': state.session_id, 'cat': 'DOMICILIO'})
    assert response.status_code == 200
    for extension in ('preview', 'docx', 'pdf'):
        assert exported_text(client, state.session_id, extension) == state.detections[0].placeholder
    csv = client.post('/api/export/csv', json={'session_id': state.session_id})
    assert csv.status_code == 200 and 'Campana 39' in csv.text


def test_disabled_long_name_does_not_remove_active_surname_on_export(review):
    client, state = review
    state.doc_text = 'Juan Perez declaró.'
    state.detections = [
        Detection(id=0, cat='PERSONA', original='Juan Perez', placeholder='[PERSONA_1]',
                  enabled=False, positions=[Position(start=0, end=10)]),
        Detection(id=1, cat='PERSONA', original='Perez', placeholder='[PERSONA_2]',
                  positions=[Position(start=5, end=10)]),
    ]
    for extension in ('preview', 'docx', 'pdf'):
        assert exported_text(client, state.session_id, extension) == 'Juan [PERSONA_2] declaró.'


@pytest.mark.parametrize('bulk', [False, True])
def test_stale_offsets_are_rejected_without_modifying_the_session(review, bulk):
    client, state = review
    state.doc_text = '📄 Campana 39. Fin.'
    before = state.model_dump()
    payload = {'session_id': state.session_id, 'cat': 'DOMICILIO', 'original': 'Campana 39'}
    if bulk:
        endpoint = '/api/search-and-anonymize'
        payload['positions'] = [{'start': 3, 'end': 13, 'raw': 'Campana 39'}]
    else:
        endpoint = '/api/manual-detection'
        payload.update(start=3, end=13)
    result = client.post(endpoint, json=payload)
    assert result.status_code == 400
    assert state.model_dump() == before


def test_manual_multiline_selection_and_new_group(review):
    client, state = review
    state.doc_text = 'Antes. Campana\n39. Después.'
    surface = 'Campana\n39'
    start = state.doc_text.index(surface)
    response = client.post('/api/manual-detection', json={
        'session_id': state.session_id, 'cat': 'DOMICILIO',
        'start': start, 'end': start + len(surface), 'original': 'Campana 39',
    })
    assert response.status_code == 200, response.text
    detection_id = response.json()['detection']['id']
    grouped = client.post('/api/assign-cluster', json={
        'session_id': state.session_id, 'detection_id': detection_id, 'cluster_id': '__new__',
    })
    assert grouped.status_code == 200, grouped.text
    assert exported_text(client, state.session_id, 'preview') == 'Antes. [DOMICILIO_1]. Después.'
