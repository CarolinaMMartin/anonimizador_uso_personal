"""Regresión: listas de personas con coma, separadores de campo y frases abstractas."""
import socket

import pytest

from app import main
from app.detection import pipeline
from app.detection.filters import is_valid_detection
from app.detection.person_names import (
    comma_is_name_inversion, comma_separates_people, cut_at_field_separator, is_abstract_phrase,
)


def _persons(text):
    return [m.surface for m in pipeline.run_detection(text, ['PERSONA'])]


@pytest.mark.parametrize('text, expected', [
    ('los señores Gustavo Ríos, Mariela Paz, Hernán Luna',
     ['Gustavo Ríos', 'Mariela Paz', 'Hernán Luna']),
    ('Se cita a Roberto Fernández, Laura Martínez, Diego Sosa.',
     ['Roberto Fernández', 'Laura Martínez', 'Diego Sosa']),
    ('JUAN PEREZ, MARIA LOPEZ y CARLOS GOMEZ comparecen',
     ['JUAN PEREZ', 'MARIA LOPEZ', 'CARLOS GOMEZ']),
    ('Pérez, Juan y López, Ana comparecen.', ['Pérez, Juan', 'López, Ana']),
])
def test_comma_lists_produce_one_detection_per_person(text, expected):
    assert _persons(text) == expected


@pytest.mark.parametrize('text, expected', [
    ('PÉREZ, Juan Carlos fue notificado.', 'PÉREZ, Juan Carlos'),
    ('CZICZERSKYJ, YAMILA MONICA solicita', 'CZICZERSKYJ, YAMILA MONICA'),
    ('El imputado PÉREZ GARCÍA, Juan declaró.', 'PÉREZ GARCÍA, Juan'),
    ('Sr. Pérez, Juan', 'Pérez, Juan'),
])
def test_inverted_surname_first_names_stay_whole(text, expected):
    assert expected in _persons(text)


def test_comma_reading_distinguishes_list_from_inversion():
    lista = 'Mariela Paz, Hernán Luna'
    assert comma_separates_people(lista, lista.index(','))
    assert not comma_is_name_inversion(lista, lista.index(','))
    invertido = 'PÉREZ, Juan Carlos'
    assert comma_is_name_inversion(invertido, invertido.index(','))
    assert not comma_separates_people(invertido, invertido.index(','))
    enumeracion = 'Martín, Sofía, Lucas y Valentina'
    assert comma_separates_people(enumeracion, enumeracion.index(','))


def test_unknown_names_after_comma_are_not_treated_as_a_list():
    # Sin ancla en el catálogo la lectura es incierta: no se descarta la detección.
    text = 'velken, norlia'
    assert not comma_separates_people(text, text.index(','))


@pytest.mark.parametrize('text', [
    'Víctima: Conexidad Subjetiva',
    'Prisión Preventiva',
    'CONEXIDAD SUBJETIVA',
])
def test_abstract_legal_phrases_are_not_people(text):
    assert _persons(text) == []


@pytest.mark.parametrize('text, expected', [
    ('Víctima: Xiomara Zúñiga', 'Xiomara Zúñiga'),
    ('Víctima: Concepción Arenales', 'Concepción Arenales'),
])
def test_unanchored_names_with_one_regular_word_survive(text, expected):
    assert expected in _persons(text)


def test_abstract_phrase_rule_requires_every_word_to_be_abstract():
    assert is_abstract_phrase('Conexidad Subjetiva')
    assert not is_abstract_phrase('Concepción Arenales')
    assert not is_abstract_phrase('Florencia Valencia')  # ambas en catálogo


def test_spaced_dash_ends_a_person_name():
    text = 'Juan Pérez - Conexidad Subjetiva'
    assert _persons(text) == ['Juan Pérez']
    assert cut_at_field_separator(text) == 'Juan Pérez'
    assert cut_at_field_separator('Ana María Pérez-Gómez') == 'Ana María Pérez-Gómez'
    assert not is_valid_detection('PERSONA', text, text, 0)
    assert 'Ana María Pérez-Gómez' in _persons('Ana María Pérez-Gómez declaró.')


def test_browser_waits_until_the_server_accepts_connections(monkeypatch):
    opened = []
    monkeypatch.setattr(main.webbrowser, 'open', opened.append)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        free_port = probe.getsockname()[1]
    main.open_browser_when_ready('http://x', '127.0.0.1', free_port, timeout=0.3)
    assert opened == []
    with socket.socket() as server:
        server.bind(('127.0.0.1', 0))
        server.listen()
        port = server.getsockname()[1]
        main.open_browser_when_ready('http://ok', '127.0.0.1', port, timeout=2)
    assert opened == ['http://ok']


@pytest.mark.parametrize('text, expected', [
    ('Juan Pérez Conexidad Subjetiva', ['Juan Pérez']),
    ('Conexidad Subjetiva, Juan', ['Juan']),
    ('PEREZ JUAN - CONEXIDAD SUBJETIVA', ['PEREZ JUAN']),
    ('Imputado: Conexidad Subjetiva', []),
    ('Firmado por: CONEXIDAD SUBJETIVA', []),
    ('En la causa conexidad subjetiva se dispuso', []),
])
def test_never_anonymized_terms_are_removed_from_every_layer(text, expected):
    assert _persons(text) == expected


def test_never_anonymized_terms_ignore_case_and_accents():
    from app.detection.exceptions import exception_spans

    text = 'CONEXIDAD  SUBJETIVA y Conexidad Subjetiva'
    assert len(exception_spans(text)) == 2
    assert exception_spans('Conexidades subjetivas') == []
