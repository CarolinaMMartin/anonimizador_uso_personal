"""Find bounded name variants learned from validated people in this document.

Catalogs and NER supply the first pass. This pass reuses those names to find
otherwise unknown components and shortened forms; it never learns new names
from its own results or combines tokens from different people.
"""
import re
from itertools import combinations

from app.detection.dictionaries import STOPWORDS_FRASE
from app.detection.filters import _looks_like_narrative, get_formulas
from app.detection.person_context import is_vehicle_name
from app.detection.regex_ar import RawItem
from app.resolution.normalize import normalize_text
from app.resolution.person_identity import name_parts

_WORD = re.compile(r"[^\W\d_](?:[^\W\d_]|[\u0300-\u036f])*(?:['’ʼ][^\W\d_](?:[^\W\d_]|[\u0300-\u036f])*)*", re.UNICODE)
_PARTICLES = {'de', 'del', 'la', 'las', 'los', 'y'}
_HONOR = re.compile(r'\b(?:sr\.?|sra\.?|srta\.?|dr\.?|dra\.?|don|do[ñn]a|se[ñn]or|se[ñn]ora)\s*$', re.I)
_END = object()


def _normal(word: str) -> str:
    return normalize_text(word).replace('’', "'").replace('ʼ', "'")


def _initial(word: str) -> bool:
    return len(word) == 1 and 'a' <= word <= 'z'


def _gap_allowed(gap: str, previous: str, allow_comma: bool) -> bool:
    gap = _normal(gap)
    if _initial(previous):
        gap = gap.lstrip('.')
    if allow_comma:
        gap = gap.replace(',', '')
    gap = re.sub(r'\b(?:de|del|la|las|los|y)\b', '', gap)
    return bool(gap == '' or re.fullmatch(r'[\s\-‐‑–—]+', gap))


def detect_document_aliases(text: str, seeds: list[RawItem], protected: list[RawItem],
                            session_id: str | None = None) -> list[RawItem]:
    from app.services.analysis_cancel import check_cancel

    trie: dict = {}
    explicit_orders: set[tuple[str, ...]] = set()
    blocked = STOPWORDS_FRASE | get_formulas()
    for seed in seeds:
        name, reverse = name_parts(seed.original)
        if not 2 <= len(name) <= 8:
            continue
        # Particles are structural only where this particular seed supplies
        # them. A conjunction in prose must not become part of a learned name.
        seed_words = [(match, _normal(match.group())) for match in _WORD.finditer(seed.original)
                      if _normal(match.group()) not in _PARTICLES]
        connectors: dict[tuple[str, str], set[tuple[str, ...]]] = {}
        for (left, before), (right, after) in zip(seed_words, seed_words[1:]):
            gap = seed.original[left.end():right.start()]
            particles = tuple(_normal(match.group()) for match in _WORD.finditer(gap))
            if not particles or any(word not in _PARTICLES for word in particles):
                continue
            for first_word in (before, before[0]):
                for second_word in (after, after[0]):
                    connectors.setdefault((first_word, second_word), set()).add(particles)
        # Ordered subsets cover omitted given names/surnames. Every word comes
        # from this particular name; there is no cross-person phrase generator.
        variants = {tuple(name[index] for index in subset)
                    for length in range(1, len(name) + 1)
                    for subset in combinations(range(len(name)), length)}
        if reverse:
            variants.add(reverse)
            explicit_orders.add(reverse)
        # Abbreviated first given name, retaining complete identifying words.
        if not _initial(name[0]):
            variants.update({(name[0][0], *variant[1:]) for variant in variants
                             if len(variant) > 1 and variant[0] == name[0]})
            variants.update({tuple(word[0] if index < len(variant) - 1 else word
                                   for index, word in enumerate(variant))
                             for variant in variants if len(variant) > 1 and variant[0] in (name[0], name[0][0])})
        for variant in variants:
            if not variant or all(_initial(word) for word in variant):
                continue
            if any(word in blocked for word in variant):
                continue
            node = trie
            for word in variant:
                node = node.setdefault(word, {})
            pattern = tuple(frozenset(connectors.get(pair, ()))
                            for pair in zip(variant, variant[1:]))
            node.setdefault(_END, set()).add(pattern)

    if not trie:
        return []
    words = [(match, _normal(match.group())) for match in _WORD.finditer(text)
             if _normal(match.group()) not in _PARTICLES]
    spans = sorted((item.start, item.end) for item in protected)
    protected_index = 0
    results: list[RawItem] = []
    for index, (first, word) in enumerate(words):
        if index % 1024 == 0:
            check_cancel(session_id)
        if word not in trie or (first.start() and (text[first.start() - 1].isalnum() or text[first.start() - 1] == '_')):
            continue
        node = trie
        sequence: list[str] = []
        found_connectors: list[tuple[str, ...]] = []
        previous = None
        for last, current in words[index:index + 8]:
            if current not in node:
                break
            if previous:
                gap = text[previous.end():last.start()]
                if not _gap_allowed(gap, sequence[-1], True):
                    break
                found_connectors.append(tuple(_normal(match.group()) for match in _WORD.finditer(gap)))
            node = node[current]
            sequence.append(current)
            previous = last
            if _END not in node:
                continue
            if not any(all(not actual or actual in permitted
                           for actual, permitted in zip(found_connectors, pattern))
                       for pattern in node[_END]):
                continue
            start, end = first.start(), last.end()
            if end < len(text) and (text[end].isalnum() or text[end] == '_'):
                continue
            raw = text[start:end]
            # Commas are allowed only for the complete surname-first order
            # explicitly supplied by a seed, not arbitrary lists of people.
            if ',' in raw and (tuple(sequence) not in explicit_orders or raw.count(',') != 1):
                continue
            matched_words = [match.group() for match in _WORD.finditer(raw)
                             if _normal(match.group()) not in _PARTICLES]
            if not all(token[0].isupper() for token in matched_words):
                if not _HONOR.search(text[max(0, start - 45):start]):
                    continue
            if _looks_like_narrative(raw, max_chars=120, max_words=12):
                continue
            while protected_index < len(spans) and spans[protected_index][1] <= start:
                protected_index += 1
            if protected_index < len(spans) and spans[protected_index][0] < end:
                continue
            preceding = words[index - 1][0] if index else None
            vehicle_start = preceding.start() if preceding else start
            if is_vehicle_name(raw, text, start) or is_vehicle_name(text[vehicle_start:end], text, vehicle_start):
                continue
            results.append(RawItem('PERSONA', raw, start, end, 'document_alias'))
    return results
