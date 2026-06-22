"""Casos del equivalencias (11).csv — deben filtrarse o deduplicarse."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.detection.filters import is_valid_detection
from app.services.analyze import _drop_substring_personas, _prune_detections
from app.models.schemas import Detection, Position

MUST_REJECT = [
    ("PERSONA", "Mariana c/ Calderini"),
    ("PERSONA", "Matías s/"),
    ("DOMICILIO", "2026"),
    ("DOMICILIO", "Calderini"),
    ("PERSONA", "de parte de las conversaciones previas"),
    ("PERSONA", "Matías negó los hechos atribuidos y afirmó"),
    (
        "ORGANISMO",
        "juzgado dispuso correr traslado de la presentación y requirió a Ailen Bressan",
    ),
]

SHOULD_KEEP = [
    ("PERSONA", "Sánchez Caparrós"),
    ("PERSONA", "Mariana Sánchez Caparrós"),
    ("PERSONA", "Matías Calderini"),
    ("PERSONA", "Ailen Bressan"),
    ("ORGANISMO", "Juzgado Civil N.º 12"),
]


def main() -> int:
    text = "texto de prueba con mariana y ailen bressan"
    err = []
    for cat, s in MUST_REJECT:
        if is_valid_detection(cat, s, text, 0):
            err.append(f"Debería rechazarse: {cat} / {s!r}")

    for cat, s in SHOULD_KEEP:
        if not is_valid_detection(cat, s, text, 0):
            err.append(f"Debería aceptarse: {cat} / {s!r}")

    dets = [
        Detection(
            id=i,
            cat=cat,  # type: ignore[arg-type]
            original=s,
            placeholder=f"[{cat}_{i}]",
            enabled=True,
            positions=[Position(start=0, end=len(s))],
        )
        for i, (cat, s) in enumerate(
            [
                ("PERSONA", "Mariana Sánchez Caparrós"),
                ("PERSONA", "Mariana"),
                ("PERSONA", "Ailen Bressan"),
                ("PERSONA", "Ailen"),
                ("PERSONA", "Bressan"),
            ]
        )
    ]
    pruned = _drop_substring_personas(dets)
    surfaces = {d.original for d in pruned if d.cat == "PERSONA"}
    if "Mariana" in surfaces or "Ailen" in surfaces or "Bressan" in surfaces:
        err.append(f"Dedup falló, quedaron: {surfaces}")

    if err:
        print("FALLÓ:")
        for e in err:
            print(" ", e)
        return 1
    print("OK — casos CSV (11)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
