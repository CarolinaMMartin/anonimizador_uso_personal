"""Generación de placeholders."""
from app.models.schemas import Detection, Mention, Position


def make_placeholder(cat: str, original: str, idx: int, mode: str) -> str:
    if mode == "gen":
        mapping = {
            "PERSONA": "[NOMBRE]",
            "DNI": "[DNI]",
            "CUIT": "[CUIT]",
            "EMPRESA": "[EMPRESA]",
            "EMAIL": "[EMAIL]",
            "TELEFONO": "[TELÉFONO]",
            "DOMICILIO": "[DOMICILIO]",
            "EXPEDIENTE": "[EXPEDIENTE]",
            "ORGANISMO": "[ORGANISMO]",
            "PATENTE": "[PATENTE]",
            "OTRO": "[DATO]",
        }
        return mapping.get(cat, "[DATO]")

    if mode == "ini":
        if cat in ("PERSONA", "EMPRESA"):
            skip = {
                "de", "del", "la", "las", "los", "y", "i",
                "S.A.", "S.R.L.", "S.A.S.", "S.A.U.",
            }
            parts = [p for p in original.split() if p not in skip and len(p) > 1]
            if parts:
                return "".join(p[0].upper() + "." for p in parts)
            return "[NOMBRE]" if cat == "PERSONA" else "[EMPRESA]"

    labels = {
        "PERSONA": "PERSONA",
        "DNI": "DNI",
        "CUIT": "CUIT",
        "EMPRESA": "EMPRESA",
        "EMAIL": "EMAIL",
        "TELEFONO": "TELEFONO",
        "DOMICILIO": "DOMICILIO",
        "EXPEDIENTE": "EXPEDIENTE",
        "ORGANISMO": "ORGANISMO",
        "PATENTE": "PATENTE",
        "OTRO": "DATO",
    }
    label = labels.get(cat, "DATO")
    return f"[{label}_{idx}]"


def build_detections_from_mentions(
    mentions: list[Mention], mode: str
) -> list[Detection]:
    groups: dict[str, dict] = {}
    for m in mentions:
        key = f"{m.cat}||{m.surface.strip().lower()}"
        if key not in groups:
            groups[key] = {
                "cat": m.cat,
                "original": m.surface.strip(),
                "positions": [],
                "mention_ids": [],
            }
        groups[key]["positions"].append(
            Position(start=m.start, end=m.end, raw=m.surface)
        )
        groups[key]["mention_ids"].append(m.id)

    counters: dict[str, int] = {}
    detections: list[Detection] = []
    det_id = 0
    for g in groups.values():
        cat = g["cat"]
        counters[cat] = counters.get(cat, 0) + 1
        placeholder = make_placeholder(cat, g["original"], counters[cat], mode)
        detections.append(
            Detection(
                id=det_id,
                cat=cat,  # type: ignore[arg-type]
                original=g["original"],
                placeholder=placeholder,
                enabled=True,
                positions=g["positions"],
                mention_ids=g["mention_ids"],
            )
        )
        det_id += 1
    return detections
