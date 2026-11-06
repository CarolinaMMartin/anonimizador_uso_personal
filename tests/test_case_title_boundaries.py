import re

import pytest

from app.detection import pipeline
from app.detection.case_titles import CASE_CONNECTOR_RE, is_explicit_case_party
from app.detection.filters import apply_quality_filters, is_valid_detection
from app.detection.regex_ar import RawItem, _detect_autos_parties, detect_regex_ar
from app.detection.regex_catalog import _caratula_parties


@pytest.mark.parametrize('versus', ['c/', 'c./', 'C /', 'contra', 'CONTRA'])
@pytest.mark.parametrize('subject', ['s/', 's./', 'S /', 'sobre', 'SOBRE'])
def test_both_parties_stop_at_case_connectors(versus, subject):
    actor, defendant = 'Gómez Pérez, María', 'Suárez, Juan'
    text = f'{actor} {versus} {defendant} {subject} daños y perjuicios'
    spans = _detect_autos_parties(text)
    assert [value for _, _, value in spans] == [actor, defendant]
    assert all(text[start:end] == value for start, end, value in spans)
    catalog = _caratula_parties(re.search(r'(.*)', text))
    assert catalog == [(value, start, end) for start, end, value in spans]


@pytest.mark.parametrize('surface', [
    'María c/ Suárez', 'María c./ Suárez', 'María contra Suárez',
    'Juan s/', 'Juan s./', 'Juan sobre daños',
])
def test_caption_context_cannot_validate_a_cross_party_name(surface):
    text = f'Gómez Pérez, {surface} s/ daños y perjuicios'
    start = text.index(surface)
    assert not is_valid_detection('PERSONA', surface, text, start)
    items = [RawItem('PERSONA', surface, start, start + len(surface), source)
             for source in ('regex', 'spacy', 'presidio', 'regex_v2')]
    assert apply_quality_filters(items, text) == []


@pytest.mark.parametrize('connector', ['c/', 'c./', 's/', 's./'])
def test_partial_nlp_connector_tokens_are_rejected(connector):
    text = f'Gómez, María {connector} Suárez, Juan s/ daños'
    start = text.index('María')
    end = text.index(connector) + 1
    assert not is_valid_detection('PERSONA', text[start:end], text, start)


@pytest.mark.parametrize('actor, defendant', [
    ('Gómez Pérez, María', 'Suárez, Juan'),
    ('GÓMEZ PÉREZ, MARÍA', 'SUÁREZ, JUAN'),
    ('María de los Ángeles Gómez', 'Juan de la Vega'),
    ('Gómez Pérez,\nMaría', 'Suárez,\nJuan'),
    ('Gómez, M.', 'Suárez, J.'),
])
def test_nlp_bridges_cannot_join_the_two_parties(monkeypatch, actor, defendant):
    from app.detection import presidio_layer, spacy_layer

    text = f'{actor} c./ {defendant} s./ daños y perjuicios'
    slash = text.index(' c./ ')
    opponent = text.index(defendant)
    end_subject = text.index(' s./') + len(' s./')
    bridges = [
        RawItem('PERSONA', text[0:opponent + len(defendant)], 0, opponent + len(defendant), 'presidio'),
        RawItem('PERSONA', text[slash + 1:end_subject], slash + 1, end_subject, 'spacy'),
    ]
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', True)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', True)
    monkeypatch.setattr(presidio_layer, 'detect_presidio', lambda *args, **kwargs: bridges[:1])
    monkeypatch.setattr(spacy_layer, 'detect_spacy', lambda *args, **kwargs: bridges[1:])
    mentions = pipeline.run_detection(text, ['PERSONA'])
    assert [item.surface.rstrip('.') for item in mentions] == [actor.rstrip('.'), defendant.rstrip('.')]
    assert all(not CASE_CONNECTOR_RE.search(item.surface) for item in mentions)


def test_real_nlp_keeps_people_and_company_separate():
    text = 'Gómez Pérez, María c/ Nueva Industria S.R.L. s/ daños y perjuicios.'
    mentions = pipeline.run_detection(text)
    assert [(item.cat, item.surface) for item in mentions] == [
        ('PERSONA', 'Gómez Pérez, María'), ('EMPRESA', 'Nueva Industria S.R.L.'),
    ]


@pytest.mark.parametrize('surface', [
    'María de los Ángeles Gómez', 'Juan del Valle', 'César Contreras',
    'Sofía Sobrero', 'Contras, Juan',
])
def test_name_particles_and_connector_substrings_are_not_barriers(surface):
    assert not CASE_CONNECTOR_RE.search(surface)


@pytest.mark.parametrize('actor, defendant', [
    ('lucia benitez', 'tomas ferrao'),
    ('zorlan vexor', 'altra zexor'),
    ('velken, norlia', 'qoren, davren'),
    ('zorlan de la vexor', 'altra del zexor'),
    ('Zorlan Vexor', 'Altra Zexor'),
])
@pytest.mark.parametrize('versus', [' c/ ', ' c/', '   c./  ', '\r\nc/\r\n'])
@pytest.mark.parametrize('subject', ['', ' s/daños y perjuicios'])
def test_explicit_parties_preserve_unknown_names_without_a_catalog_anchor(actor, defendant, versus, subject):
    text = f'{actor}{versus}{defendant}{subject}'
    items = apply_quality_filters(detect_regex_ar(text), text)
    people = [item for item in items if item.cat == 'PERSONA']
    assert {item.original for item in people} == {actor, defendant}
    assert all(text[item.start:item.end] == item.original for item in people)


@pytest.mark.parametrize('subject', [' s/ ', ' s/', '  s./  ', '\r\ns/\r\n'])
@pytest.mark.parametrize('actor', ['zorlan vexor', 'vexor, zorlan', 'zorlan de la vexor'])
def test_subject_separator_does_not_require_an_opposing_party(actor, subject):
    text = f'{actor}{subject}daños y perjuicios'
    items = apply_quality_filters(detect_regex_ar(text), text)
    assert [(item.cat, item.original) for item in items] == [('PERSONA', actor)]
    start, end, value = _detect_autos_parties(text)[0]
    assert text[:start] + '[PERSONA_1]' + text[end:] == f'[PERSONA_1]{subject}daños y perjuicios'
    assert value == actor


@pytest.mark.parametrize('text', [
    'informe técnico sobre salud',
    'consulta pendiente contra resolución',
    'solicita información s/ el trámite',
    'recibió documentación s/ el trámite',
    'zorlan vexor compareció y declaró',
])
def test_caption_context_does_not_enable_unknown_words_in_prose(text):
    assert not [item for item in detect_regex_ar(text) if item.cat == 'PERSONA']


def test_nearby_caption_does_not_validate_an_unrelated_phrase():
    text = 'zorlan vexor c/ altra zexor s/ alimentos.\nInforme técnico.'
    phrase = 'Informe técnico'
    start = text.index(phrase)
    assert not is_explicit_case_party(phrase, text, start)
    assert not is_valid_detection('PERSONA', phrase, text, start)


@pytest.mark.parametrize('text', ['Domicilio: c/ Olmos 123, piso 2', 'vive c/ Olmos 123'])
def test_street_abbreviation_is_not_a_case_party(text):
    items = detect_regex_ar(text)
    assert not any(item.cat == 'PERSONA' for item in items)
    assert any(item.cat == 'DOMICILIO' and item.original.startswith('c/ Olmos 123') for item in items)


@pytest.mark.parametrize('nlp', [False, True])
@pytest.mark.parametrize('actor, defendant', [
    ('Zorlan vexor gundor', 'Altra zexor pellor'),
    ('Mario vexor gundor', 'Tomas ferrao'),
    ('Zorlan perez gundor', 'Tomas ferrao'),
    ('zorlan de la vexor del monte azul', 'altra zexor'),
    ('Vexor', 'Zexor'),
])
def test_complete_bounded_names_do_not_depend_on_case_or_particle_count(monkeypatch, nlp, actor, defendant):
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', nlp)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', nlp)
    text = f'{actor} c/ {defendant} s/ daños'
    assert [(item.cat, item.surface) for item in pipeline.run_detection(text)] == [
        ('PERSONA', actor), ('PERSONA', defendant),
    ]


@pytest.mark.parametrize('nlp', [False, True])
@pytest.mark.parametrize('party, category', [
    ('acme servicios s.a.', 'EMPRESA'),
    ('ACME SERVICIOS S.A.', 'EMPRESA'),
    ('Acme servicios s.r.l.', 'EMPRESA'),
    ('obra social ferroviaria', 'EMPRESA'),
    ('Cooperativa Norte Sur', 'EMPRESA'),
    ('asociación civil nueva esperanza', 'EMPRESA'),
    ('ministerio público fiscal', 'ORGANISMO'),
])
def test_bounded_nonperson_parties_keep_their_category(monkeypatch, nlp, party, category):
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', nlp)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', nlp)
    text = f'{party} c/ zorlan vexor s/ cobro'
    assert [(item.cat, item.surface) for item in pipeline.run_detection(text)] == [
        (category, party), ('PERSONA', 'zorlan vexor'),
    ]


@pytest.mark.parametrize('nlp', [False, True])
@pytest.mark.parametrize('phrase', [
    'informe técnico', 'recurso extraordinario', 'constancia presentada',
    'oficios electrónicos', 'copias certificadas', 'notificación pendiente',
    'procedimiento abreviado', 'actuaciones administrativas',
    'consulta pendiente', 'inscripción provisional', 'certificaciones pendientes',
    'requerimiento urgente', 'traslados electrónicos',
])
def test_procedural_noun_phrases_are_not_people_even_before_a_subject(monkeypatch, nlp, phrase):
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', nlp)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', nlp)
    text = f'{phrase} s/ cumplimiento'
    assert not is_valid_detection('PERSONA', phrase, text, 0)
    assert pipeline.run_detection(text) == []


def test_administrative_nominal_phrases_on_both_sides_are_not_people():
    assert pipeline.run_detection('consulta pendiente c/ resolución administrativa') == []


@pytest.mark.parametrize('nlp', [False, True])
@pytest.mark.parametrize('prefix', ['se presentó ', 'consta que ', 'compareció la '])
def test_company_caption_does_not_absorb_an_introductory_clause(monkeypatch, nlp, prefix):
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', nlp)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', nlp)
    text = f'{prefix}acme servicios s.a. c/ zorlan vexor s/ cobro'
    assert [(item.cat, item.surface) for item in pipeline.run_detection(text)] == [
        ('EMPRESA', 'acme servicios s.a.'), ('PERSONA', 'zorlan vexor'),
    ]
