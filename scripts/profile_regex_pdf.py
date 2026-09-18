"""Perfil de regex sobre un PDF concreto."""
import sys
import argparse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description='Perfil local de regex sobre un PDF elegido.')
    parser.add_argument('pdf', type=Path)
    pdf = parser.parse_args().pdf
    import re

    from app.detection.regex_ar import detect_regex_ar
    from app.detection.regex_catalog import load_catalog_patterns
    from app.extraction.pdf import extract_pdf

    text = extract_pdf(pdf.read_bytes())
    print(f"chars={len(text)}", flush=True)

    print("\n--- regex_ar por bloque ---", flush=True)
    blocks: list[tuple[str, re.Pattern[str]]] = []
    # import patterns from module by re-running sections is heavy; profile catalog + full

    print("\n--- catalog ---", flush=True)
    for p in load_catalog_patterns():
        t0 = time.perf_counter()
        n = sum(1 for _ in p.regex.finditer(text))
        dt = time.perf_counter() - t0
        print(f"{dt:7.2f}s n={n:5d} {p.name:30s} {p.cat}", flush=True)

    print("\n--- detect_regex_ar total ---", flush=True)
    t0 = time.perf_counter()
    items = detect_regex_ar(text)
    print(f"{time.perf_counter()-t0:.2f}s items={len(items)}", flush=True)


if __name__ == "__main__":
    main()
