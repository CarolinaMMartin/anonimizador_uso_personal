"""Comprobación de precisión sobre un documento sintético."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.detection.pipeline import run_detection

BAD = [
    "expuesto",
    "nombre",
    "nombres",
    "nocturnos",
    "2026",
    "manifiesta que mantuvo una relación",
    "es y hostigamiento reiterado",
    "exportadas",
    "no pudo",
    "considera que se trata de una",
    "02052026",
    "como",
    "ficticio",
    "de parte de las conversaciones",
    "matías s/",
    "mariana c/",
    "negó los hechos",
]

EXPECTED = {
    ("PERSONA", "Marcos Adrián Benítez"),
    ("PERSONA", "Camila Rocío Ferreyra"),
    ("DNI", "29.882.104"),
    ("TELEFONO", "+54 9 11 5931-7720"),
    ("EMAIL", "camila.ferreyra.test@example.invalid"),
    ("DOMICILIO", "calle Sauce Viejo 3310"),
}


def main() -> None:
    text = """
    Marcos Adrián Benítez y Camila Rocío Ferreyra.
    DNI 29.882.104. Tel +54 9 11 5931-7720.
    Email camila.ferreyra.test@example.invalid
    domicilio calle Sauce Viejo 3310.
    Por lo expuesto y exportadas del año 2026.
    manifiesta que mantuvo una relación de pareja.
    nombre y nombres nocturnos no pudo exportaciones.
    """

    mentions = run_detection(text)
    surfaces = [m.surface for m in mentions]
    low = " ".join(surfaces).lower()

    errors = []
    for bad in BAD:
        if bad.lower() in low:
            errors.append(f"Falso positivo detectado: {bad!r}")

    missing = []
    actual = {(m.cat, m.surface) for m in mentions}
    for expected in sorted(EXPECTED - actual):
        missing.append(f"Falta la detección completa con sus límites exactos: {expected!r}")

    print(f"Menciones: {len(mentions)}")
    for m in mentions:
        print(f"  [{m.source_layer}] {m.cat}: {m.surface!r}")

    if errors:
        print("\nERRORES:")
        for e in errors:
            print(" ", e)
    if missing:
        print("\nFALTANTES:")
        for m in missing:
            print(" ", m)

    if not errors and not missing:
        print("\nOK — tests de precisión pasaron")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
