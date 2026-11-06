"""La selección explícita y las repeticiones tienen límites distintos."""
import pytest
from fastapi.testclient import TestClient

from app.anonymize.apply import anonymize_text
from app.main import app
from app.models.schemas import Position, SessionState
from app.models.store import store
from app.services.detections import add_bulk_detection, add_manual_detection


def _state(text):
    return SessionState(session_id="matching", doc_text=text)


def _ranges(detection):
    return sorted((p.start, p.end) for p in detection.positions)


@pytest.mark.parametrize("suffix", [
    "Mariana", "Ana@example.test", "Ana/otra", "Ana:otra", "Ana+otra",
    "Ana-otra", "Ana'otra", "Ana_otra", "Ana.otra", "Ana2", "Ana\u0301",
])
def test_manual_repetitions_require_complete_data_by_default(suffix):
    state = _state("Ana; " + suffix)
    detection = add_manual_detection(state, "PERSONA", 0, 3, "Ana")
    assert _ranges(detection) == [(0, 3)]


@pytest.mark.parametrize("suffix", ["Ana,", "Ana.", "(Ana)", "«Ana»", "📄Ana", "ANA", "ana"])
def test_manual_complete_data_accepts_punctuation_and_case(suffix):
    state = _state("Ana; " + suffix)
    start = 5 + suffix.lower().index("ana")
    detection = add_manual_detection(state, "PERSONA", 0, 3, "Ana")
    assert _ranges(detection) == [(0, 3), (start, start + 3)]


@pytest.mark.parametrize("suffix", ["+123", "123-456", "123/456", "123.456", "123_456"])
def test_manual_numeric_repetitions_do_not_split_compound_data(suffix):
    state = _state("123; " + suffix)
    detection = add_manual_detection(state, "OTRO", 0, 3, "123")
    assert _ranges(detection) == [(0, 3)]


def test_manual_rejected_candidate_does_not_skip_later_complete_occurrence():
    state = _state("Ana Ana; xAna Ana Ana")
    detection = add_manual_detection(state, "PERSONA", 0, 7, "Ana Ana")
    assert _ranges(detection) == [(0, 7), (14, 21)]


def test_manual_selection_inside_a_word_is_always_kept_exactly():
    state = _state("Mariana y Ana")
    detection = add_manual_detection(state, "PERSONA", 4, 7, "ana")
    assert _ranges(detection) == [(4, 7), (10, 13)]


def test_manual_overlapping_partial_selection_is_not_expanded_by_default():
    state = _state("121212")
    detection = add_manual_detection(state, "OTRO", 2, 6, "1212")
    assert _ranges(detection) == [(2, 6)]
    assert anonymize_text(state.doc_text, state.detections) == "12[DATO_1]"


def test_manual_repetitions_remain_literal_for_accents():
    state = _state("José; Jose; Jose\u0301; JOSÉ")
    detection = add_manual_detection(state, "PERSONA", 0, 4, "José")
    assert _ranges(detection) == [(0, 4), (19, 23)]


@pytest.mark.parametrize(("text", "query", "start", "end"), [
    ("Ana y Mariana", "Ana", 10, 13),
    ("Ana@example.test", "Ana", 0, 3),
    ("123-456", "123", 0, 3),
    ("+123", "123", 1, 4),
    ("Jose\u0301", "Jose", 0, 4),
    ("Otro texto", "Ana", 0, 3),
    ("Ana Perez", "Ana  Perez", 0, 9),
])
def test_bulk_rejects_incomplete_or_mismatched_search_without_mutation(text, query, start, end):
    state = _state(text)
    before = state.model_dump()
    with pytest.raises(ValueError):
        add_bulk_detection(state, "PERSONA", query, [Position(start=start, end=end)])
    assert state.model_dump() == before


@pytest.mark.parametrize("query", ["Jose", "José", "JOSE"])
@pytest.mark.parametrize("allow_partial", [False, True])
def test_bulk_accepts_full_decomposed_accent_span(query, allow_partial):
    state = _state("Jose\u0301")
    detection = add_bulk_detection(
        state, "PERSONA", query, [Position(start=0, end=5)], allow_partial=allow_partial,
    )
    assert _ranges(detection) == [(0, 5)]
    assert detection.positions[0].raw == state.doc_text
    assert anonymize_text(state.doc_text, state.detections) == "[PERSONA_1]"


@pytest.fixture
def api_session():
    sid = store.create()
    state = store.get(sid)
    with TestClient(app) as client:
        yield client, state
    store.delete(sid)


@pytest.mark.parametrize("endpoint", ["/api/manual-detection", "/api/detections/manual"])
@pytest.mark.parametrize("allow_partial", [None, True])
def test_manual_api_partial_option_only_changes_repetitions(api_session, endpoint, allow_partial):
    client, state = api_session
    state.doc_text = "121212"
    payload = {"session_id": state.session_id, "cat": "OTRO", "start": 2, "end": 6, "original": "1212"}
    if allow_partial is not None:
        payload["allow_partial"] = allow_partial
    response = client.post(endpoint, json=payload)
    assert response.status_code == 200, response.text
    detection = response.json()["detection"]
    positions = sorted((p["start"], p["end"]) for p in detection["positions"])
    assert positions == ([(0, 4), (2, 6)] if allow_partial else [(2, 6)])
    assert anonymize_text(state.doc_text, state.detections) == ("[DATO_1]" if allow_partial else "12[DATO_1]")


@pytest.mark.parametrize("allow_partial", [None, True])
def test_search_api_partial_option_is_validated_on_server(api_session, allow_partial):
    client, state = api_session
    state.doc_text = "📄 Mariana"
    before = state.model_dump()
    payload = {"session_id": state.session_id, "cat": "PERSONA", "original": "Ana", "positions": [{"start": 6, "end": 9}]}
    if allow_partial is not None:
        payload["allow_partial"] = allow_partial
    response = client.post("/api/search-and-anonymize", json=payload)
    assert response.status_code == (200 if allow_partial else 400), response.text
    if allow_partial:
        assert response.json()["detection"]["positions"] == [{"start": 6, "end": 9, "raw": "ana"}]
        assert anonymize_text(state.doc_text, state.detections) == "📄 Mari[PERSONA_1]"
    else:
        assert state.model_dump() == before


@pytest.mark.parametrize("allow_partial", [False, True])
def test_search_api_mismatched_offsets_after_emoji_are_rejected_even_for_partial(api_session, allow_partial):
    client, state = api_session
    state.doc_text = "📄 Ana."
    before = state.model_dump()
    response = client.post("/api/search-and-anonymize", json={
        "session_id": state.session_id, "cat": "PERSONA", "original": "Ana",
        "positions": [{"start": 3, "end": 6}], "allow_partial": allow_partial,
    })
    assert response.status_code == 400, response.text
    assert state.model_dump() == before


def test_search_api_validates_every_position_before_any_mutation(api_session):
    client, state = api_session
    state.doc_text = "Ana; Mariana"
    before = state.model_dump()
    response = client.post("/api/search-and-anonymize", json={
        "session_id": state.session_id, "cat": "PERSONA", "original": "Ana",
        "positions": [{"start": 0, "end": 3}, {"start": 9, "end": 12}],
    })
    assert response.status_code == 400, response.text
    assert state.model_dump() == before


@pytest.mark.parametrize(("text", "start", "end", "expected"), [
    ("Ana y Mariana", 0, 3, True),
    ("Ana y Mariana", 10, 13, False),
    ("Ana,", 0, 3, True),
    ("Ana.", 0, 3, True),
    ("Ana.example", 0, 3, False),
    ("Ana@example.test", 0, 3, False),
    ("Ana@example.test", 0, 16, True),
    ("+123", 1, 4, False),
    ("+123", 0, 4, True),
    ("+١٢٣", 1, 4, False),
    ("+²", 1, 2, True),
    ("Ana²", 0, 3, False),
    ("中Ana", 1, 4, False),
    ("📄 Ana", 2, 5, True),
    ("Jose\u0301", 0, 4, False),
    ("Jose\u0301", 0, 5, True),
    ("Ana\u093e", 0, 3, False),
    ("Ana\u20dd", 0, 3, False),
    ("Ana\u1ab0", 0, 3, False),
    ("x, Ana", 1, 6, True),
    ("Ana, x", 0, 4, True),
    ("Ana", -1, 3, False),
    ("Ana", 0, 4, False),
    ("Ana", 1, 1, False),
])
def test_complete_match_uses_original_unicode_token_boundaries(text, start, end, expected):
    from app.services.matching import is_complete_match

    assert is_complete_match(text, start, end) is expected


def test_search_normalization_removes_all_mark_categories_without_collapsing_spaces():
    from app.services.matching import normalize_for_search

    assert normalize_for_search("Á e\u1ab0 अ\u093e Z\u20dd  A\tB\nC") == "a e अ z  a\tb\nc"
