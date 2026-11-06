"""Filtros de calidad post-detección."""
import re

from app.detection.dictionaries import NAME_PARTICLES, STOPWORDS_FRASE, get_person_anchors
from app.detection.regex_ar import PERSONA_BOUNDARY_WORDS, RawItem, validate_cuit
from app.detection.organizations import is_company_name, is_organism_name, is_contextual_company
from app.detection.addresses import is_address
from app.detection.identifiers import is_sensitive_identifier
from app.detection.case_titles import (
    CASE_CONNECTOR_RE, is_explicit_case_party, overlaps_case_connector,
)
from app.detection.form_fields import field_value_end
from app.detection.person_context import is_contextual_person, is_vehicle_name
from app.detection.person_names import contains_person_list, is_person_name_candidate
from app.resolution.normalize import normalize_text

_verbs_re = re.compile(
    r"\b(?:que|manifiesta|declara|considera|solicita|respondió|respondio|"
    r"recibió|recibio|encontró|encontro|guardó|guardo|mantuvo|trata|"
    r"fue|había|habia|pudo|desde|hacia|sobre|bajo|también|tambien)\b",
    re.IGNORECASE,
)

# Frases narrativas completas (denuncias)
_LEGAL_CITE_RE = CASE_CONNECTOR_RE

_NARRATIVE_PHRASES = (
    "manifiesta que",
    "respondió que",
    "considera que",
    "guardó una",
    "guardó el",
    "recibió una",
    "recibió mensajes",
    "solo pudo",
    "es y hostigamiento",
    "encontró rayones",
    "la cerradura",
    "también recibió",
    "declara como",
    "solicita que",
    "nota de",
    "aportar una",
    "de parte de",
    "conversaciones previas",
    "negó los hechos",
    "afirmó que",
    "dispuso correr",
    "requirió a",
)

_PROCEDURAL_NOUNS = frozenset({
    'acta', 'actuacion', 'anexo', 'apelacion', 'audiencia', 'cedula',
    'certificacion', 'certificado', 'citacion', 'comunicacion', 'constancia',
    'consulta', 'contestacion', 'copia', 'declaracion',
    'demanda', 'denuncia', 'dictamen', 'diligencia', 'documentacion',
    'documento', 'elevacion', 'escrito', 'expediente', 'gestion',
    'habilitacion', 'impugnacion', 'incidente', 'informe', 'inscripcion',
    'instruccion', 'legalizacion', 'medida', 'memorando', 'nota',
    'notificacion', 'observacion', 'oficio', 'orden',
    'pericia', 'peticion', 'presentacion', 'procedimiento', 'providencia',
    'querella', 'reclamacion', 'reclamo', 'recurso', 'registracion',
    'registro', 'remision', 'requerimiento', 'resolucion', 'seguimiento',
    'solicitud', 'tramitacion', 'tramite', 'traslado', 'verificacion', 'vista',
})

_EXPEDIENTE_KEYWORDS = re.compile(
    r"\b(?:expediente|expte\.?|causa|autos|f\.?\s?s\.?|l\.?\s?e\.?|"
    r"exp\.?|cuij|n[uú]mero|nro\.?|n[°º]\.?)\b",
    re.IGNORECASE,
)

_CUIJ_RE = re.compile(r"\bJ-\d{2}-\d{6,9}-\d/\d{4}-\d\b", re.IGNORECASE)
_EXP_SHORT_RE = re.compile(
    r"\bEXP\.?\s+\d{2,8}(?:[\-/]\d{2,6})+\b", re.IGNORECASE
)

_MONEY_CONTEXT_RE = re.compile(
    r"(\$|pesos?|monto|suma|capital|condena|condenar|indemnizaci[oó]n|"
    r"honorarios|inter[eé]s|intereses|liquidaci[oó]n|total|importe)",
    re.IGNORECASE,
)

_PATENTE_RE = re.compile(
    r"^(?:"
    r"[A-Z]{2}[\s\-]?\d{3}[\s\-]?[A-Z]{2}"
    r"|[A-Z]{3}[\s\-]?\d{3}"
    r"|[A-Z][\s\-]?\d{3}[\s\-]?[A-Z]{3}"
    r")$",
    re.IGNORECASE,
)

# Prefijos alfabéticos que parecen patente vieja "AAA 123" pero son
# referencias legales o administrativas, no dominios vehiculares.
_PATENTE_LEGAL_PREFIXES = frozenset(
    {
        "ley", "art", "cap", "doc", "inc", "reg", "tit", "cam", "cám",
        "cpc", "cpcc", "ccc", "ccyc", "cpe", "cpp", "ord", "res", "dec",
        "exp", "fs", "lib", "fol", "rol", "iva", "afp", "ans", "afa",
        "cod", "num", "nro", "tel", "cel", "dni", "cbu", "cvu",
    }
)

_FECHA_NAC_RE = re.compile(
    r"^\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    r"septiembre|setiembre|octubre|noviembre|diciembre)\s+de\s+\d{4}$",
    re.IGNORECASE,
)

# Palabras administrativas / procesales que aparecen capitalizadas y que el
# detector de personas a veces confunde con apellidos. No son personas y no
# están en el diccionario de nombres/apellidos.
_PERSONA_ADMIN_STOPWORDS = frozenset(
    {
        "otros", "mismo", "misma", "mismos", "mismas",
        "general", "generales", "especial", "especiales",
        "comun", "común", "comunes", "carrera", "carreras",
        "ceremonias", "ceremonia",
        "publicodiferencias", "diferencias",
        "publico", "público", "publica", "pública",
        "privado", "privada", "privados", "privadas",
        "municipal", "municipales", "provincial", "provinciales",
        "estatal", "estatales", "nacional", "nacionales",
        "federal", "federales", "internacional", "internacionales",
        "sobre", "bajo", "contra", "ante",
        "empleo", "empleos", "salud", "educacion", "educación",
        "vivienda", "trabajo", "trabajos",
    }
)

_formulas: set[str] | None = None


def get_formulas() -> set[str]:
    global _formulas
    if _formulas is None:
        import json
        from app.config import DATA_DIR, RESOURCE_DATA_DIR

        _formulas = set()
        for base in (RESOURCE_DATA_DIR, DATA_DIR):
            path = base / "dictionaries" / "formulas_judiciales.json"
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    _formulas = set(json.load(f))
                break
    return _formulas


def _looks_like_narrative(surface: str, max_chars: int = 120, max_words: int = 12) -> bool:
    s = surface.strip()
    low = s.lower()
    if len(s) > max_chars:
        return True
    if any(phrase in low for phrase in _NARRATIVE_PHRASES):
        return True
    words = s.split()
    if len(words) >= 4 and _verbs_re.search(s):
        return True
    if len(words) > max_words:
        return True
    norm = [normalize_text(w.strip(".,;:")) for w in words]
    if norm:
        head = norm[0]
        head_forms = {head, head[:-1] if head.endswith('s') else head,
                      head[:-2] if head.endswith('es') else head}
        if head_forms & _PROCEDURAL_NOUNS and not is_person_name_candidate(s):
            return True
    if any(w in PERSONA_BOUNDARY_WORDS for w in norm):
        return True
    particles = {"de", "del", "la", "las", "los", "y", "e"}
    names, surnames = get_person_anchors()
    anchors = names | surnames
    if sum(1 for w in norm if w not in particles and w not in anchors
           and (w in get_formulas() or w in STOPWORDS_FRASE)) >= max(
        1, len(words) // 2
    ):
        return True
    if " que " in low or low.startswith("que "):
        return True
    return False


def _is_valid_persona(surface: str) -> bool:
    s = surface.strip()
    if len(s) < 3 or _looks_like_narrative(s):
        return False
    if _LEGAL_CITE_RE.search(s):
        return False
    low = normalize_text(s)
    if low in get_formulas() or low in STOPWORDS_FRASE:
        return False
    if low in ("como", "relato", "firma", "aclaracion", "ficticio", "nota", "cami"):
        return False
    if any(
        x in low
        for x in (
            "juzgado",
            "fiscal",
            "tribunal",
            "conversaciones",
            "negó",
            "nego",
            "afirmó",
            "afirmo",
            "dispuso",
            "requirió",
            "requirio",
            "de parte",
        )
    ):
        return False
    words = [w for w in s.split() if len(w) > 1]
    if not words:
        return False
    norm = [normalize_text(w.strip(".,;:")) for w in words]
    if any(w in PERSONA_BOUNDARY_WORDS for w in norm):
        return False
    nombres, apellidos = get_person_anchors()
    has_name = any(w in nombres for w in norm)
    has_surname = any(w in apellidos for w in norm)
    # Rechazar surfaces que contienen palabras administrativas/procesales y
    # NO tienen un nombre real como ancla. Cubre casos como
    # "Carrera Municipal" (apellido común + adjetivo administrativo),
    # "Fuentes Ceremonias" (apellido + sustantivo), "GCBA SOBRE EMPLEO".
    # Si hay un nombre claro en el surface (ej.: "Daniel Carrera"), se
    # mantiene la detección.
    if any(w in _PERSONA_ADMIN_STOPWORDS for w in norm) and not has_name:
        return False
    if all(w in _PERSONA_ADMIN_STOPWORDS for w in norm):
        return False
    if re.search(r"[A-ZÁÉÍÓÚÑ]\.", s):
        return has_surname or has_name
    if len(words) == 1:
        w = norm[0]
        return w in nombres or w in apellidos
    if len(words) >= 2 and not (has_surname or has_name):
        return False
    if len([w for w in norm if w not in {"de", "del", "la", "las", "los", "y", "e"}]) > 10:
        return False
    return has_surname or (has_name and len(words) >= 2)


def _is_valid_expediente(surface: str) -> bool:
    s = surface.strip()
    low = s.lower()
    if low in get_formulas():
        return False
    if _CUIJ_RE.search(s) or _EXP_SHORT_RE.search(s):
        return True
    if re.match(r"^no\w+", low) and not re.search(r"\d", s):
        return False
    if re.match(r"^exp(?!ediente|te|\.?\s+\d|\.?\s+j-)", low):
        return False
    if not _EXPEDIENTE_KEYWORDS.search(s) and not re.search(r"\d", s):
        return False
    return bool(re.search(r"\d", s) or "/" in s or "-" in s)


def _is_valid_telefono(surface: str) -> bool:
    if not re.fullmatch(r"\+?\(?\d[\d\s()./-]*\d\)?", surface.strip()):
        return False
    digits = re.sub(r"\D", "", surface)
    if not digits.strip("0"):
        return False
    if len(digits) == 8 and not surface.strip().startswith("+"):
        return False
    if len(digits) >= 8 and digits.startswith("0205"):
        return False
    return 10 <= len(digits) <= 13 and ("+" in surface or "-" in surface or " " in surface)


def _is_valid_dni(surface: str, text: str, start: int) -> bool:
    if not re.fullmatch(r"\d[\d\s.-]*\d", surface.strip()):
        return False
    digits = re.sub(r"\D", "", surface)
    if not (7 <= len(digits) <= 8):
        return False
    left = text[max(0, start - 80) : start]
    right = text[start : start + len(surface) + 40]
    immediate_left = text[max(0, start - 24) : start]
    if re.search(r"\b(?:dni|d\.?n\.?i\.?|documento|du)\s*(?:n[°º]\.?)?\s*$", immediate_left, re.IGNORECASE):
        return True
    context = f"{left} {right}"
    if _MONEY_CONTEXT_RE.search(context):
        return False
    # Un número con separadores de miles en contexto monetario suele venir
    # precedido por $; sin contexto de documento, mantener la validación clásica.
    if start > 0 and text[max(0, start - 3) : start].strip().endswith("$"):
        return False
    return True


def _is_valid_patente(surface: str) -> bool:
    s = surface.strip()
    # "Ley 471", "Art 123", "Inc 5", etc. cumplen el patrón de patente vieja
    # (3 letras + 3 dígitos) pero son citas normativas. Rechazar por prefijo.
    head_match = re.match(r"^([A-Za-zÁÉÍÓÚÑáéíóúñ]{2,4})\b", s)
    if head_match and head_match.group(1).lower() in _PATENTE_LEGAL_PREFIXES:
        return False
    compact = re.sub(r"[\s\-]", "", s)
    return bool(_PATENTE_RE.match(compact))


def _is_valid_otro(surface: str, text: str, start: int) -> bool:
    s = surface.strip()
    if _FECHA_NAC_RE.match(s):
        left = text[max(0, start - 40) : start].lower()
        return "nacid" in left or "nacimiento" in left
    if re.fullmatch(r"[A-Z0-9][\w\-]{5,16}", s, re.IGNORECASE):
        # Exigir al menos un dígito en el surface: un documento extranjero
        # siempre tiene número. Sin esto, palabras comunes como "recibida"
        # o "documento" caen como OTRO sólo por aparecer cerca de la
        # palabra "documento" en el contexto.
        if not re.search(r"\d", s):
            return False
        left = text[max(0, start - 50) : start].lower()
        return any(
            k in left
            for k in (
                "cédula",
                "cedula",
                "pasaporte",
                "passport",
                "documento",
                "c.i.",
                "identidad",
            )
        )
    return False


def is_valid_detection(cat: str, surface: str, text: str = "", start: int = 0) -> bool:
    """API unificada para regex, Presidio, spaCy y post-proceso."""
    s = surface.strip()
    if not s or len(s) < 2:
        return False
    if cat in {"PERSONA", "EMPRESA", "ORGANISMO"} and field_value_end(s, 0, len(s)) != len(s):
        return False
    if cat in {"DNI", "CUIT", "TELEFONO", "PATENTE", "EXPEDIENTE", "OTRO"}:
        if is_sensitive_identifier(cat, s, text, start):
            return True
    if cat == "PERSONA":
        if overlaps_case_connector(s, text, start) or contains_person_list(s):
            return False
        if is_company_name(s) or is_organism_name(s) or is_vehicle_name(s, text, start):
            return False
        if is_contextual_person(s, text, start) and not _looks_like_narrative(s, max_chars=120, max_words=12):
            return True
        if is_explicit_case_party(s, text, start) and not _looks_like_narrative(s):
            components = [word for word in re.findall(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*", s)
                          if normalize_text(word) not in NAME_PARTICLES]
            return 1 <= len(components) <= 8
        return _is_valid_persona(s)
    if cat == "EXPEDIENTE":
        return _is_valid_expediente(s)
    if cat == "DOMICILIO":
        return is_address(s, text, start)
    if cat == "TELEFONO":
        return _is_valid_telefono(s)
    if cat == "DNI":
        return _is_valid_dni(s, text, start)
    if cat == "CUIT":
        return validate_cuit(s)
    if cat == "ORGANISMO":
        return is_organism_name(s)
    if cat == "EMPRESA":
        return is_company_name(s) or is_contextual_company(s, text, start)
    if cat == "PATENTE":
        return _is_valid_patente(s)
    if cat == "OTRO":
        return _is_valid_otro(s, text, start)
    return True


def is_valid_manual_detection(cat: str, surface: str, text: str = "", start: int = 0) -> bool:
    """Validación relajada para texto elegido a mano en vista previa."""
    s = surface.strip()
    if len(s) < 2:
        return False
    if cat == "PERSONA":
        if _looks_like_narrative(s) or _LEGAL_CITE_RE.search(s):
            return False
        if any(x in s.lower() for x in ("juzgado", "fiscal", "tribunal", "dispuso", "de parte")):
            return False
        return True
    return is_valid_detection(cat, s, text, start)


def apply_quality_filters(items: list[RawItem], text: str) -> list[RawItem]:
    out: list[RawItem] = []
    for it in items:
        if it.source_layer in {"structured", "structured_alias", "company_alias"}:
            if 0 <= it.start < it.end <= len(text) and text[it.start:it.end] == it.original:
                out.append(it)
            continue
        if is_valid_detection(it.cat, it.original, text, it.start):
            out.append(it)
    return out
