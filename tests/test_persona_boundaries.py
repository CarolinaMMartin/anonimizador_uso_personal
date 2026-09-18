"""Regression: dictionary loading, uppercase names and sentence boundaries."""
import json

import pytest

from app.anonymize.apply import anonymize_text
from app.detection import dictionaries, pipeline
from app.detection.filters import is_valid_detection
from app.detection.regex_ar import _clean_persona_surface, detect_regex_ar
from app.detection.regex_catalog import detect_regex_catalog, load_catalog_patterns
from app.models.schemas import Detection, Position
from app.services.analyze import _drop_substring_personas


@pytest.mark.parametrize('text, expected', [
    ('Dr. Juan Perez solicita que se rechace la demanda.', 'Juan Perez'),
    ('DR. JUAN PÉREZ SOLICITA QUE SE RECHACE LA DEMANDA.', 'JUAN PÉREZ'),
    ('el imputado JUAN PEREZ SOLICITA UNA MEDIDA', 'JUAN PEREZ'),
    ('La víctima María José González declara ante el tribunal.', 'María José González'),
    ('PÉREZ, JUAN CARLOS compareció.', 'PÉREZ, JUAN CARLOS'),
    ('CZICZERSKYJ, YAMILA MONICA declaró.', 'CZICZERSKYJ, YAMILA MONICA'),
    ('Dra. YAMILA MONICA CZICZERSKYJ manifestó su voluntad.', 'YAMILA MONICA CZICZERSKYJ'),
    ('Sr. PÉREZ manifestó su voluntad.', 'PÉREZ'),
    ('Juan de la Cruz declaró.', 'Juan de la Cruz'),
    ('juan perez solicita una medida.', 'juan perez'),
])
def test_names_stop_before_prose(monkeypatch, text, expected):
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', False)
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', False)
    mentions = pipeline.run_detection(text, ['PERSONA'])
    assert any(m.surface == expected for m in mentions), [m.surface for m in mentions]
    for mention in mentions:
        assert text[mention.start:mention.end] == mention.surface
        assert 'solicita' not in mention.surface.casefold()
        assert 'rechace' not in mention.surface.casefold()


@pytest.mark.parametrize('text', [
    'PODER JUDICIAL DE LA NACIÓN', 'JUZGADO NACIONAL EN LO CIVIL',
    'SR. SOLICITA QUE SE RECHACE LA DEMANDA', 'CONTESTA TRASLADO',
    'DERECHOS Y GARANTÍAS CONSTITUCIONALES',
])
def test_legal_headings_are_not_people(text):
    assert not [i for i in detect_regex_ar(text) if i.cat == 'PERSONA']


def test_loader_normalizes_case_accents_whitespace(tmp_path, monkeypatch):
    folder = tmp_path / 'dictionaries'
    folder.mkdir()
    (folder / 'nombres.json').write_text(json.dumps([' JUAN ', 'María', 'MARIA']), encoding='utf-8')
    monkeypatch.setattr(dictionaries, 'RESOURCE_DATA_DIR', tmp_path)
    assert dictionaries._load_json('nombres.json') == {'juan', 'maria'}


def test_invalid_catalog_is_explicit(tmp_path, monkeypatch):
    folder = tmp_path / 'dictionaries'
    folder.mkdir()
    (folder / 'nombres.json').write_text('{"wrong": "schema"}', encoding='utf-8')
    monkeypatch.setattr(dictionaries, 'RESOURCE_DATA_DIR', tmp_path)
    with pytest.raises(ValueError, match='Catálogo inválido'):
        dictionaries._load_json('nombres.json')


def test_external_name_rules_are_actually_loaded():
    load_catalog_patterns.cache_clear()
    descriptions = [p.description for p in load_catalog_patterns()]
    assert any('Nombre + apellido' in d for d in descriptions)
    items = detect_regex_catalog('PÉREZ, JUAN CARLOS solicita una medida')
    assert any(i.original == 'PÉREZ, JUAN CARLOS' for i in items)


def test_known_name_does_not_validate_a_sentence():
    assert not is_valid_detection('PERSONA', 'JUAN PEREZ PRESENTO ESCRITO')
    assert not is_valid_detection('PERSONA', 'Juan Perez solicita una medida')


def test_cleaner_keeps_rare_surname_before_comma():
    assert _clean_persona_surface('CZICZERSKYJ, YAMILA MONICA', 12) == ('CZICZERSKYJ, YAMILA MONICA', 12)


def test_standalone_surname_occurrence_is_kept():
    text = 'Juan Perez declaró. Perez compareció.'
    surname_start = text.index('Perez', 15)
    full = Detection(id=0, cat='PERSONA', original='Juan Perez', placeholder='[PERSONA_1]',
                     positions=[Position(start=0, end=10, raw='Juan Perez')])
    surname = Detection(id=1, cat='PERSONA', original='Perez', placeholder='[PERSONA_2]',
                        positions=[Position(start=surname_start, end=surname_start + 5, raw='Perez')])
    kept = _drop_substring_personas([full, surname])
    assert len(kept) == 2
    assert 'Perez' not in anonymize_text(text, kept)
