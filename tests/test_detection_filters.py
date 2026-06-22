"""Regresión de casos sucios encontrados en `equivalencias (28).csv`.

Cada test apunta a una fila concreta del CSV que el detector marcaba mal
(falsos positivos, frases truncadas, categorías erradas o nombres con
prefijos pegados). Si alguno vuelve a fallar, lo detectamos antes de
volver a generar el CSV manualmente.
"""
from __future__ import annotations

import pytest

from app.detection.filters import is_valid_detection
from app.detection.regex_ar import _clean_persona_surface, detect_regex_ar
from app.resolution.normalize import (
    get_surnames,
    normalize_mention,
    tokenize_name,
)


# ---------------------------------------------------------------------------
# ORGANISMO: verbos, conectores narrativos y abreviaturas truncadas
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "surface",
    [
        "Tribunal Superior quien revise la sentencia",
        "Cámara se apartó",
        "Defensoría en lo Contravencional nro",
        "Tribunal Superior considera que",
        "Procuración resolverá",
    ],
)
def test_organismo_rechaza_frases_narrativas(surface: str) -> None:
    assert not is_valid_detection("ORGANISMO", surface)


def test_organismo_acepta_nombres_normales() -> None:
    assert is_valid_detection("ORGANISMO", "Tribunal Superior de Justicia")
    assert is_valid_detection(
        "ORGANISMO", "Juzgado en lo Contencioso Administrativo"
    )


# ---------------------------------------------------------------------------
# PATENTE: rechazar citas normativas (Ley, Art, Inc, …)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "surface",
    [
        "Ley 471",
        "Art 123",
        "Inc 5",
        "Cap 200",
        "CPC 100",
        "Reg 050",
        "Doc 999",
    ],
)
def test_patente_rechaza_citas_normativas(surface: str) -> None:
    assert not is_valid_detection("PATENTE", surface)


@pytest.mark.parametrize(
    "surface",
    ["AB 123 CD", "ABC 123", "A123BCD", "AB-123-CD"],
)
def test_patente_acepta_dominios_reales(surface: str) -> None:
    assert is_valid_detection("PATENTE", surface)


# ---------------------------------------------------------------------------
# OTRO: exigir dígito en el surface (no palabras comunes)
# ---------------------------------------------------------------------------

def test_otro_rechaza_palabra_sin_digito() -> None:
    # "recibida" estaba en el CSV como DATO_1, era un falso positivo.
    text = "documento recibida en la mesa de entradas."
    start = text.index("recibida")
    assert not is_valid_detection("OTRO", "recibida", text, start)


def test_otro_acepta_documento_extranjero_con_numero() -> None:
    text = "cédula colombiana CC-12345678"
    start = text.index("CC-12345678")
    assert is_valid_detection("OTRO", "CC-12345678", text, start)


# ---------------------------------------------------------------------------
# PERSONA: prefijos sucios, verbos sentence-initial, stoplist administrativa
# ---------------------------------------------------------------------------

def test_persona_limpia_prefijo_c_slash() -> None:
    cleaned, offset = _clean_persona_surface("c/ Pérez", 100)
    assert cleaned == "Pérez"
    assert offset > 100  # avanzó al menos algunos caracteres


def test_persona_limpia_prefijo_en_slash() -> None:
    cleaned, _ = _clean_persona_surface("en/ Idalgo", 0)
    assert cleaned == "Idalgo"


def test_persona_limpia_newlines_y_slash() -> None:
    cleaned, _ = _clean_persona_surface("c/\n\nGCBA", 0)
    assert cleaned == "GCBA"


def test_persona_recorta_verbo_sentence_initial() -> None:
    # "Acierta" no aparece en el diccionario de nombres; el resto
    # ("Silvia Palacio") sí tiene anclas. Debe quedar "Silvia Palacio…".
    cleaned, offset = _clean_persona_surface("Acierta Silvia Palacio de Caeiro", 50)
    assert cleaned.lower().startswith("silvia")
    assert offset > 50


@pytest.mark.parametrize(
    "surface",
    [
        "Carrera Municipal",
        "Fuentes Ceremonias",
        "GCBA SOBRE EMPLEO",
        "Publicodiferencias",
    ],
)
def test_persona_rechaza_terminos_administrativos(surface: str) -> None:
    assert not is_valid_detection("PERSONA", surface)


# ---------------------------------------------------------------------------
# EMPRESA: SACIFIA y variantes
# ---------------------------------------------------------------------------

def test_empresa_detecta_sacifia() -> None:
    text = "Notificar a Lesko SACIFIA en su domicilio legal."
    items = detect_regex_ar(text)
    empresas = [it for it in items if it.cat == "EMPRESA"]
    assert any("Lesko" in it.original or "SACIFIA" in it.original for it in empresas)


# ---------------------------------------------------------------------------
# DOMICILIO: "Departamento Ejecutivo" no debe ser detectado como DOMICILIO
# ---------------------------------------------------------------------------

def test_departamento_ejecutivo_no_es_domicilio() -> None:
    text = "El Departamento Ejecutivo dictó la resolución correspondiente."
    items = detect_regex_ar(text)
    domicilios = [it for it in items if it.cat == "DOMICILIO"]
    assert not any("Departamento Ejecutivo" in it.original for it in domicilios)


# ---------------------------------------------------------------------------
# Cluster: "Alicia Carina Castro" vs "CASTRO ALICIA CARINA"
# ---------------------------------------------------------------------------

def test_get_surnames_cubre_apellido_primero_o_ultimo() -> None:
    # Variantes naturales y judiciales del mismo nombre.
    natural = tokenize_name(normalize_mention("Alicia Carina Castro"))
    judicial = tokenize_name(normalize_mention("CASTRO ALICIA CARINA"))
    sn = get_surnames(natural)
    sj = get_surnames(judicial)
    assert sn & sj, (
        f"Las variantes naturales y judiciales deben compartir al menos un "
        f"apellido candidato. natural={sn} judicial={sj}"
    )
