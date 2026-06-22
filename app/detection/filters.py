"""Filtros de calidad post-detección."""
import re

from app.detection.dictionaries import STOPWORDS_FRASE, get_apellidos, get_nombres
from app.detection.regex_ar import RawItem
from app.resolution.normalize import normalize_text

_bad_after_calle_re = re.compile(
    r"^\s*(?:calle|c\/|av\.?|avda\.?|avenida)\s+"
    r"(?:que|se|en|un|una|el|la|los|las|del|de|donde|cuando|cual|cuales|"
    r"quien|quienes|todo|toda|todos|todas|cualquier|cualquiera)\b",
    re.IGNORECASE,
)

_DOM_NARRATIVE_BAD = (
    "territorio",
    "república",
    "republica",
    "se encuentren",
    "que se encuentren",
    "en el marco",
    "de la nacion",
    "de la nación",
    "territorio de la",
    "territorio nacional",
)

_street_prefix_re = re.compile(
    r"\b(?:calle|c\/|av\.?|avda\.?|avenida|bv\.?|boulevard|pasaje|pje\.?|"
    r"plaza|pza\.?|ruta|rt\.?|camino|barrio|b°|manzana|mza\.?|lote|lt\.?|"
    r"dpto\.?|depto\.?|piso|torre|n[°º]\.?|nro\.?)\b",
    re.IGNORECASE,
)

_verbs_re = re.compile(
    r"\b(?:que|manifiesta|declara|considera|solicita|respondió|respondio|"
    r"recibió|recibio|encontró|encontro|guardó|guardo|mantuvo|trata|"
    r"fue|había|habia|pudo|desde|hacia|sobre|bajo|también|tambien)\b",
    re.IGNORECASE,
)

# Verbos y conectores narrativos que NO deben aparecer dentro del nombre de
# un organismo. Ej.: "Tribunal Superior quien revise la sentencia", "Cámara
# se apartó", "Procuración consideró que…". Es una lista más amplia que la
# de personas porque los organismos atrapan colas narrativas frecuentes.
_ORG_NARRATIVE_RE = re.compile(
    r"\b(?:quien|quienes|cual|cuales|cuya|cuyo|cuyas|cuyos|"
    r"se\s+(?:apart[óo]|expid[ióo]|pronunci[óo]|expres[óo])|"
    r"apart[óo]|aparte|revise|revisa|revisar[áa]?|"
    r"considera|consider[óeao]|considere|"
    r"manifest[óaeo]|declara|declare|declar[óao]|"
    r"resolverá|resolvera|dispuso|disponga|dispone|"
    r"sentencia|sentenci[óa]|hechos|fundamentos|recurso|recursos)\b",
    re.IGNORECASE,
)

# Abreviaturas que indican que el surface quedó truncado (cortado antes del
# número o complemento). Ej.: "Defensoría en lo Contravencional nro" o
# "Juzgado Civil n°".
_ORG_TRAILING_ABBR_RE = re.compile(
    r"\b(?:nro|n[°º]|art|inc|sec|dpto|depto|nº)\s*\.?\s*$",
    re.IGNORECASE,
)

# Frases narrativas completas (denuncias)
_LEGAL_CITE_RE = re.compile(r"\b(?:c/|s/)\s*$|\b(?:c/|s/)\s+\w", re.IGNORECASE)

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


def _is_year(s: str) -> bool:
    if re.fullmatch(r"\d{4}", s.strip()):
        return 1900 <= int(s) <= 2100
    return False


def _has_street_context(text: str, start: int, window: int = 120) -> bool:
    chunk = text[max(0, start - window) : start + 30].lower()
    return bool(_street_prefix_re.search(chunk))


def _looks_like_narrative(surface: str) -> bool:
    s = surface.strip()
    low = s.lower()
    if len(s) > 40:
        return True
    if any(phrase in low for phrase in _NARRATIVE_PHRASES):
        return True
    words = s.split()
    if len(words) >= 4 and _verbs_re.search(s):
        return True
    if len(words) >= 8:
        return True
    norm = [normalize_text(w) for w in words]
    if sum(1 for w in norm if w in get_formulas() or w in STOPWORDS_FRASE) >= max(
        1, len(words) // 2
    ):
        return True
    if " que " in low or low.startswith("que "):
        return True
    return False


def _has_autos_context(text: str, start: int) -> bool:
    chunk = text[max(0, start - 90) : start + 140]
    return bool(re.search(r"(?:\bc\s*\.?/|\bcontra\b)", chunk, re.IGNORECASE)) and bool(
        re.search(r"(?:\bs\s*\.?/|\bsobre\b)", chunk, re.IGNORECASE)
    )


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
    norm = [normalize_text(w) for w in words]
    nombres = get_nombres()
    apellidos = get_apellidos()
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
    if len(words) > 5:
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


def _is_valid_domicilio(surface: str, text: str, start: int) -> bool:
    s = surface.strip()
    if _bad_after_calle_re.search(s):
        return False
    low = s.lower()
    if any(bad in low for bad in _DOM_NARRATIVE_BAD):
        return False
    if _is_year(s):
        return False
    norm = normalize_text(s)
    apellidos = get_apellidos()
    nombres = get_nombres()
    if norm in apellidos or norm in nombres:
        return False
    if len(s.split()) == 1 and norm in apellidos:
        return False
    low = s.lower()
    if low in ("cami", "tomi", "sauce viejo") and not _street_prefix_re.search(s):
        return False
    if re.fullmatch(r"\d{1,5}", s):
        return _has_street_context(text, start)
    if re.fullmatch(r"[A-Z]\d{4}[A-Z]{3}", s, re.IGNORECASE):
        return True

    # Si contiene un prefijo de domicilio ("Calle", "Piso", "Dpto", etc.),
    # exigir señal de dirección real (número/CPA/coma) para evitar frases narrativas
    # tipo "calle y en riesgo..." o "piso que no".
    has_prefix = bool(_street_prefix_re.search(s))
    has_digit = bool(re.search(r"\d", s))
    has_comma = "," in s
    if has_prefix:
        if has_digit or has_comma:
            return True
        # contexto fuerte + longitud razonable (pero evitando frases típicas de narrativa)
        if _has_street_context(text, start) and len(s) > 18:
            if any(
                bad in low
                for bad in (
                    "riesgo",
                    "situacion de calle",
                    "situación de calle",
                    "garantia",
                    "garantía",
                    "proteccion",
                    "protección",
                    "derechos",
                )
            ):
                return False
            return True
        return False

    if _has_street_context(text, start) and len(s) > 18 and (has_digit or has_comma):
        return True
    return False


def _is_valid_telefono(surface: str) -> bool:
    digits = re.sub(r"\D", "", surface)
    if len(digits) == 8 and not surface.strip().startswith("+"):
        return False
    if len(digits) >= 8 and digits.startswith("0205"):
        return False
    return 10 <= len(digits) <= 13 and ("+" in surface or "-" in surface or " " in surface)


def _is_valid_dni(surface: str, text: str, start: int) -> bool:
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
    if cat == "PERSONA":
        if _has_autos_context(text, start) and not _looks_like_narrative(s):
            return 2 <= len(s.split()) <= 6 or s.isupper()
        return _is_valid_persona(s)
    if cat == "EXPEDIENTE":
        return _is_valid_expediente(s)
    if cat == "DOMICILIO":
        return _is_valid_domicilio(s, text, start)
    if cat == "TELEFONO":
        return _is_valid_telefono(s)
    if cat == "DNI":
        return _is_valid_dni(s, text, start)
    if cat == "ORGANISMO":
        low = s.lower()
        if len(s) > 55 or len(s.split()) > 6:
            return False
        if any(
            x in low
            for x in (
                "papeler",
                "cerrajer",
                "unidad funcional",
                "edificio",
                "dispuso",
                "requirió",
                "requirio",
                "acompañara",
                "acompanara",
                "correr traslado",
                "presentación",
                "presentacion",
                "comunicaciones mantenidas",
            )
        ):
            return False
        if not re.match(
            r"^(?:juzgado|fiscal|tribunal|cámara|camara|defensor|ministerio|procuración|procuracion)",
            low,
        ):
            return False
        # Rechazar frases que arrastran verbos o conectores narrativos: el
        # nombre real de un organismo nunca contiene "quien revise…" o
        # "se apartó…".
        if _ORG_NARRATIVE_RE.search(s):
            return False
        # Rechazar surfaces que terminan en abreviatura sin completar
        # (truncados por la regex al toparse con un punto interno).
        if _ORG_TRAILING_ABBR_RE.search(s):
            return False
        return len(s) >= 8
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
        if is_valid_detection(it.cat, it.original, text, it.start):
            out.append(it)
    return out
