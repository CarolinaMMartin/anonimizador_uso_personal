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


_HONOR_WORDS = frozenset(normalize_text(word) for word in (
    "sr", "sra", "srta", "dr", "dra", "lic", "ing", "cdor", "cra", "arq", "señor",
    "señora", "señorita", "don", "doña", "doctor", "doctora", "licenciado",
    "licenciada", "ingeniero", "ingeniera",
))

# Un guion rodeado de espacios separa campos o títulos ("Pérez - Conexidad");
# los apellidos compuestos llevan guion sin espacios ("Pérez-Gómez").
_SPACED_SEPARATOR_RE = re.compile(r"[ \t ]+[-–—][ \t ]+")

# Terminaciones de sustantivos abstractos y adjetivos que no forman nombres
# propios cuando ninguna palabra del texto figura en los catálogos.
_ABSTRACT_SUFFIX_RE = re.compile(
    r"(?:idad|cion|sion|miento|ncia|tiva|tivo|siva|sivo|mente|ismo)$"
)


def cut_at_field_separator(value: str) -> str:
    """Devuelve el tramo previo a un separador «espacio-guion-espacio»."""
    match = _SPACED_SEPARATOR_RE.search(value)
    return value[:match.start()] if match else value


def is_abstract_phrase(value: str) -> bool:
    """True si todas las palabras significativas son términos abstractos sin ancla.

    «Conexidad Subjetiva» o «Prisión Preventiva» no son personas, aunque
    aparezcan después de un rótulo como «Víctima:» o con mayúscula inicial.
    Un nombre real con una sola palabra de esa forma («Concepción Arenales»)
    se conserva porque basta una palabra que no lo sea.
    """
    names, surnames = get_person_anchors()
    significant = [token.norm for token in _tokens(value) if token.norm not in _PARTICLES]
    return bool(significant) and all(
        token not in names and token not in surnames and _ABSTRACT_SUFFIX_RE.search(token)
        for token in significant
    )


def _comma_reading(text: str, comma: int) -> str:
    """Lee la coma en ``text[comma]``: «inversion», «lista» o «incierta».

    La forma invertida («PÉREZ, Juan», «Fernández Noble, Julia Iris») pone
    los nombres de pila después de la coma. Hay evidencia de lista cuando:

    - después de la coma sigue un nombre completo, con apellido propio
      («Mariela Paz, Hernán Luna»);
    - después del nombre siguen más nombres de pila enumerados
      («Martín, Sofía, Lucas y Valentina»);
    - antes de la coma hay sólo nombres de pila («Martín, Sofía»).

    Sin un nombre de pila del catálogo después de la coma la lectura es
    incierta: puede ser una inversión con nombres fuera del catálogo.
    """
    names, surnames = get_person_anchors()
    pure_names = names - surnames
    pure_surnames = surnames - names
    base = comma + 1
    following = _tokens(text[base:base + 160])
    if not following or not _HORIZONTAL.fullmatch(text[base:base + following[0].start] or " "):
        return "incierta"
    # Tramo de nombres después de la coma.
    run_end = base + following[0].end
    next_index = len(following)
    for index, token in enumerate(following[1:], start=1):
        gap = text[run_end:base + token.start]
        if len(following[index - 1].raw) == 1:
            gap = gap.removeprefix(".")  # inicial: «Ethel B. Pérez»
        ends_run = (token.norm in PERSONA_BOUNDARY_WORDS or token.norm in {"y", "e"}
                    or (not token.raw[0].isupper() and token.norm not in _PARTICLES))
        if not _HORIZONTAL.fullmatch(gap) or ends_run:
            next_index = index
            break
        if token.norm in pure_surnames:
            return "lista"  # nombre completo después de la coma: es otra persona
        run_end = base + token.end
    if next_index < len(following):
        candidate = following[next_index]
        tail = text[run_end:base + candidate.start]
        if candidate.norm in {"y", "e"} and _HORIZONTAL.fullmatch(tail) and next_index + 1 < len(following):
            candidate, tail = following[next_index + 1], ","
        if (tail.strip(" .") == "," and candidate.norm in pure_names
                and following[0].norm in names):
            return "lista"  # enumeración de nombres de pila
    line_start = max(text.rfind("\n", 0, comma), text.rfind("\r", 0, comma)) + 1
    left: list[_Token] = []
    boundary = comma
    for token in reversed(_tokens(text[line_start:comma])):
        token = _Token(token.start + line_start, token.end + line_start, token.raw, token.norm)
        gap = text[token.end:boundary]
        if left and not _HORIZONTAL.fullmatch(gap):
            break
        if not left and gap.strip(" \t."):
            return "incierta"
        if (token.norm in PERSONA_BOUNDARY_WORDS or token.norm in _HONOR_WORDS
                or token.norm in {"y", "e"}):
            break
        if token.norm in _PARTICLES:
            boundary = token.start
            continue
        if not token.raw[0].isupper():
            break
        left.append(token)
        boundary = token.start
    if not left:
        return "incierta"
    if all(token.norm in pure_names for token in left) and following[0].norm in names:
        return "lista"
    return "inversion" if following[0].norm in names else "incierta"


def comma_is_name_inversion(text: str, comma: int) -> bool:
    """True si la coma invierte un nombre conocido («PÉREZ, Juan»)."""
    return _comma_reading(text, comma) == "inversion"


def comma_separates_people(text: str, comma: int) -> bool:
    """True si hay evidencia de que la coma enumera personas distintas."""
    return _comma_reading(text, comma) == "lista"


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
    following = words[index + 1]
    after = text[following.end:following.end + 2]
    if after[:1] == ',' and comma_is_name_inversion(text, following.end):
        return True  # «Pérez, Juan y López, Ana»: la conjunción abre otro nombre invertido
    if following.norm not in names:
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
                        and significant
                        and comma_is_name_inversion(text, text.index(",", last.end))):
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
