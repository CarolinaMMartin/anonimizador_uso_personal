"""Tests del buscador del preview: add_bulk_detection y endpoint."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Position
from app.models.store import store
from app.services.detections import add_bulk_detection


DOC = (
    "El Sr. García declaró ante la fiscalía. "
    "Más adelante, García ratificó su declaración. "
    "La testigo mencionó también a García."
)


def _new_session_with_doc(text: str = DOC) -> str:
    sid = store.create()
    state = store.get(sid)
    assert state is not None
    state.doc_name = "prueba"
    state.doc_text = text
    store.save(state)
    return sid


def test_add_bulk_detection_crea_una_deteccion_con_todas_las_positions():
    sid = _new_session_with_doc()
    state = store.get(sid)
    assert state is not None

    positions = [
        Position(start=7, end=13),
        Position(start=57, end=63),
        Position(start=113, end=119),
    ]
    det = add_bulk_detection(state, "PERSONA", "García", positions)

    assert det.cat == "PERSONA"
    assert det.original == "García"
    assert det.user_added is True
    assert len(det.positions) == 3
    assert {(p.start, p.end) for p in det.positions} == {(7, 13), (57, 63), (113, 119)}
    assert det.placeholder.startswith("[PERSONA")


def test_add_bulk_detection_deduplica_positions_repetidas():
    sid = _new_session_with_doc()
    state = store.get(sid)
    assert state is not None

    positions = [
        Position(start=7, end=13),
        Position(start=7, end=13),
        Position(start=57, end=63),
    ]
    det = add_bulk_detection(state, "PERSONA", "García", positions)
    assert len(det.positions) == 2


def test_add_bulk_detection_extiende_si_ya_existe_misma_cat_original():
    sid = _new_session_with_doc()
    state = store.get(sid)
    assert state is not None

    first = add_bulk_detection(
        state, "PERSONA", "García", [Position(start=7, end=13)]
    )
    total_detecciones_antes = len(state.detections)

    second = add_bulk_detection(
        state,
        "PERSONA",
        "García",
        [Position(start=7, end=13), Position(start=57, end=63)],
    )

    assert len(state.detections) == total_detecciones_antes
    assert second.id == first.id
    assert {(p.start, p.end) for p in second.positions} == {(7, 13), (57, 63)}


def test_add_bulk_detection_rechaza_positions_fuera_del_documento():
    sid = _new_session_with_doc()
    state = store.get(sid)
    assert state is not None

    with pytest.raises(ValueError):
        add_bulk_detection(
            state, "PERSONA", "García", [Position(start=99999, end=100000)]
        )


def test_add_bulk_detection_rechaza_rango_invalido():
    sid = _new_session_with_doc()
    state = store.get(sid)
    assert state is not None

    with pytest.raises(ValueError):
        add_bulk_detection(state, "PERSONA", "García", [Position(start=10, end=10)])


def test_add_bulk_detection_rechaza_original_corto():
    sid = _new_session_with_doc()
    state = store.get(sid)
    assert state is not None

    with pytest.raises(ValueError):
        add_bulk_detection(state, "PERSONA", "a", [Position(start=0, end=1)])


def test_add_bulk_detection_rechaza_sin_positions():
    sid = _new_session_with_doc()
    state = store.get(sid)
    assert state is not None

    with pytest.raises(ValueError):
        add_bulk_detection(state, "PERSONA", "García", [])


def test_add_bulk_detection_placeholder_personalizado():
    sid = _new_session_with_doc()
    state = store.get(sid)
    assert state is not None

    det = add_bulk_detection(
        state, "PERSONA", "García", [Position(start=7, end=13)],
        placeholder="[APELLIDO]",
    )
    assert det.placeholder == "[APELLIDO]"
    assert det.manual_placeholder is True


def test_endpoint_search_and_anonymize_shape_igual_a_manual_detection():
    client = TestClient(app)
    sid = _new_session_with_doc()

    r = client.post(
        "/api/search-and-anonymize",
        json={
            "session_id": sid,
            "cat": "PERSONA",
            "original": "García",
            "positions": [
                {"start": 7, "end": 13},
                {"start": 57, "end": 63},
                {"start": 113, "end": 119},
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "detection" in body
    assert "detections" in body
    assert body["detection"]["original"] == "García"
    assert len(body["detection"]["positions"]) == 3


def test_endpoint_devuelve_400_si_positions_esta_vacio():
    client = TestClient(app)
    sid = _new_session_with_doc()

    r = client.post(
        "/api/search-and-anonymize",
        json={"session_id": sid, "cat": "PERSONA", "original": "García", "positions": []},
    )
    assert r.status_code == 400


def test_endpoint_devuelve_404_si_sesion_inexistente():
    client = TestClient(app)
    r = client.post(
        "/api/search-and-anonymize",
        json={
            "session_id": "no-existe",
            "cat": "PERSONA",
            "original": "García",
            "positions": [{"start": 0, "end": 6}],
        },
    )
    assert r.status_code == 404
