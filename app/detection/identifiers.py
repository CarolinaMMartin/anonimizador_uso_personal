"""Identificadores documentales y de contacto, con límites de campo compartidos."""
from __future__ import annotations

import re
from bisect import bisect_left
from collections.abc import Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.detection.regex_ar import RawItem

_NUMBER = r"(?:n[úu]mero|n[úu]m\.?|nro\.?|n[°ºo*]\.?|n\.|n\b)"
_SEPARATOR = rf"\s*(?:[:=#|–—-]\s*)?(?:{_NUMBER}\s*)?[:=#|°º–—-]?\s*"
_CODE = (
    r"(?:(?-i:[A-Z]{1,8})[ \t]+(?=[0-9]))?"
    r"[A-Z0-9]{1,48}(?:[ \t]*[-/_][ \t]*[A-Z0-9]{1,32}|\.[A-Z0-9]{1,32}){0,8}"
)
_PHONE = r"\+?\(?[0-9][0-9() ./\s-]{4,34}[0-9](?!\w)"
_DNI = r"(?:[0-9Oo]{1,2}[.\s-]{1,3}[0-9Oo]{3}[.\s-]{1,3}[0-9Oo]{3}|[0-9Oo]{5,8})(?!\w)"
_PLATE = (
    r"(?:[A-Z]{2}[ .-]*\d{3}[ .-]*[A-Z]{2}"
    r"|[A-Z]{3}[ .-]*\d{3}"
    r"|[A-Z][ .-]*\d{3}[ .-]*[A-Z]{3}"
    r"|\d{3}[ .-]*[A-Z]{3}"
    r"|[A-Z][ .-]*\d{6,7})(?!\w)"
)
_VIN = r"[A-HJ-NPR-Z0-9]{17}"
_TRACKING_SUBJECT = r"(?:denuncias?|reclamos?|tr[áa]mites?|consultas?)"
_TRACKING = (
    rf"(?:(?:{_NUMBER}|c[óo]digo|identificador|id)[ \t]+(?:de[ \t]+)?"
    rf"(?:seguimiento|{_TRACKING_SUBJECT})"
    rf"|seguimiento|{_TRACKING_SUBJECT})"
    rf"(?:[ \t]+(?:(?:de|del)[ \t]+(?:(?:la|las|el)[ \t]+)?)?{_TRACKING_SUBJECT})?"
)
_DOCUMENT = (
    r"(?:d\.?[ \t]*n\.?[ \t]*i\.?|documento(?:[ \t]+nacional[ \t]+de[ \t]+identidad)?"
    r"|d\.?[ \t]*u\.?|l\.?[ \t]*[ec]\.?)"
)
_PHONE_LABEL = (
    r"(?:tel[ée]fonos?(?:[ \t]+(?:fijos?|m[óo]vil(?:es)?|particular(?:es)?|laboral(?:es)?|de[ \t]+contacto))?"
    r"|tel\.?|celulares?|cel\.?|m[óo]vil(?:es)?|fijos?|l[íi]neas?|whats?app|contacto[ \t]+telef[óo]nico)"
)
_FOREIGN_DOCUMENT = (
    r"(?:pasaporte|passport|c[ée]dula(?:[ \t]+de[ \t]+identidad)?|c\.[ \t]*i\.)"
    r"(?:[ \t]+(?:argentin[oa]|extranjer[oa]|colombian[oa]|uruguay[oa]|"
    r"venezolan[oa]|dominican[oa]|chilen[oa]|paraguay[oa]|bolivian[oa]|peruan[oa]|brasile[ñn][oa]|brasiler[oa]))?"
)


def _labeled(label: str, value: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){label}{_SEPARATOR}(?P<value>{value})(?!\w)", re.IGNORECASE)


_RULES = (
    ("DNI", "dni", _labeled(_DOCUMENT, _DNI)),
    ("CUIT", "cuit", _labeled(r"c\.?[ \t]*u\.?[ \t]*i\.?[ \t]*[tl]\.?", r"[0-9Oo]{2}[ -]*[0-9Oo]{8}[ -]*[0-9Oo]")),
    ("CUIT", "cuit", _labeled(r"domicilio[ \t]+(?:electr[óo]nico|autorizado|fiscal|legal)", r"[0-9]{11}")),
    ("TELEFONO", "phone", _labeled(_PHONE_LABEL, _PHONE)),
    ("PATENTE", "plate", _labeled(r"(?:patente|dominio|matr[íi]cula)(?:[ \t]+(?:vehicular|del[ \t]+veh[íi]culo))?", _PLATE)),
    ("EXPEDIENTE", "code", _labeled(r"(?:expediente(?:[ \t]+SAC)?|expte\.?|exp\.?|causa|legajo|CUIJ|I\.?[ \t]*P\.?[ \t]*P\.?)(?:[ \t]+(?:judicial|penal))?", _CODE)),
    ("EXPEDIENTE", "code", _labeled(r"(?:f\.?[ \t]*s\.?|l\.?[ \t]*e\.?)", r"\d{1,8}(?:[/-]\d{1,8})+")),
    ("OTRO", "tracking", _labeled(_TRACKING, _CODE)),
    ("OTRO", "code", _labeled(r"p[óo]liza(?:[ \t]+(?:de[ \t]+)?seguro(?:s)?)?", _CODE)),
    ("OTRO", "code", _labeled(r"(?:chasis|chassis|bastidor|VIN|motor)(?:[ \t]+(?:del[ \t]+veh[íi]culo|de[ \t]+identificaci[óo]n))?", _CODE)),
    ("OTRO", "code", _labeled(_FOREIGN_DOCUMENT, _CODE)),
    ("OTRO", "bank", _labeled(r"(?:C\.?B\.?U\.?|C\.?V\.?U\.?|cuenta(?:[ \t]+(?:bancaria|corriente|de[ \t]+ahorro))?|caja[ \t]+de[ \t]+ahorro|c/c|c/a)", _CODE)),
    ("OTRO", "fiscal", _labeled(r"(?:C\.?A\.?E\.?A\.?|C\.?A\.?[EI]\.?|c[óo]digo[ \t]+de[ \t]+autorizaci[óo]n[ \t]+(?:electr[óo]nic[oa]|de[ \t]+impresi[óo]n))", r"\d{8,20}")),
    ("OTRO", "fiscal", _labeled(r"(?:comp(?:robante)?\.?|factura|recibo|remito|ticket)(?:[ \t]+electr[óo]nic[oa])?[ \t]+" + _NUMBER, r"\d{1,5}[ -]\d{6,12}|\d{6,12}")),
    ("OTRO", "fiscal", _labeled(r"(?:ingresos[ \t]+brutos|I\.?I\.?B\.?B\.?)", r"\d{2,4}[ -]\d{5,12}(?:[ -]\d)?|\d{6,15}")),
)

_URL_RE = re.compile(r"(?<!\w)(?:https?://|www\.)[^\s<>\"“”]+", re.IGNORECASE)
_VIN_RE = re.compile(rf"(?<!\w){_VIN}(?!\w)", re.IGNORECASE)
_DNI_RE = re.compile(r"(?<![\w.])\d{1,2}\.\d{3}\.\d{3}(?!\w|\.\d)")
_CUIT_RE = re.compile(r"(?<![\w\d-])\d{2}[ -]?\d{8}[ -]?\d(?![\w\d-])")
_CUIJ_RE = re.compile(r"\bJ-\d{2}-\d{6,9}-\d/\d{4}-\d\b", re.IGNORECASE)
_NUMBERED_CASE_RE = _labeled(_NUMBER, r"\d{1,8}(?:[ \t]*[/-][ \t]*\d{1,8})+")
_PLATE_RE = re.compile(rf"(?<![\w./-]){_PLATE}", re.IGNORECASE)
_INTERNATIONAL_PHONE_RE = re.compile(rf"(?<!\w)(?:\+|00|(?=54))[1-9][0-9() ./\t\u00a0-]{{6,30}}[0-9](?!\w)")
_DOMESTIC_PHONE_RE = re.compile(
    rf"(?<!\w)(?:\(?0?(?:11|[23]\d{{2,3}})\)?[ .-]+(?:15[ .-]*)?\d{{3,4}}[ .-]?\d{{4}}"
    rf"|(?:11|15)\d{{8}}|549\d{{10}})(?!\w)"
)
_PHONE_EXTENSION_RE = re.compile(r"[ \t]*(?:int(?:erno)?\.?|ext(?:ensi[óo]n)?\.?)\s*[:#]?\s*\d{1,6}\b", re.IGNORECASE)
_NON_CODES = frozenset({"pendiente", "asignado", "asignar", "desconocido", "desconocida", "inexistente", "numero", "número", "seguimiento", "recibida", "recibido", "denuncia", "reservado"})
_NON_PLATES = frozenset({"LEY", "ART", "CAP", "DOC", "INC", "REG", "TIT", "CAM", "CPC", "CCC", "CPE", "CPP", "ORD", "RES", "DEC", "EXP", "LIB", "FOL", "ROL", "IVA", "AFP", "ANS", "AFA", "VIN", "COD", "NUM", "NRO", "TEL", "CEL", "DNI", "CUIT", "CUIL", "CBU", "CVU"})
_MONEY_RE = re.compile(r"\$|\b(?:pesos?|monto|suma|capital|honorarios|indemnizaci[óo]n|importe|total)\b", re.IGNORECASE)
_PHONE_CONTINUATION_RE = re.compile(rf"[ \t]*(?:[,/;]|\b[yo]\b)[ \t]*(?P<value>{_PHONE})", re.IGNORECASE)
_LOCAL_PHONE_RE = re.compile(r"(?<!\w)(?:\d{3,4}[ .-]\d{4}|\d{6,10})(?!\w)")


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value.replace("O", "0").replace("o", "0"))


def _valid_value(kind: str, value: str) -> bool:
    digits = _digits(value)
    if kind == "dni":
        return 5 <= len(digits) <= 8
    if kind == "cuit":
        return len(digits) == 11 and len(set(digits)) > 1
    if kind == "phone":
        return 6 <= len(digits) <= 15 and bool(digits.strip("0"))
    if kind == "plate":
        return True
    if kind == "fiscal":
        return bool(digits.strip("0"))
    if len(value) > 120 or value.lower() in _NON_CODES:
        return False
    return bool(re.search(r"[0-9]", value))


def _iter_spans(text: str, *, labeled_only: bool = False) -> Iterator[tuple[str, int, int]]:
    labeled_phone_ranges: list[tuple[int, int]] = []
    labeled_ranges: list[tuple[int, int]] = []
    for cat, kind, pattern in _RULES:
        for match in pattern.finditer(text):
            value = match.group("value")
            alpha_tracking = (
                kind == "tracking" and len(value) >= 6 and value.isascii()
                and re.fullmatch(r"[A-Za-z0-9]+(?:[ ./_-][A-Za-z0-9]+)*", value)
                and value.lower() not in _NON_CODES
                and re.search(r"seguimiento|c[óo]digo|identificador", match.group(), re.IGNORECASE)
                and (value.isupper() or re.search(r"[:=#|]", match.group()))
            )
            valid = _valid_value(kind, value) or alpha_tracking
            if kind == "tracking" and len(_digits(value)) < 4 and not re.search(
                rf"seguimiento|c[óo]digo|identificador|{_NUMBER}|[:=#]", match.group()[:match.start("value") - match.start()], re.IGNORECASE
            ):
                valid = False
            if kind == "phone" and not valid:
                parts = list(_LOCAL_PHONE_RE.finditer(value))
                if parts and not _LOCAL_PHONE_RE.sub("", value).strip(" /\t\u00a0"):
                    for part in parts:
                        start, end = match.start("value") + part.start(), match.start("value") + part.end()
                        labeled_phone_ranges.append((start, end))
                        yield cat, start, end
            if valid:
                end = match.end("value")
                if kind == "phone":
                    extension = _PHONE_EXTENSION_RE.match(text, end)
                    if extension:
                        end = extension.end()
                    labeled_phone_ranges.append((match.start("value"), end))
                yield cat, match.start("value"), end
                labeled_ranges.append((match.start("value"), end))
                if kind == "phone":
                    while continuation := _PHONE_CONTINUATION_RE.match(text, end):
                        if not _valid_value("phone", continuation.group("value")):
                            break
                        end = continuation.end("value")
                        labeled_phone_ranges.append((continuation.start("value"), end))
                        yield cat, continuation.start("value"), end

    if labeled_only:
        return

    for match in _URL_RE.finditer(text):
        value = match.group().rstrip(".,;:!?)]}'")
        if value:
            yield "OTRO", match.start(), match.start() + len(value)
    for match in _VIN_RE.finditer(text):
        if re.search(r"[0-9]", match.group()) and re.search(r"[A-Z]", match.group(), re.IGNORECASE):
            yield "OTRO", match.start(), match.end()
    for match in _CUIJ_RE.finditer(text):
        yield "EXPEDIENTE", match.start(), match.end()
    for match in _NUMBERED_CASE_RE.finditer(text):
        start, end = match.span("value")
        if not any(left < end and start < right for left, right in labeled_ranges):
            yield "EXPEDIENTE", start, end
    for match in _DNI_RE.finditer(text):
        context = text[max(0, match.start() - 80):min(len(text), match.end() + 40)]
        if not _MONEY_RE.search(context):
            yield "DNI", match.start(), match.end()
    for match in _CUIT_RE.finditer(text):
        from app.detection.regex_ar import validate_cuit

        if validate_cuit(match.group()):
            yield "CUIT", match.start(), match.end()
    for match in _PLATE_RE.finditer(text):
        compact = re.sub(r"[ .-]", "", match.group()).upper()
        if compact[:3] in _NON_PLATES or re.fullmatch(r"[A-Z]\d{6,7}", compact):
            continue
        if re.fullmatch(r"\d{3}[A-Z]{3}", compact) and compact[-3:] in _NON_PLATES | {"TEL", "CEL", "DNI", "CBU", "CVU"}:
            continue
        yield "PATENTE", match.start(), match.end()
    for pattern in (_INTERNATIONAL_PHONE_RE, _DOMESTIC_PHONE_RE):
        for match in pattern.finditer(text):
            if any(start < match.end() and match.start() < end for start, end in labeled_phone_ranges):
                continue
            if 10 <= len(_digits(match.group())) <= 15 and _valid_value("phone", match.group()):
                end = match.end()
                extension = _PHONE_EXTENSION_RE.match(text, end)
                if extension:
                    end = extension.end()
                yield "TELEFONO", match.start(), end


def is_sensitive_identifier(cat: str, surface: str, text: str, start: int) -> bool:
    """Valida el mismo intervalo que el detector, conservando su contexto."""
    if not text or start < 0 or text[start:start + len(surface)] != surface:
        return False
    base = max(0, start - 180)
    end = start + len(surface)
    window = text[base:min(len(text), end + 80)]
    return any(
        found_cat == cat and left + base == start and right + base == end
        for found_cat, left, right in _iter_spans(window)
    )


def _alias_pattern(cat: str, surface: str) -> tuple[str, str] | None:
    value = surface.strip()
    if cat == "TELEFONO" and _PHONE_EXTENSION_RE.search(value):
        return None
    if cat in {"DNI", "CUIT"}:
        value = value.replace("O", "0").replace("o", "0")
    compact = re.sub(r"[^A-Za-z0-9]", "", value).upper()
    if len(compact) < 6 or not compact.isascii():
        return None
    if compact.isdigit():
        separator = r"[ ./\t\u00a0()_-]{0,3}" if "/" in value or "_" in value else r"[ .\t\u00a0()-]{0,3}"
        body = separator.join(compact)
        if cat == "TELEFONO":
            body = r"\+?" + body
    else:
        pieces = re.findall(r"[A-Za-z0-9]+|[-/._]|[ \t]+", value)
        if "".join(pieces) != value:
            return None
        body = "".join(
            r"[ \t]*" if piece.isspace()
            else rf"[ \t]*{re.escape(piece)}?[ \t]*" if piece in "-/._"
            else re.escape(piece)
            for piece in pieces
        )
    return compact, body


def _identifier_aliases(
    text: str, spans: list[tuple[str, int, int]]
) -> Iterator[tuple[str, int, int]]:
    seeds: dict[str, dict[str, set[str]]] = {}
    for cat, start, end in _iter_spans(text, labeled_only=True):
        alias = _alias_pattern(cat, text[start:end])
        if alias:
            compact, pattern = alias
            seeds.setdefault(compact, {}).setdefault(cat, set()).add(pattern)
    alternatives: set[str] = set()
    categories: dict[str, str] = {}
    for compact, owners in seeds.items():
        cat = next(iter(owners)) if len(owners) == 1 else "OTRO"
        patterns = set().union(*owners.values())
        alternatives.update(patterns)
        categories[compact] = cat
    if not alternatives:
        return
    reserved: list[tuple[int, int]] = []
    for _, start, end in spans:
        if reserved and start <= reserved[-1][1]:
            reserved[-1] = (reserved[-1][0], max(end, reserved[-1][1]))
        else:
            reserved.append((start, end))
    starts = [start for start, _ in reserved]
    pattern = re.compile(
        rf"(?<![\w/.-])(?:{'|'.join(sorted(alternatives))})(?![\w/-]|\.[A-Za-z0-9])",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        start, end = match.span()
        prior = bisect_left(starts, end) - 1
        if prior >= 0 and reserved[prior][1] > start:
            continue
        compact = re.sub(r"[^A-Za-z0-9]", "", match.group()).upper()
        yield categories[compact], start, end


def detect_identifiers(text: str) -> list[RawItem]:
    from app.detection.regex_ar import RawItem

    spans = sorted(set(_iter_spans(text)), key=lambda span: (span[1], -span[2], span[0]))
    items = [
        RawItem(cat=cat, original=text[start:end], start=start, end=end, source_layer="structured")
        for cat, start, end in spans
    ]
    items.extend(
        RawItem(cat=cat, original=text[start:end], start=start, end=end, source_layer="structured_alias")
        for cat, start, end in _identifier_aliases(text, spans)
    )
    return sorted(items, key=lambda item: (item.start, -item.end, item.cat))
