"""Aplicación de reemplazos al texto."""
from app.models.schemas import Detection


def anonymize_text(text: str, detections: list[Detection], confirmed_only: bool = False) -> str:
    replacements: list[tuple[int, int, str]] = []
    for d in detections:
        if not d.enabled:
            continue
        if confirmed_only and not d.cluster_confirmed:
            # En modo confirmed_only, solo reemplazos con cluster confirmado
            # o detecciones marcadas manualmente
            if not (d.user_added or getattr(d, "_force_apply", False)):
                continue
        for p in d.positions:
            replacements.append((p.start, p.end, d.placeholder))

    replacements.sort(key=lambda x: (x[0], -x[1]))
    merged: list[tuple[int, int, str]] = []
    for start, end, value in replacements:
        if start < 0 or end > len(text) or end <= start:
            raise ValueError("Posición de anonimización inválida")
        if merged and start < merged[-1][1]:
            old_start, old_end, old_value = merged[-1]
            merged[-1] = (old_start, max(old_end, end), old_value)
        else:
            merged.append((start, end, value))
    out = text
    for start, end, value in reversed(merged):
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
