"""Límites compartidos de las búsquedas manuales sobre el texto original."""
import unicodedata


_CONNECTORS = frozenset(".@/:+-'")


def _is_word_char(char: str) -> bool:
    return char == "_" or unicodedata.category(char)[0] in "LNM"


def _is_token_char(text: str, index: int) -> bool:
    if not 0 <= index < len(text):
        return False
    char = text[index]
    if _is_word_char(char):
        return True
    if char not in _CONNECTORS:
        return False
    previous_is_word = index > 0 and _is_word_char(text[index - 1])
    next_is_word = index + 1 < len(text) and _is_word_char(text[index + 1])
    if previous_is_word and next_is_word:
        return True
    return (
        char == "+"
        and not previous_is_word
        and index + 1 < len(text)
        and text[index + 1].isdecimal()
    )


def is_complete_match(text: str, start: int, end: int) -> bool:
    """Indica si el intervalo evita cortar una palabra o dato compuesto.

    Los offsets son puntos Unicode del texto original. La puntuación de fin
    de frase no prolonga un dato; un conector entre caracteres de palabra sí.
    Una selección manual explícita no está sujeta a este filtro.
    """
    if start < 0 or end > len(text) or end <= start:
        return False
    cuts_start = _is_token_char(text, start - 1) and _is_token_char(text, start)
    cuts_end = _is_token_char(text, end - 1) and _is_token_char(text, end)
    return not cuts_start and not cuts_end


def normalize_for_search(text: str) -> str:
    """Ignora mayúsculas y todas las marcas Unicode, conservando espacios."""
    return "".join(
        char for char in unicodedata.normalize("NFD", text)
        if not unicodedata.category(char).startswith("M")
    ).lower()
