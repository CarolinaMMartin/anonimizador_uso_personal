"""Exportación CSV de equivalencias."""
import csv
import io

from app.models.schemas import Detection


def build_csv_bytes(detections: list[Detection]) -> bytes:
    rows = [["Tipo", "Original", "Sustitución", "Ocurrencias", "Activa", "Cluster"]]
    for d in detections:
        rows.append(
            [
                d.cat,
                d.original,
                d.placeholder,
                str(len(d.positions)),
                "Sí" if d.enabled else "No",
                d.cluster_id or "",
            ]
        )
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerows(rows)
    return ("\ufeff" + buf.getvalue()).encode("utf-8")
