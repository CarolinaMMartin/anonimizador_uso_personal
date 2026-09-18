"""Document-wide person identity suggestions, independent of catalog coverage.

Full forms provide anchors. Short forms and initials may join an anchor only
when exactly one most-specific identity fits the whole mention. In particular,
an ambiguous surname must never connect two otherwise different people.
"""
from collections import defaultdict

from app.models.schemas import Mention
from app.resolution.normalize import TREATMENTS, normalize_mention, normalize_text, tokenize_name

Name = tuple[str, ...]
Edge = tuple[str, str, float, str]


def name_parts(surface: str) -> tuple[Name, Name | None]:
    normalized = TREATMENTS.sub('', normalize_text(surface)).strip()
    if normalized.count(',') == 1:
        surname, given = normalized.split(',', 1)
        surnames = tuple(tokenize_name(surname))
        givens = tuple(tokenize_name(TREATMENTS.sub('', given.strip())))
        if surnames and givens:
            return givens + surnames, surnames + givens
    return tuple(tokenize_name(normalized)), None


def _specificity(name: Name) -> tuple[int, int]:
    return len(name), sum(not _is_initial(token) for token in name)


def _is_initial(token: str) -> bool:
    return len(token) == 1 and 'a' <= token <= 'z'


def is_name_variant(short: Name, full: Name) -> bool:
    """Match every supplied token in order; never fuzz different full words.

Only one-letter tokens are initials. At least one complete word must agree;
initials alone do not identify a person. Missing tokens can represent omitted
given names or surnames, but supplied contradictory tokens cannot be ignored.
    """
    if not short or not full or _specificity(short) > _specificity(full):
        return False
    if not any(not _is_initial(token) and token in full for token in short):
        return False
    index = 0
    for token in full:
        if index < len(short) and (
            short[index] == token or (_is_initial(short[index]) and token.startswith(short[index]))
        ):
            index += 1
    return index == len(short)


def person_edges(mentions: list[Mention]) -> list[Edge]:
    parsed = [(mention, *name_parts(mention.surface)) for mention in mentions]
    # An explicit comma supplies order evidence for otherwise unmarked forms.
    reversed_forms: dict[Name, set[Name]] = defaultdict(set)
    surname_blocks: dict[Name, set[Name]] = defaultdict(set)
    for mention, canonical, reversed_name in parsed:
        if reversed_name:
            reversed_forms[reversed_name].add(canonical)
            surname_length = len(tokenize_name(normalize_mention(mention.surface).split(',', 1)[0]))
            surname_blocks[canonical].add(canonical[-surname_length:])

    def compatible(short: Name, full: Name) -> bool:
        if not is_name_variant(short, full):
            return False
        if len(short) == 1:
            return True
        same_start = short[0] == full[0] or (_is_initial(short[0]) and full[0].startswith(short[0]))
        # A multiword surname-only form needs surname-order evidence, rather
        # than treating a different given name as an omitted first given name.
        surname_only = any(is_name_variant(short, block) for block in surname_blocks[full])
        if not (same_start or surname_only):
            return False
        if surname_blocks[short] and surname_blocks[full]:
            return any(is_name_variant(left, right)
                       for left in surname_blocks[short] for right in surname_blocks[full])
        return True

    units: dict[Name, list[Mention]] = defaultdict(list)
    for mention, name, reversed_name in parsed:
        if reversed_name is None and len(reversed_forms.get(name, ())) == 1:
            name = next(iter(reversed_forms[name]))
        if name:
            units[name].append(mention)

    # Optional given-name evidence can delimit a natural-order compound
    # surname. Unknown names still match exact formats and single components.
    from app.detection.dictionaries import get_nombres
    given_names = get_nombres()
    for name in units:
        if name in surname_blocks or name[0] not in given_names:
            continue
        boundary = 1
        while boundary < len(name) - 1 and (name[boundary] in given_names or _is_initial(name[boundary])):
            boundary += 1
        if boundary < len(name):
            surname_blocks[name].add(name[boundary:])

    # Process most-specific forms first. Candidate lookup requires an exact
    # full word and avoids comparing every occurrence to every other occurrence.
    names = sorted(units, key=lambda name: (-len(name), -_specificity(name)[1], name))
    index: dict[str, dict[tuple[int, int], set[Name]]] = defaultdict(lambda: defaultdict(set))
    roots: dict[Name, set[Name]] = {}
    for name in names:
        candidates: set[Name] = set()
        for token in name:
            if not _is_initial(token):
                for specificity, bucket in index[token].items():
                    if specificity > _specificity(name):
                        candidates.update(bucket)
        parents = [other for other in candidates
                   if _specificity(other) > _specificity(name) and compatible(name, other)]
        roots[name] = set().union(*(roots[parent] for parent in parents)) if parents else {name}
        for token in name:
            if not _is_initial(token):
                index[token][_specificity(name)].add(name)

    edges: list[Edge] = []
    for name, members in units.items():
        members.sort(key=lambda mention: (mention.start, mention.end, mention.id))
        representative = members[0]
        for member in members[1:]:
            reason = 'exact' if normalize_mention(member.surface) == normalize_mention(representative.surface) else 'name_format'
            edges.append((representative.id, member.id, 1.0, reason))
        if roots[name] == {name} or len(roots[name]) != 1:
            continue
        root = next(iter(roots[name]))
        # Check directly against the final anchor too. This prevents omissions
        # in intermediate forms from hiding contradictory information.
        if not compatible(name, root):
            continue
        reason = 'initials_match' if any(_is_initial(token) for token in name) else 'unique_partial_name'
        edges.append((representative.id, units[root][0].id, 0.88, reason))
    return edges
