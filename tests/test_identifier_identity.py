import pytest

from app.anonymize.placeholders import build_detections_from_mentions
from app.models.schemas import Mention
from app.resolution.cluster import build_clusters
from app.resolution.similarity import compute_edge


def mentions(cat, values):
    return [Mention(id=f'm{i}', cat=cat, surface=value, start=i * 100, end=i * 100 + len(value))
            for i, value in enumerate(values)]


@pytest.mark.parametrize('cat, values', [
    ('DNI', ['30.456.789', '30.456.788']),
    ('CUIT', ['20-30456789-1', '20-30456788-1']),
    ('TELEFONO', ['11-5555-1234', '11-5555-1235']),
    ('PATENTE', ['AB123CD', 'AB124CD']),
    ('EXPEDIENTE', ['EX-2026-12345678', 'EX-2026-12345679']),
    ('OTRO', ['POL-12345678', 'POL-12345679']),
    ('OTRO', ['https://example.test/ABCD1234', 'https://example.test/abcd1234']),
    ('OTRO', ['https://example.test/a.b', 'https://example.test/ab']),
    ('EMAIL', ['ana.perez@example.test', 'anaperez@example.test']),
])
def test_distinct_identifiers_never_suggest_the_same_identity(cat, values):
    items = mentions(cat, values)
    assert compute_edge(*items, '') is None
    assert build_clusters(items, '') == []
    assert len(build_detections_from_mentions(items, 'cat')) == 2


@pytest.mark.parametrize('cat, values', [
    ('DNI', ['30.456.789', '30456789', '30 456 789']),
    ('CUIT', ['20-30456789-1', '20304567891']),
    ('TELEFONO', ['+54 (11) 5555-1234', '+541155551234']),
    ('PATENTE', ['AB 123 CD', 'ab123cd', 'AB-123-CD']),
])
def test_formatting_variants_use_one_placeholder_without_losing_positions(cat, values):
    items = mentions(cat, values)
    rows = build_detections_from_mentions(items, 'cat')
    assert len(rows) == 1
    assert [position.raw for position in rows[0].positions] == values
