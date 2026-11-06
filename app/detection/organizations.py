"""Bounded company names and qualified judicial institution names."""
import re

from app.detection.dictionaries import SUFIJOS_EMPRESA
from app.detection.case_titles import case_party_spans
from app.detection.form_fields import field_value_end
from app.detection.person_names import is_person_name_candidate
from app.resolution.normalize import normalize_text

_CAPITAL_WORD = r"[A-ZÁÉÍÓÚÜÑ][\wÁÉÍÓÚÜÑáéíóúüñ&'’\-.]*"
_SUFFIX = rf"(?i:{SUFIJOS_EMPRESA}|S\.?A\.?C\.?)"
_COMPANY_WORD = rf"(?!{_SUFFIX}(?!\w))(?:{_CAPITAL_WORD}|(?i:de|del|la|las|los|y|e|para|fines|determinados))"
_COMPANY_RE = re.compile(rf"\b{_CAPITAL_WORD}(?:\s+{_COMPANY_WORD}){{0,11}}\s+{_SUFFIX}(?!\w|\.[A-Za-z])")
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
_COMPANY_CLAUSE_RE = re.compile(
    r"\b(?:comparec(?:e|i[oó])|declar(?:a|[oó])|manifest(?:a|[oó])|"
    r"present(?:a|[oó])|inform(?:a|[oó])|reclam(?:a|[oó])|demand(?:a|[oó])|"
    r"consta|surge)\b(?:\s+que)?\s+(?:la\s+|el\s+)?", re.IGNORECASE,
)
_COMPANY_CONTEXT_RE = re.compile(
    r"\b(?P<kind>empresa|firma|raz[oó]n\s+social|aseguradora|compa[ñn][ií]a(?:\s+de\s+seguros)?|"
    r"comercio|local|hotel(?:\s+residencial)?|automotores|concesionaria|cooperativa|"
    r"fundaci[oó]n|asociaci[oó]n\s+civil)\b\s*"
    r"(?:(?:denominad[oa]|llamad[oa]|conocid[oa])\s+(?:como\s+)?)?[:\-]?\s*",
    re.IGNORECASE,
)
_COMPANY_BOUNDARY = (
    r"que|quien|con|domicilio|cuit|cuil|dni|tel[eé]fono|celular|representad[oa]|"
    r"comparece|declara|manifest[oó]|manifiesta|solicita|asegur[oó]|abon[oó]|"
    r"inform[oó]|informa|reclam[oó]|reclama|suscribi[oó]|present[oó]|presenta|"
    r"demand[oó]|demandada|demandado|se|fue|sito|situad[oa]|ubicad[oa]"
)
_CONTEXT_COMPANY_WORD = rf"(?!(?i:{_COMPANY_BOUNDARY})\b)[A-ZÁÉÍÓÚÜÑ][\wÁÉÍÓÚÜÑáéíóúüñ&'’\-]*"
_CONTEXT_NAME_RE = re.compile(
    rf"{_CONTEXT_COMPANY_WORD}(?:[ \t]+(?:(?i:de|del|la|las|los|y|e)\s+){{0,3}}"
    rf"{_CONTEXT_COMPANY_WORD}){{0,10}}"
)
_QUOTED_NAME_RE = re.compile(r'''["“«']([^"”»'\n;]{2,100})["”»']''')
_CONTEXT_LEGAL_RE = re.compile(_COMPANY_RE.pattern, re.IGNORECASE)
_INSTITUTIONAL_COMPANY_RE = re.compile(
    rf"(?:obra\s+social|mutual|cooperativa|asociaci[oó]n\s+civil|fundaci[oó]n|banco)\s+"
    rf"{_CONTEXT_NAME_RE.pattern}", re.IGNORECASE,
)


def _contextual_company_spans(text: str) -> list[tuple[int, int, str]]:
    spans = []
    for context in _COMPANY_CONTEXT_RE.finditer(text):
        generic_label = False
        if quoted := _QUOTED_NAME_RE.match(text, context.end()):
            start, end = quoted.span(1)
        elif legal := _CONTEXT_LEGAL_RE.match(text, context.end()):
            start, end = legal.span()
            if re.search(r"\b(?:SA|SRL|SAS|SAU|SAC)\.$", text[start:end], re.IGNORECASE):
                end -= 1
        elif named := _CONTEXT_NAME_RE.match(text, context.end()):
            start, end = named.span()
            generic_label = True
            while end > start and text[end - 1] == '.':
                end -= 1
        else:
            continue
        end = field_value_end(text, start, end)
        value = text[start:end]
        ambiguous_label = normalize_text(context.group('kind')) in {'empresa', 'firma', 'razon social'}
        if is_organism_name(value) or (generic_label and ambiguous_label and is_person_name_candidate(value)):
            continue
        if value and not re.fullmatch(r"(?:SA|SRL|SAS|SAU)", value, re.IGNORECASE):
            spans.append((start, end, value))
    return spans


def company_spans(text: str) -> list[tuple[int, int, str]]:
    spans = []
    for match in _COMPANY_RE.finditer(text):
        start, end = match.span()
        end = field_value_end(text, start, end)
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
    for start, end, value in _contextual_company_spans(text):
        if not any(a <= start and end <= b for a, b, _ in spans):
            spans.append((start, end, value))
    for start, end, value in case_party_spans(text):
        clauses = list(_COMPANY_CLAUSE_RE.finditer(value))
        if clauses:
            start += clauses[-1].end()
            value = text[start:end]
        if not is_company_name(value) or any(a <= start and end <= b for a, b, _ in spans):
            continue
        if (end < len(text) and text[end] == '.'
                and re.search(r"\b(?:[A-Za-z]\.)+[A-Za-z]$", value)):
            end += 1
            value = text[start:end]
        spans.append((start, end, value))
    return spans


_SUFFIX_TAIL_RE = re.compile(rf"\s+{_SUFFIX}$")
_NAME_PARTICLES = {'de', 'del', 'la', 'las', 'los', 'el', 'y', 'e', 'para'}


def company_alias_spans(
    text: str, seeds: list[tuple[int, int, str]],
) -> list[tuple[int, int, str]]:
    aliases: dict[str, str] = {}
    for _, _, value in seeds:
        suffix = _SUFFIX_TAIL_RE.search(value)
        base = value[:suffix.start()] if suffix else value
        words = [normalize_text(word) for word in re.findall(r"[^\W\d_]+", base)
                 if normalize_text(word) not in _NAME_PARTICLES]
        if len(words) < 2 or is_person_name_candidate(base):
            continue
        aliases.setdefault(normalize_text(base), base)
    spans: list[tuple[int, int, str]] = []
    seen: set[tuple[int, int]] = set()
    for base in aliases.values():
        pattern = re.compile(r"(?<!\w)" + r"\s+".join(map(re.escape, base.split())) + r"(?!\w)", re.IGNORECASE)
        for match in pattern.finditer(text):
            start, end = match.span()
            if (start, end) in seen or any(a <= start and end <= b for a, b, _ in seeds):
                continue
            seen.add((start, end))
            spans.append((start, end, match.group()))
    return spans


def is_company_name(surface: str) -> bool:
    return bool(_CONTEXT_LEGAL_RE.fullmatch(surface.strip()) or
                _INSTITUTIONAL_COMPANY_RE.fullmatch(surface.strip())) and not bool(
        _HEADER_PREFIX_RE.match(surface.strip()) or _PROSE_PREFIX_RE.search(surface)
        or _COMPANY_CLAUSE_RE.search(surface))


def is_contextual_company(surface: str, text: str, start: int) -> bool:
    context_end = start
    if context_end and text[context_end - 1] in '\"“«\'':
        context_end -= 1
    while context_end and text[context_end - 1].isspace():
        context_end -= 1
    left = max(0, context_end - 120)
    fragment = text[left:start + len(surface) + 1]
    return any(a + left == start and b + left == start + len(surface)
               for a, b, _ in _contextual_company_spans(fragment))


_ORG_HEAD = (
    r"(?:Juzgado|Juz\.?|Fiscal[ií]a|Defensor[ií]a|Tribunal|C[aá]mara|"
    r"Procuraci[oó]n|Corte|Ministerio\s+P[uú]blico|Ministerio|Poder\s+Judicial|Unidad\s+Fiscal)"
)
_QUALIFIER = (
    r"(?:Nacional|Federal|Provincial|General|Superior|Suprema|Justicia|Apelaciones|"
    r"Casaci[oó]n|Primera|Segunda|Tercera|Instancia|Civil|Comercial|Penal|Criminal|"
    r"Correccional|Econ[oó]mico|Econ[oó]mica|Contencioso|Administrativo|Administrativa|"
    r"Contravencional|Familia|Menores|Garant[ií]as|Trabajo|Seguridad|Social|Fiscal|"
    r"Naci[oó]n|Provincia|Ciudad|Aut[oó]noma|Buenos|Aires|C[oó]rdoba|Mendoza|"
    r"C\.?A\.?B\.?A\.?|Salud|Educaci[oó]n|Econom[ií]a|Interior|Defensa|"
    r"Departamental|Departamento|Judicial|Catamarca|Chaco|Chubut|Corrientes|"
    r"Entre|R[ií]os|Formosa|Jujuy|Pampa|Rioja|Misiones|Neuqu[eé]n|R[ií]o|Negro|"
    r"Salta|San|Juan|Luis|Santa|Cruz|Fe|Santiago|Estero|Tierra|Fuego|Tucum[aá]n|"
    r"de|del|la|las|los|en|lo|y)"
)
_ORG_NUMBER = r"(?:\s+(?:nro\.?|n[°º]|n[uú]mero)\s*\d{1,3})?"
_ORG_RE = re.compile(
    rf"\b(?:{_ORG_HEAD}(?:\s+{_QUALIFIER}){{1,18}}{_ORG_NUMBER}|"
    rf"Juzgado\s+(?:nro\.?|n[°º]|n[uú]mero)\s*\d{{1,3}}|"
    rf"Sala\s+(?:[A-Z]|[IVXLC]+|\d+)|(?:CSJN|SCBA|MPF)(?:\s+{_QUALIFIER}){{0,18}})(?!\w)",
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
