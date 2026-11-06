"""Detección determinística para Argentina."""
import re
from dataclasses import dataclass

from app.detection.dictionaries import (
    get_apellidos,
    get_nombres,
)
from app.resolution.normalize import normalize_text
from app.detection.organizations import company_alias_spans, company_spans, organism_spans
from app.detection.person_context import actor_spans, signature_spans
from app.detection.person_names import PERSONA_BOUNDARY_WORDS, person_name_spans, trim_persona_tail
from app.detection.addresses import address_spans
from app.detection.case_titles import case_party_spans, is_explicit_case_party


@dataclass
class RawItem:
    cat: str
    original: str
    start: int
    end: int
    source_layer: str = "regex"


def validate_cuit(cuit: str) -> bool:
    digits = re.sub(r"\D", "", cuit)
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    mult = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(digits[i]) * mult[i] for i in range(10))
    check = 11 - (total % 11)
    if check == 11:
        check = 0
    if check == 10:
        check = 9
    return int(digits[10]) == check


def validate_dni(dni: str) -> bool:
    digits = re.sub(r"\D", "", dni)
    return 7 <= len(digits) <= 8


_detect_domicilios = address_spans


_PERSONA_NOISE_PREFIX_RE = re.compile(
    r"^(?:ORIGINAL|DUPLICADO|TRIPLICADO|CUADRUPLICADO|COPIA|ANEXO)\s+",
    re.IGNORECASE,
)

# Conectores procesales pegados al nombre por arrastre de carátulas o cortes
# de OCR: "c/ GCBA", "s/ Pérez", "en/ Idalgo".
_PERSONA_LEGAL_PREFIX_RE = re.compile(
    r"^(?:c\s*\.?\s*/|s\s*\.?\s*/|en\s*/|y\s+|e\s+|o\s+)\s*",
    re.IGNORECASE,
)

# Caracteres no-nombre al inicio (puntuación, saltos de línea, slashes).
_PERSONA_LEADING_PUNCT_RE = re.compile(r"^[\s,.;:\-/\\\"'()\[\]]+")

def _trim_initial_nonname_token(value: str) -> tuple[str, int]:
    """Recorta el primer token cuando NO aparece en los diccionarios de
    nombres/apellidos y el resto del surface SÍ contiene nombre + apellido.

    Cubre casos como "Acierta Silvia Palacio de Caeiro" donde el verbo
    capitalizado por punto se pega al nombre real. Devuelve (nuevo_valor,
    bytes_saltados_al_inicio_del_original).
    """
    parts = value.split()
    if len(parts) < 3:
        return value, 0
    nombres = get_nombres()
    apellidos = get_apellidos()
    # "APELLIDO, NOMBRE" is a strong surname-order signal, including rare
    # surnames absent from the dictionary. Never trim the surname as prose.
    if parts[0].endswith(","):
        return value, 0
    first_norm = normalize_text(parts[0].strip(".,;:"))
    if first_norm in nombres or first_norm in apellidos:
        return value, 0
    if first_norm not in PERSONA_BOUNDARY_WORDS:
        return value, 0  # an unknown first name is not evidence of a prose prefix
    rest_norms = [normalize_text(p) for p in parts[1:]]
    has_name = any(p in nombres for p in rest_norms)
    has_surname = any(p in apellidos for p in rest_norms)
    # Necesitamos una ancla en el diccionario en el resto (nombre o apellido),
    # caso contrario podríamos estar recortando un apellido poco común.
    if not (has_name or has_surname):
        return value, 0
    first_token = parts[0]
    idx = value.find(first_token)
    if idx < 0:
        return value, 0
    cut = idx + len(first_token)
    while cut < len(value) and value[cut].isspace():
        cut += 1
    return value[cut:], cut


def _clean_persona_surface(original: str, start: int, allow_unknown_lower: bool = False) -> tuple[str, int]:
    """Quita rótulos de copias y conectores procesales pegados al nombre."""
    value = original
    offset = 0
    # 1) Saltos / puntuación inicial.
    m = _PERSONA_LEADING_PUNCT_RE.match(value)
    if m:
        offset += m.end()
        value = value[m.end():]
    # 2) Rótulos de copia (ORIGINAL/DUPLICADO/…) y conectores legales.
    while True:
        m = _PERSONA_NOISE_PREFIX_RE.match(value) or _PERSONA_LEGAL_PREFIX_RE.match(value)
        if not m:
            break
        offset += m.end()
        value = value[m.end():]
        # Limpiar puntuación que pudiera quedar después del prefijo.
        m2 = _PERSONA_LEADING_PUNCT_RE.match(value)
        if m2:
            offset += m2.end()
            value = value[m2.end():]
    # 3) Verbo / palabra fuera de diccionario pegado al inicio del nombre
    #    ("Acierta Silvia Palacio…", "Considera Juan Pérez…").
    value, skipped = _trim_initial_nonname_token(value)
    offset += skipped
    return trim_persona_tail(value.strip(), allow_unknown_lower), start + offset


def _detect_autos_parties(text: str) -> list[tuple[int, int, str]]:
    return case_party_spans(text)


def detect_regex_ar(text: str) -> list[RawItem]:
    items: list[RawItem] = []
    seen: set[tuple[str, int, int]] = set()

    def add(cat: str, original: str, start: int, end: int, layer: str = "regex") -> bool:
        if cat == "PERSONA":
            bounded_party = layer in {"caratula", "ruler"} and is_explicit_case_party(original, text, start)
            if not bounded_party:
                original, start = _clean_persona_surface(original, start, layer == "person_context")
            end = start + len(original)
            if len(original.strip()) < 3:
                return False
        from app.detection.filters import is_valid_detection

        if not 0 <= start < end <= len(text) or text[start:end] != original:
            return False
        if layer not in {"structured", "structured_alias", "company_alias"} and not is_valid_detection(cat, original, text, start):
            return False
        key = (cat, start, end)
        if key in seen:
            return False
        seen.add(key)
        items.append(RawItem(cat=cat, original=original, start=start, end=end, source_layer=layer))
        return True

    from app.detection.identifiers import detect_identifiers

    for item in detect_identifiers(text):
        add(item.cat, item.original, item.start, item.end, item.source_layer)

    # --- Email ---
    email_re = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
    for m in email_re.finditer(text):
        add("EMAIL", m.group(0), m.start(), m.end())

    # --- Empresas ---
    companies = company_spans(text)
    for start, end, val in companies:
        add("EMPRESA", val, start, end)
    for start, end, val in company_alias_spans(text, companies):
        add("EMPRESA", val, start, end, "company_alias")

    # --- Domicilios ---
    for start, end, val in _detect_domicilios(text):
        add("DOMICILIO", val, start, end)

    # --- Organismos judiciales ---
    for start, end, val in organism_spans(text):
        add("ORGANISMO", val, start, end)

    # Explicit signatures identify names absent from the finite catalogs.
    # Their exact repetitions, including inserted initials, are also personal data.
    for start, end, val in signature_spans(text):
        add("PERSONA", val, start, end, "signature")
    for start, end, val in actor_spans(text):
        add("PERSONA", val, start, end, "caratula")

    # --- Personas en carátulas/autos: "ACTOR c/ DEMANDADO s/ ..." ---
    for start, end, val in _detect_autos_parties(text):
        add("PERSONA", val, start, end, "ruler")

    for start, end, value, explicit in person_name_spans(text):
        add("PERSONA", value, start, end, "person_context" if explicit else "names")

    # --- Fecha de nacimiento explícita ---
    nacimiento_re = re.compile(
        r"\b(?:nacido|nacida|fecha de nacimiento)[^\.\n]{0,40}?"
        r"(\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
        r"septiembre|setiembre|octubre|noviembre|diciembre)\s+de\s+\d{4})\b",
        re.IGNORECASE,
    )
    for m in nacimiento_re.finditer(text):
        add("OTRO", m.group(1), m.start(1), m.end(1))

    # Catálogo Regex_limpio_v2: completa huecos (OCR, domicilios, pasaportes, etc.)
    from app.detection.regex_catalog import detect_regex_catalog

    for item in detect_regex_catalog(text):
        add(item.cat, item.original, item.start, item.end, item.source_layer)

    items.sort(key=lambda x: x.start)
    return items
