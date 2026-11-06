"""Nombres delimitados por estructura, catálogos y contexto explícito."""
import re
from bisect import bisect_right
from dataclasses import dataclass

from app.detection.dictionaries import NAME_PARTICLES, STOPWORDS_FRASE, get_person_anchors
from app.detection.form_fields import FIELD_LABEL_RE, field_value_end
from app.resolution.normalize import normalize_text


PERSONA_BOUNDARY_WORDS = {
    "solicita", "solicito", "solicitar", "declara", "declaro", "declarar",
    "declararon", "manifiesta", "manifesto", "manifestaron", "comparece",
    "comparecio", "presenta", "presento", "presentaron", "rechace", "demanda",
    "afirma", "afirmo", "nego", "dispuso", "requiere", "requirio", "considera",
    "considero", "expresa", "expreso", "informa", "informo", "denuncia",
    "denuncio", "resuelve", "resolvio", "sentencia", "escrito", "medida",
    "juzgado", "tribunal", "judicial", "nacional", "municipal", "provincial",
    "que", "quien", "como", "se", "su", "sus", "ante", "contra", "sobre",
    "para", "por", "con", "en", "fue", "ha", "habia", "poder",
    "acierta", "sostiene", "sostuvo", "explico", "explica", "apelo",
    "recibio", "respondio", "indico", "dijo", "informaron", "indicaron",
    "ratifico", "ratifica", "relato", "relata", "nacido", "nacida",
    "domicilio", "domiciliado", "domiciliada", "dni", "cuit", "cuil",
    "telefono", "celular", "correo", "email", "expediente", "expte",
    "abogado", "abogada", "letrado", "letrada", "juez", "jueza", "fiscal",
    "secretario", "secretaria", "firmado", "firma", "aclaracion",
    "imputado", "imputada", "victima", "denunciante", "testigo", "testiga",
    "nombre", "nombres", "apellido", "apellidos", "edad", "nacionalidad",
    "el", "un", "una", "este", "esta", "es", "son", "soy", "tiene",
    "siendo", "quedo", "resulto", "cuya", "cuyo", "segun", "consta",
    "adquirio", "adquiere", "suscribio", "suscribe", "asumio", "asume",
    "comparecieron", "comparecen", "celebro", "celebra", "vendio", "vende",
    "compro", "compra", "entrego", "entrega", "denunciado", "denunciada",
    "director", "directora", "presidente", "presidenta", "vicepresidente",
    "ministro", "ministra", "doctor", "doctora", "licenciado", "licenciada",
    "ingeniero", "ingeniera", "firmo", "firman", "firmaron",
    "empresa", "aseguradora", "compania", "comercio", "local", "hotel",
    "automotores", "concesionaria", "cooperativa", "fundacion", "asociacion",
}

_PARTICLES = NAME_PARTICLES
_WORD = re.compile(r"[^\W\d_](?:[^\W\d_]|[\u0300-\u036f])*(?:[-'’ʼ][^\W\d_](?:[^\W\d_]|[\u0300-\u036f])*)*", re.UNICODE)
_HORIZONTAL = re.compile(r"[ \t\u00a0]+")
_NAME_LABEL = (
    r"(?:nombre(?:s)?(?:[ \t]+completo(?:s)?)?(?:[ \t]+y[ \t]+apellido(?:s)?)?|apellido(?:s)?(?:[ \t]+y[ \t]+nombre(?:s)?)?"
    r"|firmado[ \t]+por|firma|aclaraci[oó]n)"
)
_PERSON_ROLE = (
    r"(?:imputad[oa]|v[ií]ctima|denunciante|testig[oa]|querellante|damnificad[oa]"
    r"|ofendid[oa]|sospechos[oa]|investigad[oa]|menor|niñ[oa]|adolescente"
    r"|progenitor[oa]|representante[ \t]+legal|actor[oa]|demandad[oa])"
)
_HONOR = r"(?:sr|sra|srta|dr|dra|lic|ing|cdor|cra|arq|señor|señora|señorita|don|doña|doctor|doctora|licenciado|licenciada|ingeniero|ingeniera)\.?"
_CONTEXT = re.compile(
    rf"\b(?:{_NAME_LABEL}[ \t]*[:|][ \t\r\n]*|{_PERSON_ROLE}\b[ \t]*[:,.|]?[ \t]*|{_HONOR}[ \t\r\n]+)"
    rf"(?:{_HONOR}[ \t\r\n]+)?", re.IGNORECASE,
)
_CONTEXT_END = re.compile(rf"{_CONTEXT.pattern}$", re.IGNORECASE)


def has_person_context(text: str, start: int) -> bool:
    label_end = start
    while label_end > 0 and text[label_end - 1].isspace():
        label_end -= 1
    return bool(_CONTEXT_END.search(text[max(0, label_end - 100):start]))


@dataclass(frozen=True)
class _Token:
    start: int
    end: int
    raw: str
    norm: str


def _tokens(text: str) -> list[_Token]:
    return [_Token(match.start(), match.end(), match.group(), normalize_text(match.group()))
            for match in _WORD.finditer(text)]


def is_person_name_candidate(value: str) -> bool:
    names, surnames = get_person_anchors()
    significant = [token for token in _tokens(value) if token.norm not in _PARTICLES]
    return (
        2 <= len(significant) <= 8
        and not any(token.norm in PERSONA_BOUNDARY_WORDS for token in significant)
        and all(token.norm in names or token.norm in surnames or token.raw[0].isupper()
                for token in significant)
        and (
            sum(token.norm in names for token in significant) >= 2
            or any(name.norm in names and surname.norm in surnames and i != j
                   for i, name in enumerate(significant) for j, surname in enumerate(significant))
        )
    )


def _unknown_lower_can_continue(
    significant: list[_Token], names: frozenset[str], surnames: frozenset[str], contextual: bool,
) -> bool:
    if not contextual:
        return False
    if not significant or all(token.raw.islower() for token in significant):
        return True
    if significant[-1].norm in surnames and significant[-1].norm not in names:
        return False
    return len(significant) == 1 or all(token.norm in names for token in significant)


def _conjunction_splits_name(
    text: str, words: list[_Token], index: int, significant: list[_Token],
    names: frozenset[str], surnames: frozenset[str],
) -> bool:
    if not significant or words[index].norm not in {'y', 'e'} or index + 1 >= len(words):
        return False
    if words[index + 1].norm not in names:
        return False
    right = []
    previous = words[index]
    for word in words[index + 1:index + 9]:
        gap = text[previous.end:word.start]
        if len(previous.raw) == 1:
            gap = gap.removeprefix('.')
        if gap.strip() == ',' and word.norm in names and (
            significant[0].norm not in names or significant[0].norm in surnames
        ):
            return False
        if not gap.isspace() or word.norm in PERSONA_BOUNDARY_WORDS or word.norm in {'y', 'e'}:
            break
        if word.norm not in _PARTICLES:
            if not (word.norm in names or word.norm in surnames or word.raw[0].isupper()):
                break
            right.append(word)
        previous = word
    return len(right) >= 2 or (len(significant) == 1 and significant[0].norm in names)


def contains_person_list(value: str) -> bool:
    names, surnames = get_person_anchors()
    words = _tokens(value)
    significant = []
    for index, word in enumerate(words):
        if _conjunction_splits_name(value, words, index, significant, names, surnames):
            return True
        if word.norm not in _PARTICLES:
            significant.append(word)
    return False


def trim_persona_tail(value: str, allow_unknown_lower: bool = False) -> str:
    value = value[:field_value_end(value, 0, len(value))]
    names, surnames = get_person_anchors()
    anchors = names | surnames
    last_end = 0
    significant = []
    for token in _tokens(value):
        if token.norm in PERSONA_BOUNDARY_WORDS:
            break
        if (token.raw.islower() and token.norm not in anchors and token.norm not in _PARTICLES
                and not _unknown_lower_can_continue(significant, names, surnames, allow_unknown_lower)):
            break
        if token.norm not in _PARTICLES:
            significant.append(token)
            last_end = token.end
            if len(token.raw) == 1 and value[last_end:last_end + 1] == ".":
                last_end += 1
    return value[:last_end].rstrip(" ,.;:")


def person_name_spans(text: str) -> list[tuple[int, int, str, bool]]:
    names, surnames = get_person_anchors()
    anchors = names | surnames
    words = _tokens(text)
    contexts = {match.end() for match in _CONTEXT.finditer(text)}
    fields = [(match.start(), match.end()) for match in FIELD_LABEL_RE.finditer(text)]
    field_starts = [start for start, _ in fields]

    def in_field_label(position: int) -> bool:
        index = bisect_right(field_starts, position) - 1
        return index >= 0 and position < fields[index][1]

    results = []
    consumed_end = -1
    for index, first in enumerate(words):
        if first.start < consumed_end:
            continue
        if in_field_label(first.start):
            continue
        explicit = first.start in contexts
        if first.norm in _PARTICLES or first.norm in PERSONA_BOUNDARY_WORDS:
            continue
        if first.start and (text[first.start - 1].isalnum() or text[first.start - 1] in "_@"):
            continue
        if not explicit and first.norm not in anchors and not first.raw[0].isupper():
            continue
        significant = []
        last = None
        end = first.end
        comma_seen = False
        for token_index, token in enumerate(words[index:index + 12], start=index):
            if in_field_label(token.start):
                break
            if last is not None:
                gap = text[last.end:token.start]
                if len(last.raw) == 1:
                    gap = gap.removeprefix(".")
                if ("," in gap and not comma_seen and gap.strip() == ","
                        and token.norm in names
                        and significant
                        and (significant[0].norm not in names or significant[0].norm in surnames)):
                    comma_seen = True
                elif not _HORIZONTAL.fullmatch(gap):
                    soft_wrap = bool(re.fullmatch(r"[ \t\u00a0]*\r?\n[ \t\u00a0]*", gap))
                    continuation = ((explicit and len(significant) == 1) or token.norm in surnames
                                    or significant and all(word.norm in names for word in significant))
                    if not (soft_wrap and continuation):
                        break
            if token.norm in PERSONA_BOUNDARY_WORDS:
                break
            if token.norm in _PARTICLES:
                if _conjunction_splits_name(text, words, token_index, significant, names, surnames):
                    break
                last = token
                continue
            if token.norm in STOPWORDS_FRASE and token.norm not in anchors:
                break
            if not (token.norm in anchors or token.raw[0].isupper()
                    or _unknown_lower_can_continue(significant, names, surnames, explicit)):
                break
            if len(token.raw) == 1 and text[token.end:token.end + 1] != ".":
                break
            significant.append(token)
            last = token
            end = token.end
            if len(significant) >= 8:
                break
        if not significant:
            continue
        if not explicit and (len(significant) < 2 or not any(word.norm in anchors for word in significant)):
            continue
        if end < len(text) and (text[end].isalnum() or text[end] in "_@"):
            continue
        results.append((first.start, end, text[first.start:end], explicit))
        consumed_end = end
    return results
