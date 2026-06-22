"""Aplicación de reemplazos al texto."""
from app.models.schemas import Detection


def anonymize_text(text: str, detections: list[Detection], confirmed_only: bool = False) -> str:
    replacements: list[tuple[int, int, str]] = []
    for d in detections:
        if not d.enabled:
            continue
        if confirmed_only and not d.cluster_id:
            # En modo confirmed_only, solo reemplazos con cluster confirmado
            # o detecciones marcadas manualmente
            if not getattr(d, "_force_apply", False):
                continue
        for p in d.positions:
            replacements.append((p.start, p.end, d.placeholder))

    replacements.sort(key=lambda x: x[0], reverse=True)
    out = text
    for start, end, value in replacements:
        out = out[:start] + value + out[end:]
    return out


def build_highlights(
    text: str, detections: list[Detection]
) -> list[dict]:
    """Genera rangos para highlights en frontend."""
    ranges = []
    for d in detections:
        if not d.enabled:
            continue
        for p in d.positions:
            ranges.append(
                {
                    "start": p.start,
                    "end": p.end,
                    "cat": d.cat,
                    "placeholder": d.placeholder,
                    "cluster_id": d.cluster_id,
                }
            )
    ranges.sort(key=lambda x: x["start"])
    filtered = []
    last_end = -1
    for r in ranges:
        if r["start"] >= last_end:
            filtered.append(r)
            last_end = r["end"]
    return filtered
