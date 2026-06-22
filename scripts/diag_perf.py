"""Diagnóstico de rendimiento: extracción y análisis NLP."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.detection.pipeline import run_detection
from app.detection.regex_ar import detect_regex_ar
from app.detection.regex_catalog import load_catalog_patterns
from app.resolution.cluster import build_clusters


def bench_text(label: str, text: str) -> None:
    print(f"\n=== {label} ===")
    print(f"  chars: {len(text):,}")

    t0 = time.perf_counter()
    regex_items = detect_regex_ar(text)
    t1 = time.perf_counter()
    print(f"  regex_ar: {t1 - t0:.2f}s -> {len(regex_items)} items")

    try:
        from app.detection.presidio_layer import detect_presidio

        t0 = time.perf_counter()
        pres = detect_presidio(text)
        t1 = time.perf_counter()
        print(f"  presidio: {t1 - t0:.2f}s -> {len(pres)} items")
    except Exception as e:
        print(f"  presidio: ERROR {e}")

    try:
        from app.detection.spacy_layer import detect_spacy

        t0 = time.perf_counter()
        sp = detect_spacy(text)
        t1 = time.perf_counter()
        print(f"  spacy: {t1 - t0:.2f}s -> {len(sp)} items")
    except Exception as e:
        print(f"  spacy: ERROR {e}")

    t0 = time.perf_counter()
    mentions = run_detection(text)
    t1 = time.perf_counter()
    print(f"  run_detection: {t1 - t0:.2f}s -> {len(mentions)} mentions")

    t0 = time.perf_counter()
    clusters = build_clusters(mentions, text)
    t1 = time.perf_counter()
    print(f"  build_clusters: {t1 - t0:.2f}s -> {len(clusters)} clusters")
    n = len(mentions)
    print(f"  pares cluster (O(n^2)): {n * (n - 1) // 2:,}")


def bench_pdf(path: Path) -> None:
    import pdfplumber

    from app.extraction.pdf import extract_pdf

    data = path.read_bytes()
    print(f"\n=== PDF: {path.name} ({len(data) / 1024 / 1024:.1f} MB) ===")

    with pdfplumber.open(path) as doc:
        total = len(doc.pages)
        print(f"  paginas: {total}")

        t0 = time.perf_counter()
        empty = 0
        text_pages = 0
        for i, page in enumerate(doc.pages):
            pt = (page.extract_text() or "").strip()
            if pt:
                text_pages += 1
            else:
                empty += 1
            if (i + 1) % 20 == 0:
                elapsed = time.perf_counter() - t0
                print(f"    extract_text pag {i+1}/{total}: {elapsed:.2f}s acum")
        t1 = time.perf_counter()
        print(f"  extract_text todas: {t1 - t0:.2f}s ({text_pages} con texto, {empty} vacias)")

    t0 = time.perf_counter()
    text = extract_pdf(data)
    t1 = time.perf_counter()
    print(f"  extract_pdf: {t1 - t0:.2f}s -> {len(text):,} chars")
    bench_text("analisis post-extraccion", text)


def main() -> None:
    page = (
        "Autos: GONZALEZ MARIA c/ EMPRESA S.A. s/ danos y perjuicios\n"
        "Expediente N SAC 12345/2026. Juzgado Nacional en lo Civil N 45.\n"
        "El imputado Juan Carlos Perez, DNI 27.353.518, CUIT 20-27353518-3,\n"
        "domiciliado en Av. Corrientes 1234, piso 3, dto. B, CABA.\n"
        "Telefono 011-4567-8901. Email juan.perez@mail.com.\n"
        "La Sra. Maria Elena Rodriguez comparece como testigo.\n"
        "Dr. Roberto Martinez, abogado patrocinante.\n"
    )
    text_100 = (page + "\n\n") * 100
    bench_text("sintetico ~100 pag", text_100)

    text_400 = (page + "\n\n") * 400
    bench_text("sintetico ~400 pag", text_400)

    print(f"\ncatalog patterns: {len(load_catalog_patterns())}")

    if len(sys.argv) > 1:
        bench_pdf(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
