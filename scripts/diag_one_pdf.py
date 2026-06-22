import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PDF = Path(r"c:\Users\CarolinaM\Downloads\LC 4980-2025 - DICTAMEN FINAL-2.pdf")


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> None:
    from app.extraction.pdf import extract_pdf
    from app.detection.regex_ar import detect_regex_ar
    from app.detection.pipeline import run_detection
    from app.resolution.cluster import build_clusters

    data = PDF.read_bytes()
    log(f"file_mb={len(data)/1024/1024:.1f}")

    t0 = time.perf_counter()
    text = extract_pdf(data)
    log(f"extract {time.perf_counter()-t0:.2f}s chars={len(text)} lines={text.count(chr(10))}")

    t0 = time.perf_counter()
    regex = detect_regex_ar(text)
    log(f"regex {time.perf_counter()-t0:.2f}s items={len(regex)}")

    t0 = time.perf_counter()
    mentions = run_detection(text)
    log(f"detection {time.perf_counter()-t0:.2f}s mentions={len(mentions)}")

    t0 = time.perf_counter()
    clusters = build_clusters(mentions, text)
    log(f"cluster {time.perf_counter()-t0:.2f}s clusters={len(clusters)}")


if __name__ == "__main__":
    main()
