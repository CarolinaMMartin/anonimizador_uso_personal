from app.anonymize.apply import anonymize_text
from app.models.schemas import Detection, Position
from app.services.analyze import _prune_detections


def test_prune_keeps_user_added_persona():
    text = "BENICIO MERCEDES, Estella Marys declaró ante el tribunal."
    manual = Detection(
        id=0,
        cat="PERSONA",
        original="BENICIO MERCEDES, Estella Marys",
        placeholder="[PERSONA_1]",
        enabled=True,
        positions=[Position(start=0, end=32, raw="BENICIO MERCEDES, Estella Marys")],
        user_added=True,
    )
    pruned = _prune_detections([manual], text)
    assert len(pruned) == 1
    out = anonymize_text(text, pruned)
    assert "[PERSONA_1]" in out
    assert "BENICIO MERCEDES" not in out
