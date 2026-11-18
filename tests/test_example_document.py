"""El documento de ejemplo es ficticio, reproducible y útil como demostración."""
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import audit_repository  # noqa: E402
import make_example_document  # noqa: E402

from app.main import app  # noqa: E402

EXAMPLE = ROOT / audit_repository.EXAMPLE_DOCUMENT


def test_example_document_matches_its_generator():
    assert EXAMPLE.is_file(), "Generalo con scripts/make_example_document.py"
    found = [paragraph.text for paragraph in Document(str(EXAMPLE)).paragraphs]
    assert found == make_example_document.document_paragraphs()
    assert "ficticios" in found[0]
    assert audit_repository.check_example_document() == []


def test_example_uses_values_that_cannot_belong_to_real_people():
    text = "\n".join(make_example_document.document_paragraphs())
    dnis = re.findall(r"DNI (\d{2})\.\d{3}\.\d{3}", text)
    assert dnis and set(dnis) == {"99"}, "Rango de DNI no emitido"
    assert set(re.findall(r"\b(?:20|27|30)-(\d{2})\d{6}-\d\b", text)) == {"99"}
    assert re.findall(r"Expediente N° \d+/(\d{4})", text) == ["2099"]
    emails = re.findall(r"[\w.+-]+@[\w.-]+", text)
    assert emails and all(email.rstrip(".,").endswith(".invalid") for email in emails)
    assert "5555-01" in text, "Teléfono de un rango reservado para ficción"


def test_application_detects_the_main_categories_in_the_example():
    with TestClient(app) as client:
        uploaded = client.post("/api/upload", files={
            "file": (EXAMPLE.name, EXAMPLE.read_bytes(),
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
        assert uploaded.status_code == 200, uploaded.text
        analyzed = client.post("/api/analyze", json={
            "session_id": uploaded.json()["session_id"], "label_mode": "cat"})
        assert analyzed.status_code == 200, analyzed.text
    detections = analyzed.json()["detections"]
    categories = Counter(item["cat"] for item in detections)
    for category in ("PERSONA", "DNI", "CUIT", "DOMICILIO", "EMAIL", "TELEFONO", "EXPEDIENTE"):
        assert categories[category] >= 1, f"El ejemplo debería mostrar {category}"
    originals = {item["original"] for item in detections}
    assert "Marcelina Aurora Quintanilla Ordóñez" in originals
    assert "99.812.345" in originals


def test_audit_admits_only_the_fictitious_example():
    assert audit_repository.is_unexpected_data_file("docs/ejemplos/escrito_ficticio.docx") is False
    assert audit_repository.is_unexpected_data_file("docs/ejemplos/otro.docx") is True
    assert audit_repository.is_unexpected_data_file("docs/ejemplos/ESCRITO_FICTICIO.DOCX") is True
    assert audit_repository.is_unexpected_data_file("escrito_ficticio.docx") is True
    assert audit_repository.is_unexpected_data_file("data/expediente.pdf") is True
    assert audit_repository.is_unexpected_data_file("docs/DEPLOY.md") is False


def test_audit_rejects_an_example_replaced_by_another_document(tmp_path):
    target = tmp_path / audit_repository.EXAMPLE_DOCUMENT
    target.parent.mkdir(parents=True)
    assert audit_repository.check_example_document(tmp_path) == []  # ausente: nada que revisar

    shutil.copyfile(EXAMPLE, target)
    assert audit_repository.check_example_document(tmp_path) == []

    replaced = Document()
    replaced.add_paragraph("Juan Pérez, DNI 20.123.456, expediente real.")
    replaced.save(target)
    errors = audit_repository.check_example_document(tmp_path)
    assert len(errors) == 1 and "differs" in errors[0]

    target.write_bytes(b"no es un docx")
    errors = audit_repository.check_example_document(tmp_path)
    assert len(errors) == 1 and "Unreadable" in errors[0]
