"""Similitud textual y reglas de identidad."""
try:
    from rapidfuzz import fuzz  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    fuzz = None  # type: ignore[assignment]

from app.config import FUZZY_HIGH, FUZZY_MEDIUM, PROXIMITY_CHARS
from app.models.schemas import Mention
from app.resolution.normalize import (
    get_initials,
    get_surnames,
    normalize_mention,
    tokenize_name,
)


def fuzzy_score(a: str, b: str) -> float:
    if fuzz is not None:
        return float(fuzz.token_sort_ratio(a, b))
    # Fallback cuando rapidfuzz no está disponible (dev tools / linters).
    from difflib import SequenceMatcher

    return float(SequenceMatcher(None, a, b).ratio() * 100)


def _token_is_initial(tok: str) -> bool:
    t = tok.replace(".", "").strip()
    return len(t) <= 2


def initials_match(a_tokens: list[str], b_tokens: list[str]) -> bool:
    if not a_tokens or not b_tokens:
        return False
    if not shared_surname(a_tokens, b_tokens):
        return False
    a_init = get_initials(a_tokens)
    b_init = get_initials(b_tokens)
    if len(a_init) < 1 or len(b_init) < 1:
        return False
    # M. A. Benitez vs Marcos Adrian Benitez (m vs marcos pero mismo apellido)
    if any(_token_is_initial(t) for t in a_tokens) or any(_token_is_initial(t) for t in b_tokens):
        return a_init[0] == b_init[0] or a_init in b_init or b_init in a_init
    if a_tokens[0] != b_tokens[0]:
        return False
    shorter, longer = (a_init, b_init) if len(a_init) <= len(b_init) else (b_init, a_init)
    return longer.startswith(shorter) or shorter == longer[: len(shorter)]


def surname_fuzzy_match(t1: list[str], t2: list[str], n1: str, n2: str) -> bool:
    """Mismo apellido + similitud alta (typos Ferreyra/Ferreira)."""
    if not shared_surname(t1, t2):
        return False
    return fuzzy_score(n1, n2) >= FUZZY_MEDIUM


def shared_surname(a_tokens: list[str], b_tokens: list[str]) -> bool:
    sa = get_surnames(a_tokens)
    sb = get_surnames(b_tokens)
    return bool(sa & sb) and len(sa) > 0


def proximity(m1: Mention, m2: Mention, text: str, max_chars: int = PROXIMITY_CHARS) -> bool:
    if m1.cat != "PERSONA" or m2.cat != "PERSONA":
        return False
    dist = abs(m1.start - m2.start)
    if dist <= max_chars:
        return True
    # mismo párrafo
    para_start = text.rfind("\n", 0, min(m1.start, m2.start))
    para_end = text.find("\n", max(m1.end, m2.end))
    if para_end == -1:
        para_end = len(text)
    return m1.start >= para_start and m2.start <= para_end


def identifier_near_name(
    id_mention: Mention, name_mention: Mention, max_chars: int = PROXIMITY_CHARS
) -> bool:
    if id_mention.cat not in ("DNI", "CUIT"):
        return False
    if name_mention.cat != "PERSONA":
        return False
    return abs(id_mention.start - name_mention.start) <= max_chars


def link_personas_near_identifier(
    mentions: list[Mention], max_chars: int = PROXIMITY_CHARS
) -> list[tuple[str, str, float, str]]:
    """Enlaza personas que comparten un DNI/CUIT cercano."""
    edges: list[tuple[str, str, float, str]] = []
    ids = [m for m in mentions if m.cat in ("DNI", "CUIT")]
    personas = [m for m in mentions if m.cat == "PERSONA"]
    for ident in ids:
        nearby = [p for p in personas if identifier_near_name(ident, p, max_chars)]
        for i, p1 in enumerate(nearby):
            for p2 in nearby[i + 1 :]:
                # Evitar unir personas no relacionadas solo por cercanía al mismo ID.
                # Compartir apellido NO alcanza (dos familiares —p. ej. Sandra y
                # Cristian Villarreal— pueden estar cerca del mismo CUIT). Se exige
                # que sean la misma identidad: mismo nombre/iniciales o fuzzy alto.
                n1 = normalize_mention(p1.surface)
                n2 = normalize_mention(p2.surface)
                t1 = tokenize_name(n1)
                t2 = tokenize_name(n2)
                score = fuzzy_score(n1, n2)
                if initials_match(t1, t2) or score >= FUZZY_HIGH:
                    edges.append((p1.id, p2.id, 0.95, "shared_identifier"))
    return edges


def compute_edge(
    m1: Mention, m2: Mention, text: str
) -> tuple[float, str, str] | None:
    if m1.cat != m2.cat:
        return None

    n1 = normalize_mention(m1.surface)
    n2 = normalize_mention(m2.surface)
    if n1 == n2:
        return (1.0, "alta", "exact")

    score = fuzzy_score(n1, n2)
    t1 = tokenize_name(n1)
    t2 = tokenize_name(n2)

    # Reglas más estrictas para PERSONA: evitar clusters por "cadenas" de fuzzy.
    if m1.cat == "PERSONA":
        if initials_match(t1, t2):
            return (0.93, "alta", "initials_match")

        if surname_fuzzy_match(t1, t2, n1, n2):
            conf = "alta" if score >= FUZZY_HIGH else "media"
            return (max(score, 88) / 100, conf, "shared_surname")

        if shared_surname(t1, t2) and score >= FUZZY_MEDIUM and len(t1) >= 2 and len(t2) >= 2:
            conf = "alta" if score >= FUZZY_HIGH else "media"
            return (score / 100, conf, "shared_surname")

        # Proximidad solo si además comparten apellido y el fuzzy es alto.
        if proximity(m1, m2, text) and shared_surname(t1, t2) and score >= FUZZY_HIGH:
            return (score / 100, "media", "proximity")

        return None

    # Para otras categorías, fuzzy sigue siendo útil.
    if score >= FUZZY_HIGH:
        return (score / 100, "alta", "fuzzy_high")

    if score >= FUZZY_MEDIUM:
        return (score / 100, "baja", "fuzzy_medium")

    return None
