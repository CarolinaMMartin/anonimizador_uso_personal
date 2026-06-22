"""Detección determinística para Argentina."""
import re
from dataclasses import dataclass

from app.detection.dictionaries import (
    SUFIJOS_EMPRESA,
    STOPWORDS_FRASE,
    get_apellidos,
    get_nombres,
)
from app.resolution.normalize import normalize_text


@dataclass
class RawItem:
    cat: str
    original: str
    start: int
    end: int
    source_layer: str = "regex"


def validate_cuit(cuit: str) -> bool:
    digits = re.sub(r"\D", "", cuit)
    if len(digits) != 11:
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


_STREET_PREFIX = (
    r"(?:Calle|C\/|Av\.?|Avda\.?|Avenida|Bv\.?|Boulevard|Bulevar|"
    r"Pasaje|Pje\.?|Plaza|Pza\.?|Ruta|Rt\.?|Camino|Barrio|B°|"
    r"Manzana|Mza\.?|Lote|Lt\.?|Dpto\.?|Depto\.?|Piso|Torre)"
)

# Tras "calle/av." no debe seguir un conector narrativo (evita "calle que se encuentren…").
_STREET_BAD_FOLLOW = (
    r"que|se|en|un|una|el|la|los|las|del|de|donde|cuando|cual|cuales|"
    r"quien|quienes|todo|toda|todos|todas|cualquier|cualquiera"
)
_ADDR_END = (
    r"(?=[;:\n]|$"
    r"|\.(?!(?:\s*(?:piso|dto\.?|dpto\.?|depto\.?|torre|de\s+esta)"
    r"|\s+[A-Za-záéíóúñ]\b"
    r"|\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})))"
)


def _merge_domicilio_spans(
    text: str, spans: list[tuple[int, int, str]]
) -> list[tuple[int, int, str]]:
    if not spans:
        return []
    spans.sort(key=lambda x: x[0])
    merged: list[tuple[int, int, str]] = [spans[0]]
    for start, end, _ in spans[1:]:
        ps, pe, _ = merged[-1]
        if start <= pe + 2:
            new_end = max(pe, end)
            merged[-1] = (ps, new_end, text[ps:new_end].strip())
        else:
            merged.append((start, end, text[start:end].strip()))
    return merged


def _detect_domicilios(text: str) -> list[tuple[int, int, str]]:
    """Detecta domicilios argentinos (regex compuesto, genérico y anclas narrativas)."""
    spans: list[tuple[int, int, str]] = []

    def push(m: re.Match[str]) -> None:
        val = m.group(0).strip()
        if len(val) > 5:
            spans.append((m.start(), m.end(), val))

    # Dirección compuesta: Av. Nombre 1234, piso 1, Dpto. A [, de esta ciudad]
    compound_re = re.compile(
        rf"\b{_STREET_PREFIX}\s*"
        r"[A-ZÁÉÍÓÚÑa-záéíóúñ0-9·\.\-]+(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ0-9·\.\-]+)*"
        r"\s+\d{1,5}[A-Za-z]?"
        r"(?:\s*,\s*(?:piso|dto\.?|dpto\.?|depto\.?|torre|mz\.?|manzana|lote|"
        r"n[°º]\.?\s*\d+)\s+[\w\d]+)+"
        r"(?:\s*,\s*de\s+esta\s+ciudad)?",
        re.IGNORECASE,
    )
    for m in compound_re.finditer(text):
        push(m)

    # Genérico: prefijo + cuerpo hasta terminador inteligente (Av.Corrientes sin espacio)
    generic_re = re.compile(
        rf"\b{_STREET_PREFIX}\s+"
        rf"(?!{_STREET_BAD_FOLLOW}\b)"
        r"[A-ZÁÉÍÓÚÑa-záéíóúñ0-9·\.\-\s,°º]+?"
        + _ADDR_END,
        re.IGNORECASE,
    )
    for m in generic_re.finditer(text):
        push(m)

    constituido_re = re.compile(
        r"\bdomicilio(?:\s+\w+){0,4}\s+constitu(?:ido|ida)\s+en\s+"
        r"(?:la\s+)?"
        r"(.+?)"
        r"(?=(?:,\s*)?y\s+(?:electr\w*|como|con|domicilio)|[.;]\s*$|\.$)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in constituido_re.finditer(text):
        body = m.group(1).strip(" ,.;")
        if len(body) > 8 and (re.search(r"\d", body) or _street_prefix_in(body)):
            start = m.start(1)
            spans.append((start, start + len(body), body))

    # Anclas narrativas: domicilio en … / sito en …
    narrative_re = re.compile(
        r"\b(?:"
        r"domicilio\s+(?:electr[oó]nico|fiscal|legal|autorizado)\s+(?:en\s+)?"
        r"|domicilio|domiciliad[oa]|con\s+domicilio|sito"
        r")\s+"
        r"(?:en|real\s+en|fiscal\s+en)\s+"
        r"(?:la\s+)?"
        r"(.+?)"
        r"(?=(?:,\s*)?y\s+(?:electr\w*|como|con|domicilio)|[.;]\s|$)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in narrative_re.finditer(text):
        body = m.group(1).strip()
        if re.search(r"\d", body) or _street_prefix_in(body):
            start = m.start(1)
            spans.append((start, start + len(body), body))

    # CPA argentino
    cpa_re = re.compile(r"\b([A-Z]\d{4}[A-Z]{3})\b")
    for m in cpa_re.finditer(text):
        spans.append((m.start(), m.end(), m.group(1)))

    return _merge_domicilio_spans(text, spans)


def _street_prefix_in(s: str) -> bool:
    return bool(
        re.search(
            r"\b(?:calle|c\/|av\.?|avda\.?|avenida|piso|dpto\.?|depto\.?)\b",
            s,
            re.IGNORECASE,
        )
    )


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
    first_norm = normalize_text(parts[0])
    if first_norm in nombres or first_norm in apellidos:
        return value, 0
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


def _clean_persona_surface(original: str, start: int) -> tuple[str, int]:
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
    return value.strip(), start + offset


def _detect_autos_parties(text: str) -> list[tuple[int, int, str]]:
    """Extrae actor y demandado de carátulas tipo "Apellido c/ Apellido s/"."""
    party = (
        r"[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ,&\.\-']{2,}"
        r"(?:[ \t]+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ,&\.\-']{2,}){0,5}"
    )
    autos_re = re.compile(
        rf"(?P<actor>{party})\s+(?:C\s*\.?/|CONTRA)\s+"
        rf"(?P<demandado>{party})(?=\s+(?:S\s*\.?/|SOBRE\b)|[.;,\n]|$)",
        re.IGNORECASE,
    )
    spans: list[tuple[int, int, str]] = []
    for m in autos_re.finditer(text):
        for group in ("actor", "demandado"):
            val = m.group(group).strip(" ,.;")
            if len(val.split()) >= 1:
                start = m.start(group) + (len(m.group(group)) - len(m.group(group).lstrip()))
                spans.append((start, start + len(val), val))
    return spans


def detect_regex_ar(text: str) -> list[RawItem]:
    items: list[RawItem] = []
    seen_ranges: list[tuple[int, int]] = []

    def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
        return a[0] < b[1] and b[0] < a[1]

    def add(cat: str, original: str, start: int, end: int, layer: str = "regex") -> bool:
        if cat == "PERSONA":
            original, start = _clean_persona_surface(original, start)
            end = start + len(original)
            if len(original.strip()) < 3:
                return False
        r = (start, end)
        for ex in seen_ranges:
            if overlaps(r, ex):
                return False
        seen_ranges.append(r)
        items.append(RawItem(cat=cat, original=original, start=start, end=end, source_layer=layer))
        return True

    # --- Expedientes con formato fuerte (antes que CUIT para evitar que CUIJ
    #     sea confundido con CUIT por el subnúmero 01-00056958-1).
    cuij_re = re.compile(
        r"\b(?:EXP\s+)?J-\d{2}-\d{6,9}-\d/\d{4}-\d\b",
        re.IGNORECASE,
    )
    for m in cuij_re.finditer(text):
        add("EXPEDIENTE", m.group(0), m.start(), m.end())

    exp_short_re = re.compile(
        r"\bEXP\.?\s+\d{2,8}(?:[\-/]\d{1,6})+\b",
        re.IGNORECASE,
    )
    for m in exp_short_re.finditer(text):
        add("EXPEDIENTE", m.group(0), m.start(), m.end())

    # --- CUIT/CUIL (antes que DNI para evitar solapes) ---
    cuit_labeled_re = re.compile(
        r"\b(?:CUIT|CUIL|C\.U\.I\.T\.|C\.U\.I\.L\.)\s*"
        r"(?:N[°º]\.?|Nro\.?|n[uú]mero)?\s*[:#]?\s*"
        r"(\d{2}[\s\-]*\d{8}[\s\-]*\d)",
        re.IGNORECASE,
    )
    for m in cuit_labeled_re.finditer(text):
        digits = re.sub(r"\D", "", m.group(1))
        if len(digits) == 11 and validate_cuit(digits):
            add("CUIT", m.group(0).strip(), m.start(), m.end())

    cuit_re = re.compile(r"\b(\d{2}[\s\-]*\d{8}[\s\-]*\d)\b")
    for m in cuit_re.finditer(text):
        digits = re.sub(r"\D", "", m.group(1))
        if len(digits) == 11 and validate_cuit(digits):
            add("CUIT", m.group(0).strip(), m.start(), m.end())

    # CUIT/CUIL tras "domicilio electrónico/autorizado" sin etiqueta explícita
    dom_cuit_re = re.compile(
        r"\bdomicilio\s+(?:electr[oó]nico|fiscal|legal|autorizado)\s+"
        r"(\d{11})\b",
        re.IGNORECASE,
    )
    for m in dom_cuit_re.finditer(text):
        if validate_cuit(m.group(1)):
            add("CUIT", m.group(1), m.start(1), m.end(1))

    # --- DNI (formato con puntos para no solapar con CUIT) ---
    dni_re = re.compile(r"\b(\d{1,2}\.\d{3}\.\d{3})\b")
    for m in dni_re.finditer(text):
        if validate_dni(m.group(1)):
            add("DNI", m.group(0), m.start(), m.end())

    # --- Email ---
    email_re = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
    for m in email_re.finditer(text):
        add("EMAIL", m.group(0), m.start(), m.end())

    # --- Teléfonos AR (exige +54 o formato con guiones/espacios) ---
    phone_re = re.compile(
        r"(?:\+54\s?(?:9\s?)?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}|"
        r"(?:15|11)[-.\s]?\d{3,4}[-.\s]?\d{3,4})\b"
    )
    for m in phone_re.finditer(text):
        raw = m.group(0)
        digits = re.sub(r"\D", "", raw)
        if len(digits) < 10 or len(digits) > 13:
            continue
        skip = any(m.start() < ex[1] and ex[0] < m.end() for ex in seen_ranges)
        if not skip:
            add("TELEFONO", raw, m.start(), m.end())

    # --- Empresas ---
    empresa_re = re.compile(
        rf"\b((?:[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ&\-\.]*\s+){{1,6}}{SUFIJOS_EMPRESA})\b",
        re.IGNORECASE,
    )
    for m in empresa_re.finditer(text):
        val = m.group(0).strip()
        if len(val) >= 5:
            add("EMPRESA", val, m.start(), m.end())

    # --- Domicilios ---
    for start, end, val in _detect_domicilios(text):
        add("DOMICILIO", val, start, end)

    # --- Expedientes (sin exp\.? ni n[°ºo] que matchea "nombre"/"nocturno") ---
    expt_re = re.compile(
        r"\b(?:expediente|expte\.?|causa|autos)\s+"
        r"(?:n[°º]\.?\s*)?[:#]?\s*([A-Z0-9][A-Z0-9\-\/\.]{3,28})\b",
        re.IGNORECASE,
    )
    for m in expt_re.finditer(text):
        full = m.group(0).strip()
        if re.search(r"\d", full):
            add("EXPEDIENTE", full, m.start(), m.end())

    expt_n_re = re.compile(
        r"\b(?:expediente|expte\.?|causa)\s+n[°º]\.?\s*(\d[\d\-\/\.]{2,20})\b",
        re.IGNORECASE,
    )
    for m in expt_n_re.finditer(text):
        add("EXPEDIENTE", m.group(0), m.start(), m.end())

    expt_num_re = re.compile(
        r"\b(?:FS|F\.?\s?S\.?|LE|L\.?\s?E\.?)\s*[:#]?\s*(\d{1,6}[/\-]\d{2,6})\b",
        re.IGNORECASE,
    )
    for m in expt_num_re.finditer(text):
        add("EXPEDIENTE", m.group(0), m.start(), m.end())

    # Etiquetas tipo "Nro. 12345/2020" — captura cuando hay un número con barra
    # (los CUIJ y EXP cortos ya se detectan antes que CUIT, ver inicio).
    label_re = re.compile(
        r"\b(?:n[uú]mero|nro\.?|n[°º]\.?)\s*[:#]?\s*"
        r"(\d{2,8}[/\-]\d{2,4}(?:[\-/]\d{1,6})?)\b",
        re.IGNORECASE,
    )
    for m in label_re.finditer(text):
        add("EXPEDIENTE", m.group(0), m.start(), m.end())

    # --- Organismos judiciales ---
    org_re = re.compile(
        r"\b(?:Juzgado|Juz\.?|Fiscalía|Fiscalia|Defensoría|Defensoria|"
        r"Tribunal|Cámara|Camara|Procuración|Procuracion|"
        r"Ministerio Público|MPF|SCBA|CSJN|"
        r"Unidad Fiscal|UF\s?\d+|Sala\s+[IVXLC\d]+)\s+"
        r"(?:[A-ZÁÉÍÓÚÑ][\wáéíóúñÁÉÍÓÚÑ\s\.\-]+?)(?=[\.;,\n]|$)",
        re.IGNORECASE,
    )
    for m in org_re.finditer(text):
        val = m.group(0).strip()
        if len(val) > 8:
            add("ORGANISMO", val, m.start(), m.start() + len(val))

    # --- Personas en carátulas/autos: "ACTOR c/ DEMANDADO s/ ..." ---
    for start, end, val in _detect_autos_parties(text):
        add("PERSONA", val, start, end, "ruler")

    # --- Personas: tratamientos ---
    honor_re = re.compile(
        r"\b(?:Sr\.?|Sra\.?|Srta\.?|Dr\.?|Dra\.?|Lic\.?|Ing\.?|"
        r"señor|señora|señorita|don|doña)[ \t]+"
        r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:[ \t]+(?:de|del|la|las|los|y)[ \t]+)?"
        r"(?:[ \t]+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,5})",
        re.IGNORECASE,
    )
    for m in honor_re.finditer(text):
        name = m.group(1)
        name_start = m.start() + m.group(0).index(name)
        add("PERSONA", name, name_start, name_start + len(name))

    # --- Personas: roles judiciales ---
    rol_re = re.compile(
        r"\b(?:imputad[oa]|v[ií]ctima|denunciante|testig[oa]|"
        r"querellante|damnificad[oa]|ofendid[oa]|"
        r"menor|niñ[oa]|adolescente|progenitor[oa]|"
        r"representante[ \t]+legal|parte|actor[oa]|demandad[oa])[ \t]*"
        r"[:,\.]?[ \t]*"
        r"(?:(?:Sr|Sra|Dr|Dra)\.?[ \t]+)?"
        r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+"
        r"(?:[ \t]+(?:(?:de|del|la|las|los|y)[ \t]+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,5})",
        re.IGNORECASE,
    )
    for m in rol_re.finditer(text):
        if m.group(1):
            name = m.group(1)
            name_start = m.start() + m.group(0).index(name)
            add("PERSONA", name, name_start, name_start + len(name), "ruler")

    # --- Personas: iniciales (Juan G. Pérez) ---
    init_re = re.compile(
        r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+[ \t]+"
        r"(?:[A-ZÁÉÍÓÚÑ]\.[ \t]*){1,3}"
        r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\b"
    )
    for m in init_re.finditer(text):
        add("PERSONA", m.group(1), m.start(), m.end())

    # --- Personas: Sr./Sra. + apellido ---
    sr_re = re.compile(
        r"\b(?:Sr|Sra|Srta)\.?[ \t]+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\b",
        re.IGNORECASE,
    )
    for m in sr_re.finditer(text):
        add("PERSONA", m.group(1), m.start(1), m.end(1), "ruler")

    nombres = get_nombres()
    apellidos = get_apellidos()

    # --- Personas: tratamiento + nombre en MAYÚSCULAS ---
    #     (ej. "Dra. YAMILA MONICA CZICZERSKYJ"). El título es señal fuerte,
    #     por eso no exigimos diccionario aquí.
    honor_caps_re = re.compile(
        r"\b(?:Sr\.?|Sra\.?|Srta\.?|Dr\.?|Dra\.?|Lic\.?|Ing\.?|"
        r"se[ñn]or|se[ñn]ora|se[ñn]orita|don|do[ñn]a)[ \t]+"
        r"([A-ZÁÉÍÓÚÑ]{2,}(?:[ \t]+(?:DE|DEL|LA|LAS|LOS|Y)[ \t]+)?"
        r"(?:[ \t]*[A-ZÁÉÍÓÚÑ]{2,}){0,3})\b",
        re.IGNORECASE,
    )
    for m in honor_caps_re.finditer(text):
        name = m.group(1).strip()
        if not name.isupper():
            continue  # los titlecase ya los cubre honor_re
        norm_parts = [normalize_text(p) for p in name.split()]
        if all(p in STOPWORDS_FRASE for p in norm_parts):
            continue
        add("PERSONA", name, m.start(1), m.start(1) + len(name), "ruler")

    # --- Personas: "APELLIDO, Nombre[s]" (encabezado judicial) ---
    #     ej. "CERRUDO, MARCELO" o "Morales, Patricia Valeria". La coma es
    #     una señal fuerte: basta UN ancla de diccionario (nombre o apellido).
    ap_nom_re = re.compile(
        r"\b([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ]{2,}),[ \t]+"
        r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ]{2,}"
        r"(?:[ \t]+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ]{2,}){0,3})\b"
    )
    for m in ap_nom_re.finditer(text):
        all_norm = [normalize_text(m.group(1))] + [
            normalize_text(p) for p in m.group(2).split()
        ]
        if any(p in STOPWORDS_FRASE for p in all_norm):
            continue
        if not any(p in nombres or p in apellidos for p in all_norm):
            continue
        add("PERSONA", m.group(0), m.start(), m.end())

    # --- Personas: capitalización + diccionario ---
    cap_re = re.compile(
        r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}"
        r"(?:[ \t]+(?:(?:de|del|la|las|los|y)[ \t]+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}){1,5})\b"
    )
    for m in cap_re.finditer(text):
        candidate = m.group(1)
        # No unir dos sujetos: "Marcos Benítez y Camila Ferreyra"
        if re.search(r"\s+y\s+", candidate, re.IGNORECASE):
            candidate = re.split(r"\s+y\s+", candidate, maxsplit=1, flags=re.IGNORECASE)[0].strip()
            end = m.start() + len(candidate)
        else:
            end = m.end()
        parts = [
            p
            for p in candidate.split()
            if p.lower() not in ("de", "del", "la", "las", "los", "y")
        ]
        if len(parts) < 2:
            continue
        norm_parts = [normalize_text(p) for p in parts]
        has_apellido = any(p in apellidos for p in norm_parts)
        has_nombre = any(p in nombres for p in norm_parts)
        has_stop = any(p in STOPWORDS_FRASE for p in norm_parts)
        if has_stop:
            continue
        # Requiere ancla en diccionario (no solo capitalización)
        if not (has_apellido or has_nombre):
            continue
        if candidate.isupper() and len(parts) >= 2:
            if not (has_apellido and has_nombre):
                continue
        add("PERSONA", candidate, m.start(), end)

    # --- Personas: MAYÚSCULAS (ej. "CARRERA TERESITA HAYDEE") ---
    caps_name_re = re.compile(
        r"\b([A-ZÁÉÍÓÚÑ]{2,}(?:[ \t]+[A-ZÁÉÍÓÚÑ]{2,}){1,4})\b"
    )
    for m in caps_name_re.finditer(text):
        candidate = m.group(1).strip()
        parts = [p for p in candidate.split() if p]
        if len(parts) < 2:
            continue
        norm_parts = [normalize_text(p) for p in parts]
        if any(p in STOPWORDS_FRASE for p in norm_parts):
            continue
        has_apellido = any(p in apellidos for p in norm_parts)
        has_nombre = any(p in nombres for p in norm_parts)
        # Basta UN ancla (nombre o apellido): los apellidos poco comunes
        # (ej. CZICZERSKYJ, MOLINERO) no están en catálogo, pero el nombre sí.
        # Los encabezados no-persona ("CONTESTA TRASLADO") no tienen ancla.
        if not (has_apellido or has_nombre):
            continue
        add("PERSONA", candidate, m.start(), m.end())

    # --- Apellido aislado tras rol judicial (ej. "víctima Speroni") ---
    rol_apellido_re = re.compile(
        r"\b(?:imputad[oa]|v[ií]ctima|testig[oa]|denunciante|querellante|"
        r"damnificad[oa]|ofendid[oa]|sospechos[oa]|investigad[oa])\s+"
        r"(?:[:,\.\s]+)?"
        r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,})\b",
        re.IGNORECASE,
    )
    for m in rol_apellido_re.finditer(text):
        surname = m.group(1)
        norm = normalize_text(surname)
        if norm in apellidos or norm in nombres:
            add("PERSONA", surname, m.start(1), m.end(1), "ruler")

    # --- Patentes / dominios vehiculares (Mercosur y formatos anteriores) ---
    patente_re = re.compile(
        r"\b("
        r"[A-Z]{2}[\s\-]?\d{3}[\s\-]?[A-Z]{2}"
        r"|[A-Z]{3}[\s\-]?\d{3}"
        r"|[A-Z][\s\-]?\d{3}[\s\-]?[A-Z]{3}"
        r")\b",
        re.IGNORECASE,
    )
    for m in patente_re.finditer(text):
        val = m.group(1).strip()
        add("PATENTE", val, m.start(1), m.end(1))

    # --- Domicilios: avenida/calle + nombre + n° (formato judicial frecuente) ---
    calle_num_re = re.compile(
        r"\b((?:avenida|av\.?|avda\.?|calle|c/)\s+"
        r"[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ\s\.\'-]{2,45}?"
        r"\s+n[°ºo\*]?\.?\s*\d{1,5})\b",
        re.IGNORECASE,
    )
    for m in calle_num_re.finditer(text):
        add("DOMICILIO", m.group(1).strip(), m.start(1), m.end(1))

    # --- Teléfonos con prefijo de área extendido (2235-51-0529, 11-5808-1688) ---
    phone_ext_re = re.compile(
        r"\b(?:11|15|\d{4})[\s\-]\d{2,4}[\s\-]\d{4}\b"
    )
    for m in phone_ext_re.finditer(text):
        add("TELEFONO", m.group(0).strip(), m.start(), m.end())

    # --- Documentos extranjeros con etiqueta ---
    doc_ext_re = re.compile(
        r"\b(?:c[eé]dula|pasaporte|passport|c\.?\s*i\.?)\s+"
        r"(?:colombian[oa]|argentino|extranjer[oa]|uruguay[oa]|dominicano|n[°º]\.?)?\s*"
        r"(?:n[°ºo\.]?|nro\.?)?\s*[:#]?\s*"
        r"([A-Z0-9][\w\-]{5,16})\b",
        re.IGNORECASE,
    )
    for m in doc_ext_re.finditer(text):
        add("OTRO", m.group(1), m.start(1), m.end(1))

    # --- Fecha de nacimiento explícita ---
    nacimiento_re = re.compile(
        r"\b(?:nacido|nacida|fecha de nacimiento)[^\.\n]{0,40}?"
        r"(\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
        r"septiembre|setiembre|octubre|noviembre|diciembre)\s+de\s+\d{4})\b",
        re.IGNORECASE,
    )
    for m in nacimiento_re.finditer(text):
        add("OTRO", m.group(1), m.start(1), m.end(1))

    # --- Comercios / hoteles con nombre propio ---
    comercio_re = re.compile(
        r"\b(?:Hotel|Automotores|Local|Comercio|TOTOS)\s+"
        r"([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ\s&\-\.]{2,40}?)\b",
        re.IGNORECASE,
    )
    for m in comercio_re.finditer(text):
        val = f"{m.group(0).split()[0]} {m.group(1).strip()}".strip()
        add("EMPRESA", val, m.start(), m.start() + len(val))

    # Catálogo Regex_limpio_v2: completa huecos (OCR, domicilios, pasaportes, etc.)
    from app.detection.regex_catalog import detect_regex_catalog

    for item in detect_regex_catalog(text):
        add(item.cat, item.original, item.start, item.end, item.source_layer)

    items.sort(key=lambda x: x.start)
    return items
