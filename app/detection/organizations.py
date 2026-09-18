"""Bounded company names and qualified judicial institution names."""
import re

from app.detection.dictionaries import SUFIJOS_EMPRESA

_CAPITAL_WORD = r"[A-ZÁÉÍÓÚÜÑ][\wÁÉÍÓÚÜÑáéíóúüñ&'’\-.]*"
_SUFFIX = rf"(?i:{SUFIJOS_EMPRESA}|S\.?A\.?C\.?)"
_COMPANY_WORD = rf"(?!{_SUFFIX}(?!\w))(?:{_CAPITAL_WORD}|(?i:de|del|la|las|los|y|e|para|fines|determinados))"
_COMPANY_RE = re.compile(rf"\b{_CAPITAL_WORD}(?:\s+{_COMPANY_WORD}){{0,11}}\s+{_SUFFIX}(?!\w)")
_HEADER_PREFIX_RE = re.compile(
    r"^(?:Comercial[ \t]*\n\s*|Sala[ \t]+(?:[A-Z]|[IVXLC]+|\d+)[ \t]*\n\s*|[IVXLC]+\.[ \t]+)",
    re.IGNORECASE,
)
_PROSE_PREFIX_RE = re.compile(
    r"\b(?:confirmar\s+la\s+responsabilidad\s+de|que\s+la\s+responsabilidad\s+de|"
    r"rechaza\s+el\s+agravio\s+de|las\s+de\s+Alzada\s+a|en\s+el\s+caso\s+de|"
    r"de\s+ahorro\s+administrado\s+por|no\s+media\s+relaci[oó]n\s+contractual\s+entre|"
    r"una\s+empleada\s+de\s+la\s+concesionaria|el\s+se[ñn]or\s+\w+\s+adquiri[oó]\s+de|"
    r"el\s+expediente\s+surge\s+que|con\s+costas|esta\s+instancia\s+la\s+responsabilidad\s+de)\s+",
    re.IGNORECASE,
)


def company_spans(text: str) -> list[tuple[int, int, str]]:
    spans = []
    for match in _COMPANY_RE.finditer(text):
        start, end = match.span()
        value = text[start:end]
        if re.search(r"\b(?:SA|SRL|SAS|SAU|SAC)\.$", value, re.IGNORECASE):
            end -= 1  # preserve the sentence's full stop after an undotted suffix
            value = text[start:end]
        prefixes = list(_PROSE_PREFIX_RE.finditer(value))
        if prefixes:
            start += prefixes[-1].end()
            value = text[start:end]
        while prefix := _HEADER_PREFIX_RE.match(value):
            start += prefix.end()
            value = text[start:end]
        # A header removal must leave a complete legal name, not a suffix alone.
        if _COMPANY_RE.fullmatch(value):
            spans.append((start, end, value))
    return spans


def is_company_name(surface: str) -> bool:
    return bool(_COMPANY_RE.fullmatch(surface.strip())) and not bool(
        _HEADER_PREFIX_RE.match(surface.strip()) or _PROSE_PREFIX_RE.search(surface))


_ORG_HEAD = (
    r"(?:Juzgado|Juz\.?|Fiscal[ií]a|Defensor[ií]a|Tribunal|C[aá]mara|"
    r"Procuraci[oó]n|Corte|Ministerio\s+P[uú]blico|Poder\s+Judicial|Unidad\s+Fiscal)"
)
_QUALIFIER = (
    r"(?:Nacional|Federal|Provincial|General|Superior|Suprema|Justicia|Apelaciones|"
    r"Casaci[oó]n|Primera|Segunda|Tercera|Instancia|Civil|Comercial|Penal|Criminal|"
    r"Correccional|Econ[oó]mico|Econ[oó]mica|Contencioso|Administrativo|Administrativa|"
    r"Contravencional|Familia|Menores|Garant[ií]as|Trabajo|Seguridad|Social|Fiscal|"
    r"Naci[oó]n|Provincia|Ciudad|Aut[oó]noma|Buenos|Aires|C[oó]rdoba|Mendoza|"
    r"de|del|la|las|los|en|lo|y)"
)
_ORG_NUMBER = r"(?:\s+(?:nro\.?|n[°º])\s*\d{1,3})?"
_ORG_RE = re.compile(
    rf"\b(?:{_ORG_HEAD}(?:\s+{_QUALIFIER}){{1,18}}{_ORG_NUMBER}|"
    rf"Juzgado\s+(?:nro\.?|n[°º])\s*\d{{1,3}}|"
    rf"Sala\s+(?:[A-Z]|[IVXLC]+|\d+)|CSJN|SCBA|MPF)(?!\w)",
    re.IGNORECASE,
)
_TRAILING_CONNECTOR_RE = re.compile(r"\s+(?:de|del|la|las|los|en|lo|y)$", re.IGNORECASE)


def organism_spans(text: str) -> list[tuple[int, int, str]]:
    spans = []
    for match in _ORG_RE.finditer(text):
        start, end = match.span()
        value = text[start:end]
        while trailing := _TRAILING_CONNECTOR_RE.search(value):
            end = start + trailing.start()
            value = text[start:end]
        if is_organism_name(value):
            spans.append((start, end, value))
    return spans


def is_organism_name(surface: str) -> bool:
    value = surface.strip()
    return bool(_ORG_RE.fullmatch(value)) and not bool(_TRAILING_CONNECTOR_RE.search(value))
