"""Domicilios delimitados por su estructura postal."""
import re


_LETTER = r"[^\W\d_]"
_ABBREVIATION = r"(?:Gral|Grl|Dr|Dra|Ing|Pte|Pres|Tte|Cnel|Cmte|Sta|Sto|Sgto|[A-Z])\."
_WORD = rf"(?:(?i:{_ABBREVIATION})|{_LETTER}+(?:[-'’]{_LETTER}+)*)"
_CAP_WORD = rf"(?:{_ABBREVIATION}|[A-ZÁÉÍÓÚÜÑ][^\W\d_]*(?:[-'’][^\W\d_]+)*)"
_CONNECTOR = r"(?i:de|del|la|las|los|el|y)"
_NOT_STREET = (
    r"ley|art[ií]culo|art|inciso|inc|decreto|resoluci[oó]n|expediente|expte|causa|"
    r"fojas|fs|folio|p[aá]gina|p[aá]g|dni|documento|cuit|cuil|tel[eé]fono|tel|"
    r"celular|cel|motor|chasis|p[oó]liza|seguimiento|denuncia|n[uú]mero|nro|n[°ºo*]?|"
    r"patente|dominio|vin|cuenta|cbu|cvu|c[oó]digo|nacional|identidad|pasaporte|"
    r"c[eé]dula|libreta|licencia|tarjeta|seguro|"
    r"ministerio|p[uú]blico|fiscal|c[aá]mara|juzgado|tribunal|sala|"
    r"compareci[oó]|declar[oó]|declara|manifest[oó]|manifiesta|solicita|solicit[oó]|"
    r"ten[ií]a|tiene|cumpli[oó]|cumple|cobr[oó]|cobro|abon[oó]|pago|pag[oó]|"
    r"fecha|a[ñn]o|mes|d[ií]a|pesos|importe|total|cantidad|edad|"
    r"domicilio|domiciliad[oa]|ubicad[oa]|sito|con|en|el|la|los|las|a|al|"
    r"hasta|desde|sobre|bajo|luego|despu[eé]s|antes|durante"
)
_SAFE_WORD = rf"(?!(?i:{_NOT_STREET})\b){_WORD}"
_SAFE_CAP = rf"(?!(?i:{_NOT_STREET})\b){_CAP_WORD}"
_PREFIX = (
    r"(?i:calle|c/|av(?:da)?\.?|avenida|bv\.?|boulevard|bulevar|pasaje|pje\.?|"
    r"psje\.?|paseo|diagonal|costanera|camino|acceso|colectora|ruta|rt\.?)"
)
_NUMBER_LABEL = r"(?:(?i:n[uú]mero|nro\.?|n[°ºo*]\.?)\s*)?"
_DATE_NAME = rf"\d{{1,2}}\s+(?i:de)\s+{_WORD}"
_BARE_NAME = rf"(?:{_DATE_NAME}|{_SAFE_CAP}(?:\s+(?:{_CONNECTOR}\s+){{0,3}}{_SAFE_CAP}){{0,6}})"
_EXPLICIT_NAME = rf"(?:{_DATE_NAME}|(?:{_CONNECTOR}\s+){{0,3}}{_SAFE_WORD}(?:\s+(?:{_CONNECTOR}\s+){{0,3}}{_SAFE_WORD}){{0,6}}|\d{{1,3}})"
_HOUSE = (
    rf"{_NUMBER_LABEL}\d{{1,5}}(?:\s*(?i:bis)|[A-Za-z])?(?!\w)"
    r"(?![ \t]*[/\-][ \t]*\d)"
    r"(?!\s+(?i:años|personas|pesos|d[ií]as|meses|veh[ií]culos|hechos|documentos)\b)"
)
_CORE_RE = re.compile(rf"(?<![\w.])(?:{_PREFIX}\s*{_EXPLICIT_NAME}|{_BARE_NAME})\s+{_HOUSE}")
_PLATE_LIKE_RE = re.compile(r"[A-Z]{1,3}\s+\d{3}", re.IGNORECASE)
_SINGLE_INITIAL_RE = re.compile(rf"[A-Z]\.?\s+{_HOUSE}", re.IGNORECASE)
_CONTEXT_RE = re.compile(
    r"\b(?:domicilio(?:\s+(?:real|legal|fiscal|constituido|particular))?|"
    r"domiciliad[oa]|residente|sito|situad[oa]|ubicad[oa]|direcci[oó]n)"
    r'''\s*(?:(?:en|es)\s+)?[:\-]?\s*(?:la\s+)?["“']?''', re.IGNORECASE,
)
_CONTEXT_CORE_RE = re.compile(rf"(?:{_PREFIX}\s*)?{_EXPLICIT_NAME}\s+{_HOUSE}")
_UNIT_BODY = r"(?:\d{1,4}[A-Za-z]?|[A-Za-z]|[IVX]{1,5})(?!\w)"
_UNIT = rf'''(?:"{_UNIT_BODY}"|“{_UNIT_BODY}”|'{_UNIT_BODY}'|{_UNIT_BODY})'''
_OPTIONAL_UNIT = rf"(?!a\s+las\s+\d){_UNIT}"
_SEP = r"(?:\s*,\s*|\s+)"
_FLOOR = (
    r"(?:\d{1,3}(?:[°ºª]|(?:er|ro|do|to|mo|vo|no)\.?)?|primer[oa]?|segund[oa]|"
    r"tercer[oa]?|cuart[oa]|quint[oa]|sext[oa]|s[eé]ptim[oa]|octav[oa]|noven[oa]|"
    r"d[eé]cim[oa]|und[eé]cim[oa]|duod[eé]cim[oa]|subsuelo)"
)
_COMPONENT_RE = re.compile(
    rf"{_SEP}(?:"
    rf"(?:piso|planta)\s*[:\-]?\s*{_FLOOR}(?:\s+{_OPTIONAL_UNIT})?"
    rf"|(?:dto\.?|dpto\.?|depto\.?|departamento|oficina|of\.?|"
    rf"unidad(?:\s+funcional)?|uf|habitaci[oó]n|hab\.?|torre|cuerpo|bloque|"
    rf"manzana|mza\.?|mz\.?|lote|casa|local|interior)\s*[:\-]?\s*{_UNIT}[°º]?"
    rf"|{_FLOOR}\s*(?:piso|planta)(?:\s+{_OPTIONAL_UNIT})?"
    rf"|(?:PB|planta\s+baja)(?:\s+{_UNIT})?"
    rf"|\d{{1,3}}[°ºª]?(?:\s*[-/]\s*|\s+){_UNIT}"
    rf"|\d{{1,3}}[°ºª]\s*{_UNIT}"
    rf"|\d{{1,3}}[A-Z](?!\w)"
    rf"|\d{{1,3}}[°ºª]"
    rf"|\d{{1,2}}(?=\s*(?:[,.;]|$))"
    rf")", re.IGNORECASE,
)
_LOCATION_RE = re.compile(
    rf"{_SEP}(?:"
    r"(?i:(?:de\s+)?esta\s+ciudad|C\.?A\.?B\.?A\.?|Capital\s+Federal|"
    r"Ciudad\s+Aut[oó]noma\s+de\s+Buenos\s+Aires|Buenos\s+Aires|C[oó]rdoba|"
    r"Mendoza|Santa\s+Fe|San\s+Juan|San\s+Luis|Entre\s+R[ií]os|La\s+Pampa|"
    r"La\s+Rioja|Tucum[aá]n|Jujuy|Salta|Corrientes|Chaco|Formosa|Misiones|"
    r"Catamarca|Neuqu[eé]n|R[ií]o\s+Negro|Chubut|Santa\s+Cruz|Santiago\s+del\s+Estero)|"
    rf"(?i:localidad|partido|provincia|ciudad)\s+(?i:de)\s+{_CAP_WORD}"
    rf"(?:\s+(?:{_CONNECTOR}\s+)?{_CAP_WORD}){{0,4}}"
    r")(?!\w)",
)
_LOCALITY_RE = re.compile(
    rf"\s*,\s*(?:(?:La|Las|Los|El|LA|LAS|LOS|EL)\s+)?{_SAFE_CAP}"
    rf"(?:\s+(?:{_CONNECTOR}\s+){{0,3}}{_SAFE_CAP}){{0,5}}(?=\s*(?:[,.;]|$))"
)
_CROSS_NAME = rf"(?:\d{{1,5}}|{_SAFE_WORD}(?:\s+(?:(?i:de|del|la|las|los)\s+){{0,3}}{_SAFE_WORD}){{0,5}})"
_CROSS_RE = re.compile(rf"{_SEP}(?i:entre)\s+{_CROSS_NAME}\s+(?i:y)\s+{_CROSS_NAME}")
_ESTATE_RE = re.compile(
    rf"\b(?i:barrio|b[°º])\s+{_EXPLICIT_NAME}"
    r"(?=\s*,?\s*(?i:manzana|mza\.?|mz\.?|lote|casa|torre|bloque)\b)"
)
_LOT_RE = re.compile(
    rf"\b(?i:manzana|mza\.?|mz\.?|lote|parcela|casa|torre|bloque)\s*{_UNIT}"
)
_CPA_RE = re.compile(r"\b[A-Z]\d{4}[A-Z]{3}\b", re.IGNORECASE)
_PARCEL_RE = re.compile(
    rf"\b(?i:circunscripci[oó]n|circ\.?)\s*[A-Z0-9]+"
    rf"\s+(?i:secci[oó]n|secc\.?)\s*[A-Z0-9]+"
    rf"(?:\s+(?i:manzana|mza\.?|mz\.?|lote|parcela|casa)\s*[A-Z0-9]+)*", re.IGNORECASE,
)
_ROUTE_RE = re.compile(
    rf"\b(?i:ruta|rt\.?)\s+(?:(?i:nacional|provincial)\s+)?{_NUMBER_LABEL}\d{{1,4}}"
    r"\s*,?\s*(?i:km\.?|kil[oó]metro)\s*\d{1,4}(?:[.,]\d{1,3})?(?!\w)"
)


def _address_end(text: str, end: int) -> int:
    for _ in range(12):
        component = (_COMPONENT_RE.match(text, end) or _CROSS_RE.match(text, end)
                     or _LOCATION_RE.match(text, end) or _LOCALITY_RE.match(text, end))
        if component is None:
            break
        end = component.end()
    return end


def address_spans(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for match in _CORE_RE.finditer(text):
        if _PLATE_LIKE_RE.fullmatch(match.group()) or _SINGLE_INITIAL_RE.fullmatch(match.group()):
            continue
        start, end = match.span()
        end = _address_end(text, end)
        spans.append((start, end, text[start:end]))
    for context in _CONTEXT_RE.finditer(text):
        if match := _CONTEXT_CORE_RE.match(text, context.end()):
            start, end = match.span()
            end = _address_end(text, end)
            spans.append((start, end, text[start:end]))
    for pattern in (_ESTATE_RE, _LOT_RE):
        for match in pattern.finditer(text):
            start, end = match.span()
            end = _address_end(text, end)
            spans.append((start, end, text[start:end]))
    for pattern in (_CPA_RE, _PARCEL_RE, _ROUTE_RE):
        spans.extend((m.start(), m.end(), m.group()) for m in pattern.finditer(text))
    spans.sort(key=lambda span: (span[0], -span[1]))
    result: list[tuple[int, int, str]] = []
    for start, end, value in spans:
        if result and result[-1][0] <= start and end <= result[-1][1]:
            continue
        result.append((start, end, value))
    return result


def is_address(surface: str, text: str = "", start: int = 0) -> bool:
    if any(pattern.fullmatch(surface) for pattern in (_CPA_RE, _PARCEL_RE, _ROUTE_RE)):
        return True
    for pattern in (_ESTATE_RE, _LOT_RE):
        if match := pattern.match(surface):
            if _address_end(surface, match.end()) == len(surface):
                return True
    if match := _CORE_RE.match(surface):
        bare_identifier = _PLATE_LIKE_RE.fullmatch(match.group()) or _SINGLE_INITIAL_RE.fullmatch(match.group())
        if not bare_identifier and _address_end(surface, match.end()) == len(surface):
            return True
    if text and start >= 0 and (match := _CONTEXT_CORE_RE.match(surface)):
        context_end = start
        if context_end and text[context_end - 1] in '\"“\'':
            context_end -= 1
        while context_end and text[context_end - 1].isspace():
            context_end -= 1
        left = text[max(0, context_end - 120):start]
        if _address_end(surface, match.end()) == len(surface):
            return any(context.end() == len(left) for context in _CONTEXT_RE.finditer(left))
    return False
