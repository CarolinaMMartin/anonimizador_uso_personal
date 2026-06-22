"""Verifica que Presidio y spaCy estén operativos."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TEXT = """
El imputado Juan Gustavo Pérez, DNI 20.123.456, CUIT 20-20123456-3.
Email: maria.lopez@ejemplo.com.ar. Tel: +54 11 4567-8901.
Expediente N 12345/2024. Juzgado Nacional en lo Criminal.
"""


def main() -> None:
    from app.detection.nlp_status import get_nlp_layers_status
    from app.detection.pipeline import run_detection

    print("=== Estado capas NLP ===")
    status = get_nlp_layers_status()
    for name, info in status.items():
        print(f"  {name}: {info}")

    print("\n=== Detección combinada ===")
    mentions = run_detection(TEXT)
    by_layer: dict[str, int] = {}
    for m in mentions:
        by_layer[m.source_layer] = by_layer.get(m.source_layer, 0) + 1
    print(f"  Total menciones: {len(mentions)}")
    print(f"  Por capa: {by_layer}")
    for m in mentions[:12]:
        print(f"    [{m.source_layer}] {m.cat}: {m.surface!r}")


if __name__ == "__main__":
    main()
