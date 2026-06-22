"""Tests de exportación PDF."""
from app.export.pdf_export import build_pdf_bytes


def test_build_pdf_bytes_non_empty():
    data = build_pdf_bytes(["Primer párrafo.", "Segundo párrafo con [PERSONA_1]."])
    assert data.startswith(b"%PDF")
    assert len(data) > 200
