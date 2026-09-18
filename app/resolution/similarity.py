"""Pairwise similarity for categories without person identity ambiguity."""
try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None

from app.config import FUZZY_HIGH, FUZZY_MEDIUM
from app.models.schemas import Mention
from app.resolution.normalize import normalize_mention
from app.resolution.person_identity import name_parts


def fuzzy_score(a: str, b: str) -> float:
    if fuzz is not None:
        return float(fuzz.token_sort_ratio(a, b))
    from difflib import SequenceMatcher
    return float(SequenceMatcher(None, a, b).ratio() * 100)


def compute_edge(m1: Mention, m2: Mention, text: str) -> tuple[float, str, str] | None:
    if m1.cat != m2.cat:
        return None
    n1, n2 = normalize_mention(m1.surface), normalize_mention(m2.surface)
    if n1 == n2:
        return 1.0, 'alta', 'exact'
    if m1.cat == 'PERSONA':
        # Partial names need document-wide uniqueness. Pairwise fuzzy scores
        # and proximity to an identifier cannot establish person identity.
        if name_parts(m1.surface)[0] == name_parts(m2.surface)[0]:
            return 1.0, 'alta', 'name_format'
        return None
    score = fuzzy_score(n1, n2)
    if score >= FUZZY_HIGH:
        return score / 100, 'alta', 'fuzzy_high'
    if score >= FUZZY_MEDIUM:
        return score / 100, 'baja', 'fuzzy_medium'
    return None
