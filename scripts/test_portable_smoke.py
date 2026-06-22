"""Smoke tests antes de compartir el portable."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_detection_improvements():
    from app.detection.filters import is_valid_detection
    from app.detection.regex_ar import detect_regex_ar

    text = "En la calle y en riesgo de situacion de calle."
    assert not is_valid_detection("DOMICILIO", "piso que no", text, 0)
    assert not is_valid_detection(
        "DOMICILIO", "calle y en riesgo de situación de calle", text, 0
    )
    assert is_valid_detection("DOMICILIO", "Calle Falsa 123", text, 0)

    addr_text = (
        "Ingresó al domicilio de la Sra. Arroyo, sito en "
        "Av. Corrientes 2387, piso 1, Dpto. A, de esta ciudad, sin autorización."
    )
    doms = [x for x in detect_regex_ar(addr_text) if x.cat == "DOMICILIO"]
    assert doms, "debe detectar al menos un domicilio"
    best = max(doms, key=lambda x: len(x.original))
    assert "Corrientes" in best.original and "2387" in best.original
    assert "Dpto" in best.original or "piso" in best.original.lower()
    assert not any("calle y en riesgo" in d.original.lower() for d in doms)

    caps = "Fdo. por CARRERA TERESITA HAYDEE."
    personas = [x for x in detect_regex_ar(caps) if x.cat == "PERSONA"]
    assert any("CARRERA" in p.original for p in personas)

    exp_text = (
        "Número: EXP 33764/2009-0\n"
        "CUIJ: EXP J-01-00056958-1/2009-0\n"
        "Otros: Nro. 12345/22"
    )
    exps = [x for x in detect_regex_ar(exp_text) if x.cat == "EXPEDIENTE"]
    assert any("33764/2009" in e.original for e in exps), \
        f"Falta EXP 33764: {[e.original for e in exps]}"
    assert any("J-01-00056958-1/2009-0" in e.original for e in exps), \
        f"Falta CUIJ: {[e.original for e in exps]}"
    print("OK deteccion")


def test_export_utf8_filename():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.models.schemas import Detection, Position
    from app.models.store import store

    client = TestClient(app)
    sid = store.create()
    state = store.get(sid)
    assert state
    state.doc_name = "Prueba García"
    state.doc_text = "CUIT 20-12345678-9"
    state.detections = [
        Detection(
            id=0,
            cat="CUIT",
            original="20-12345678-9",
            placeholder="[CUIT_1]",
            positions=[Position(start=5, end=20)],
        )
    ]
    store.save(state)
    r = client.post("/api/export/docx", json={"session_id": sid, "use_confirmed_only": False})
    assert r.status_code == 200, r.text
    assert len(r.content) > 1000
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd
    print("OK export docx")


def test_server_starts_with_null_streams():
    import os

    # Simula PyInstaller windowed
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = None
    sys.stderr = None
    try:
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w", encoding="utf-8")
        from uvicorn.config import Config
        from app.main import app, HOST, PORT

        Config(app, host=HOST, port=PORT, log_level="info").configure_logging()
        print("OK logging windowed")
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def test_health():
    from fastapi.testclient import TestClient
    from app.main import app

    r = TestClient(app).get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    print("OK health")


if __name__ == "__main__":
    test_detection_improvements()
    test_export_utf8_filename()
    test_server_starts_with_null_streams()
    test_health()
    print("\nTODOS LOS TESTS PASARON")
