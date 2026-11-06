from app.anonymize.apply import anonymize_text
from app.models.schemas import Detection, Position


def test_export_keeps_user_added_persona():
    text = "BENICIO MERCEDES, Estella Marys declaró ante el tribunal."
    manual = Detection(
        id=0,
        cat="PERSONA",
        original="BENICIO MERCEDES, Estella Marys",
        placeholder="[PERSONA_1]",
        enabled=True,
        positions=[Position(start=0, end=len("BENICIO MERCEDES, Estella Marys"), raw="BENICIO MERCEDES, Estella Marys")],
        user_added=True,
    )
    out = anonymize_text(text, [manual])
    assert "[PERSONA_1]" in out
    assert "BENICIO MERCEDES" not in out
    assert 'declaró ante el tribunal.' in out
