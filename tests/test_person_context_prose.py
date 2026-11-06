import io

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.detection import pipeline
from app.detection.person_names import person_name_spans, trim_persona_tail
from app.main import app
from app.models.store import store


@pytest.mark.parametrize('name', ['Laura Suarez', 'Zella Qorven', 'tashi Dorji'])
@pytest.mark.parametrize('prose', [
    'figura en el encabezado', 'permanece allí', 'trabaja lejos',
    'viaja mañana', 'interviene habitualmente',
])
def test_capitalized_names_stop_at_lowercase_narrative(name, prose):
    text = f'Dra. {name} {prose}.'
    assert person_name_spans(text)[0][2] == name
    assert trim_persona_tail(f'{name} {prose}', allow_unknown_lower=True) == name


@pytest.mark.parametrize('name', [
    'tashi dorji', 'Zella qorven', 'Juan Carlos qorven',
    'Juan CARLOS pérez González', 'María de los Ángeles Fernández de la Vega',
])
def test_contextual_names_keep_catalog_case_variants_and_particles(name):
    assert person_name_spans(f'Nombre: {name}.')[0][2] == name
    assert trim_persona_tail(name, allow_unknown_lower=True) == name


@pytest.mark.parametrize('prefix', ['Dra. ', 'Denunciante: ', 'Nombre: '])
def test_explicit_context_does_not_join_separate_people_across_lines(prefix):
    text = prefix + 'Laura Suarez\nMaría Gómez'
    assert [span[2] for span in person_name_spans(text)] == ['Laura Suarez', 'María Gómez']


@pytest.mark.parametrize('name', ['Zella\nQorven', 'Juan Carlos\nQorven', 'María\nJosé González'])
def test_explicit_context_keeps_incomplete_name_across_soft_wrap(name):
    assert person_name_spans('Dra. ' + name + ' declaró.')[0][2] == name


@pytest.mark.parametrize('categories', [['PERSONA'], None])
@pytest.mark.parametrize('nlp', [False, True])
def test_header_and_footer_person_context_preserves_following_prose(monkeypatch, categories, nlp):
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', nlp)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', nlp)
    document = Document()
    document.add_paragraph('Se conserva el contenido del documento.')
    document.sections[0].header.paragraphs[0].text = 'La Dra. Laura Suarez figura en el encabezado.'
    document.sections[0].footer.paragraphs[0].text = 'El Dr. Diego Ramirez figura en el pie.'
    data = io.BytesIO()
    document.save(data)
    with TestClient(app) as client:
        uploaded = client.post('/api/upload', files={
            'file': ('partes_ficticias.docx', data.getvalue(),
                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
        })
        assert uploaded.status_code == 200, uploaded.text
        sid = uploaded.json()['session_id']
        try:
            analyzed = client.post('/api/analyze', json={
                'session_id': sid, 'enabled_categories': categories,
            })
            assert analyzed.status_code == 200, analyzed.text
            rows = [row for row in analyzed.json()['detections'] if row['cat'] == 'PERSONA']
            assert {row['original'] for row in rows} == {'Laura Suarez', 'Diego Ramirez'}
            preview = client.post('/api/export/preview', json={'session_id': sid})
            assert preview.status_code == 200, preview.text
            text = preview.json()['text']
            assert 'Laura Suarez' not in text and 'Diego Ramirez' not in text
            assert 'figura en el encabezado.' in text and 'figura en el pie.' in text
            assert 'Se conserva el contenido del documento.' in text
        finally:
            store.delete(sid)
