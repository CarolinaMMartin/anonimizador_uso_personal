import pytest

from app.detection import pipeline
from app.detection.filters import is_valid_detection
from app.detection.person_names import contains_person_list, person_name_spans
from app.models.schemas import SessionState
from app.services.analyze import run_full_analysis


@pytest.mark.parametrize('value', [
    'Quiroga y Tomás Ferrer', 'Vorst e Inés Gómez',
    'María Gómez y Pedro Ferrer', 'Juan y Pedro',
    'Quiroga y Tomás\nFerrer', 'QUIROGA Y TOMÁS FERRER',
])
def test_conjunction_between_distinct_people_is_not_a_single_name(value):
    assert contains_person_list(value)
    assert not is_valid_detection('PERSONA', value, value, 0)
    assert all(span[2] != value for span in person_name_spans(value))


@pytest.mark.parametrize('value', [
    'Juan García y Martín', 'Pedro Ramón y Zelkin',
    'María Fernández de la Vega', 'JUAN GARCÍA Y MARTÍN',
    'García y Martín Pérez, Juan',
])
def test_surname_conjunction_and_particles_remain_inside_one_name(value):
    assert not contains_person_list(value)
    assert [span[2] for span in person_name_spans(value)] == [value]
    assert is_valid_detection('PERSONA', value, value, 0)


@pytest.mark.parametrize('nlp', [False, True])
def test_paragraph_break_before_surname_cannot_join_two_identities(monkeypatch, nlp):
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', nlp)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', nlp)
    state = SessionState(session_id='conjunction-synthetic', doc_text=(
        'María Gómez Rosales compareció. Pedro Ferrer declaró. '
        'María Gómez\n\nRosales y Pedro Ferrer suscribieron el acta.'
    ))
    run_full_analysis(state)
    assert not any('Rosales y Pedro' in mention.surface for mention in state.mentions)
    assert len(state.clusters) == 2
    assert not any(any('María' in surface for surface in cluster.surfaces)
                   and any('Pedro' in surface for surface in cluster.surfaces)
                   for cluster in state.clusters)


def test_ambiguous_component_of_compound_surname_cannot_bridge_people(monkeypatch):
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', False)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', False)
    state = SessionState(session_id='surname-synthetic', doc_text=(
        'Juan García y Martín declaró. Pedro Martín compareció. Martín indicó lo sucedido.'
    ))
    run_full_analysis(state)
    full = next(det for det in state.detections if det.original == 'Juan García y Martín')
    other = next(det for det in state.detections if det.original == 'Pedro Martín')
    short = next(det for det in state.detections if det.original == 'Martín')
    assert short.cluster_id is None
    assert not any(set(full.mention_ids + other.mention_ids) <= set(cluster.mention_ids)
                   for cluster in state.clusters)


def test_explicit_surname_order_protects_its_natural_form(monkeypatch):
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', False)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', False)
    formal = 'García y Martín Pérez, Juan'
    natural = 'Juan García y Martín Pérez'
    state = SessionState(session_id='compound-synthetic', doc_text=(
        f'{formal} declaró. {natural} compareció.'
    ))
    run_full_analysis(state)
    assert {mention.surface for mention in state.mentions} == {formal, natural}
    assert len(state.clusters) == 1
    assert set(state.clusters[0].surfaces) == {formal, natural}
