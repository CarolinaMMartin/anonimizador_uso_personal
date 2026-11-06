"""Separadores estructurales de partes y materia de una carátula."""
import re
from bisect import bisect_left
from functools import lru_cache


PARTY_SEPARATOR = r"(?:c\s*(?:\.\s*)?/|contra\b)"
SUBJECT_SEPARATOR = r"(?:s\s*(?:\.\s*)?/|sobre\b)"
PARTY_SEPARATOR_RE = re.compile(rf"(?<!\w){PARTY_SEPARATOR}", re.IGNORECASE)
SUBJECT_SEPARATOR_RE = re.compile(rf"(?<!\w){SUBJECT_SEPARATOR}", re.IGNORECASE)
CASE_CONNECTOR_RE = re.compile(
    rf"(?<!\w)(?P<party>{PARTY_SEPARATOR})|(?<!\w)(?P<subject>{SUBJECT_SEPARATOR})",
    re.IGNORECASE,
)

_PARTY = (
    rf"(?!(?:{PARTY_SEPARATOR}|{SUBJECT_SEPARATOR}))[A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑa-záéíóúüñ,&.\-'’]*"
    rf"(?:\s+(?!(?:{PARTY_SEPARATOR}|{SUBJECT_SEPARATOR}))[A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑa-záéíóúüñ,&.\-'’]*){{0,11}}"
)
_VERSUS_CASE_RE = re.compile(
    rf"(?<!\w)(?P<actor>{_PARTY})\s+(?P<versus>{PARTY_SEPARATOR})\s*"
    rf"(?P<defendant>{_PARTY})(?=\s*(?P<subject>{SUBJECT_SEPARATOR})|[.;,\n]|$)",
    re.IGNORECASE,
)
_SUBJECT_CASE_RE = re.compile(
    rf"(?<!\w)(?P<actor>{_PARTY})\s+(?P<subject>{SUBJECT_SEPARATOR})",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def _case_parties(text: str) -> tuple[tuple[tuple[int, int, str], ...], frozenset[tuple[int, int]]]:
    spans = {}
    explicit = set()
    for pattern, groups in ((_VERSUS_CASE_RE, ('actor', 'defendant')),
                            (_SUBJECT_CASE_RE, ('actor',))):
        for match in pattern.finditer(text):
            subject = match.group('subject') or ''
            versus = match.groupdict().get('versus') or ''
            strong = '/' in versus or '/' in subject or bool(versus and subject)
            for group in groups:
                raw = match.group(group)
                value = raw.strip(' ,.;')
                if not value:
                    continue
                start = match.start(group) + len(raw) - len(raw.lstrip())
                end = start + len(value)
                spans[start, end] = (start, end, value)
                if strong:
                    explicit.add((start, end))
    return tuple(sorted(spans.values())), frozenset(explicit)


def case_party_spans(text: str) -> list[tuple[int, int, str]]:
    return list(_case_parties(text)[0])


def is_explicit_case_party(surface: str, text: str, start: int) -> bool:
    end = start + len(surface)
    return (start, end) in _case_parties(text)[1] and text[start:end] == surface


@lru_cache(maxsize=1)
def _connector_offsets(text: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    spans = [match.span() for match in CASE_CONNECTOR_RE.finditer(text)]
    return tuple(start for start, _ in spans), tuple(end for _, end in spans)


def overlaps_case_connector(surface: str, text: str = '', start: int = 0) -> bool:
    if not text or text[start:start + len(surface)] != surface:
        return bool(CASE_CONNECTOR_RE.search(surface))
    starts, ends = _connector_offsets(text)
    index = bisect_left(starts, start + len(surface)) - 1
    return index >= 0 and start < ends[index]


def split_case_parties(value: str, offset: int = 0) -> list[tuple[str, int, int]]:
    spans = []
    start = 0

    def append(end: int) -> None:
        raw = value[start:end]
        cleaned = raw.strip(" \t\r\n\"'“”«»,.;:")
        if len(cleaned) < 3:
            return
        left = start + raw.index(cleaned)
        spans.append((cleaned, offset + left, offset + left + len(cleaned)))

    for connector in CASE_CONNECTOR_RE.finditer(value):
        append(connector.start())
        if connector.group('subject') is not None:
            return spans
        start = connector.end()
    append(len(value))
    return spans
