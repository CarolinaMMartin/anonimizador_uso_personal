import pytest

from app.anonymize.apply import anonymize_text, build_highlights
from app.models.schemas import Detection, Position


def detection(index, text, start, end, enabled=True):
    return Detection(id=index, cat="PERSONA", original=text[start:end],
                     placeholder=f"[PERSONA_{index + 1}]", enabled=enabled,
                     positions=[Position(start=start, end=end, raw=text[start:end])])


@pytest.mark.parametrize("intervals", [
    [(0, 10), (5, 16)],
    [(5, 16), (0, 10)],
    [(0, 4), (0, 16), (5, 10)],
    [(0, 4), (4, 10), (10, 16)],
    [(0, 8), (5, 12), (10, 16)],
])
def test_highlights_cover_the_same_characters_as_anonymization(intervals):
    text = "Juan Perez Gomez declaró."
    detections = [detection(index, text, start, end) for index, (start, end) in enumerate(intervals)]
    original_positions = [item.model_dump() for item in detections]
    highlights = build_highlights(text, detections)
    covered = {position for item in highlights for position in range(item["start"], item["end"])}
    assert covered == set(range(16))
    assert all(left["end"] <= right["start"] for left, right in zip(highlights, highlights[1:]))
    assert "Gomez" not in anonymize_text(text, detections)
    assert [item.model_dump() for item in detections] == original_positions


def test_highlights_and_export_choose_the_longest_interval_at_the_same_start():
    text = "📄 Juan Perez Gomez declaró."
    rows = [detection(0, text, 2, 6), detection(1, text, 2, 18), detection(2, text, 7, 12)]
    highlights = build_highlights(text, rows)
    assert len(highlights) == 1
    assert text[highlights[0]["start"]:highlights[0]["end"]] == "Juan Perez Gomez"
    assert highlights[0]["placeholder"] == "[PERSONA_2]"
    assert anonymize_text(text, rows) == "📄 [PERSONA_2] declaró."


def test_disabled_detection_does_not_extend_highlights():
    text = "Juan Perez Gomez declaró."
    rows = [detection(0, text, 0, 10), detection(1, text, 5, 16, enabled=False)]
    assert build_highlights(text, rows)[0]["end"] == 10


def test_invalid_highlight_positions_are_reported():
    text = "Juan Perez"
    invalid = detection(0, text, 0, 30)
    with pytest.raises(ValueError, match="Posición"):
        build_highlights(text, [invalid])
