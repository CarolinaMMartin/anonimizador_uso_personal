"""Explicit name signals complement finite dictionaries without accepting prose."""
import re
from functools import lru_cache

from app.resolution.normalize import normalize_text

_WORD = r"[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ'’\-]*\.?"
_PARTICLE = r"(?:de|del|la|las|los|y)"
_NAME = rf"{_WORD}(?:[ \t]+(?:{_WORD}|{_PARTICLE})){{0,7}}"
_SIGNATURE_RE = re.compile(rf"(?i:firmado\s+por|firma|aclaraci[oó]n)[ \t]*:[ \t]*(?P<name>{_NAME})")
_ROLE = r"(?:JUE[ZS]A?|VICEPRESIDENT[EA]|PRESIDENT[EA]|PROSECRETARI[OA]|SECRETARI[OA])\b"
_ROLE_AFTER_RE = re.compile(rf"\s*(?:,\s*|\n\s*){_ROLE}", re.IGNORECASE)
_FOOTER_RE = re.compile(rf"(?m)^[ \t]*(?P<name>{_NAME})(?=\s*(?:,\s*|\n\s*){_ROLE})", re.IGNORECASE)
_ACTOR_RE = re.compile(
    rf"\b(?P<name>{_WORD},?(?:\s+(?:{_WORD},?|{_PARTICLE})){{1,8}})\s+(?i:c\s*\.?/)"
)
_HONOR_BEFORE_RE = re.compile(r"\b(?:sr\.?|sra\.?|srta\.?|dr\.?|dra\.?|se[ñn]or|se[ñn]ora|don|do[ñn]a)\s*$", re.IGNORECASE)
_PARTICLES = {'de', 'del', 'la', 'las', 'los', 'y'}
_NOT_NAMES = {'juez', 'jueza', 'fiscal', 'general', 'camara', 'tribunal', 'secretario',
              'prosecretario', 'vicepresidente', 'presidente', 'ministro', 'nacional',
              'judicial', 'poder', 'comercial', 'sala', 'conste'}
_VEHICLE_BRANDS = {'fiat', 'ford', 'chevrolet', 'renault', 'toyota', 'volkswagen',
                   'peugeot', 'citroen', 'honda', 'nissan', 'jeep', 'audi'}
_VEHICLE_CONTEXT_RE = re.compile(r"\b(?:veh[ií]culo|autom[oó]vil|automotor|rodado|marca|modelo)\b", re.IGNORECASE)


def name_tokens(surface: str) -> tuple[str, ...]:
    return tuple(normalize_text(token.rstrip('.,')) for token in surface.split()
                 if normalize_text(token.rstrip('.,')) not in _PARTICLES and len(token.rstrip('.,')) > 1)


def _name_shape(surface: str, minimum: int = 2) -> bool:
    cleaned = re.sub(r",\s*", " ", surface).strip()
    if not re.fullmatch(rf"{_WORD}(?:\s+(?:{_WORD}|{_PARTICLE}))*", cleaned):
        return False
    tokens = name_tokens(surface)
    return minimum <= len(tokens) <= 6 and not any(token in _NOT_NAMES for token in tokens)


@lru_cache(maxsize=1)
def signature_names(text: str) -> tuple[tuple[str, ...], ...]:
    return tuple(dict.fromkeys(name_tokens(match.group('name'))
                               for pattern in (_SIGNATURE_RE, _FOOTER_RE)
                               for match in pattern.finditer(text)
                               if _name_shape(match.group('name'))))


def signature_spans(text: str) -> list[tuple[int, int, str]]:
    spans = []
    accent_classes = {'a': '[aá]', 'e': '[eé]', 'i': '[ií]', 'o': '[oó]', 'u': '[uúü]', 'n': '[nñ]'}
    for tokens in signature_names(text):
        words = [''.join(accent_classes.get(char, re.escape(char)) for char in token) for token in tokens]
        separator = r"\s+(?:(?:de|del|la|las|los|y)\s+)*(?:[A-ZÁÉÍÓÚÜÑ]\.\s+)*"
        pattern = re.compile(r'\b' + separator.join(words) + r'(?!\w)', re.IGNORECASE)
        for match in pattern.finditer(text):
            spans.append((match.start(), match.end(), match.group()))
    return spans


def actor_spans(text: str) -> list[tuple[int, int, str]]:
    return [(match.start('name'), match.end('name'), match.group('name'))
            for match in _ACTOR_RE.finditer(text) if _name_shape(match.group('name'))]


def is_contextual_person(surface: str, text: str, start: int) -> bool:
    if name_tokens(surface) in signature_names(text):
        return True
    if not _name_shape(surface, minimum=1):
        return False
    left = text[max(0, start - 50):start]
    right = text[start + len(surface):start + len(surface) + 100]
    return bool(_HONOR_BEFORE_RE.search(left) or _ROLE_AFTER_RE.match(right) or
                re.match(r"\s*[.,]?\s*c\s*\.?/", right, re.IGNORECASE))


def is_vehicle_name(surface: str, text: str, start: int) -> bool:
    tokens = name_tokens(surface)
    return bool(tokens and tokens[0] in _VEHICLE_BRANDS and
                _VEHICLE_CONTEXT_RE.search(text[max(0, start - 130):start]))
