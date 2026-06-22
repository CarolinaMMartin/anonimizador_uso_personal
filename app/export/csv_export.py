"""Exportación CSV de equivalencias."""
import csv
import io

from app.models.schemas import Detection

# Caracteres que las planillas (Excel, Sheets, LibreOffice) interpretan
# como inicio de fórmula. Se neutralizan anteponiendo un apóstrofo.
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _sanitize(value: str) -> str:
    """Evita inyección de fórmulas CSV en aplicaciones de planillas."""
    if value and value[0] in _FORMULA_PREFIXES:
        return "'" + value
    return value


def build_csv_bytes(detections: list[Detection]) -> bytes:
    rows = [["Tipo", "Original", "Sustitución", "Ocurrencias", "Activa", "Cluster"]]
    for d in detections:
        rows.append(
            [
                _sanitize(d.cat),
                _sanitize(d.original),
                _sanitize(d.placeholder),
                str(len(d.positions)),
                "Sí" if d.enabled else "No",
                _sanitize(d.cluster_id or ""),
            ]
        )
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerows(rows)
    return ("\ufeff" + buf.getvalue()).encode("utf-8")
