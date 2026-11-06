import json
import unicodedata

import pytest

from app.detection import dictionaries, pipeline
from app.detection.regex_ar import detect_regex_ar
from app.detection import regex_catalog


@pytest.fixture(autouse=True)
def deterministic_detection(monkeypatch):
    monkeypatch.setattr(pipeline, "ENABLE_SPACY", False)
    monkeypatch.setattr(pipeline, "ENABLE_PRESIDIO", False)


@pytest.mark.parametrize("name", [
    "Juan Carlos Mendoza",
    "María de los Ángeles Fernández de la Vega",
    "JUAN CARLOS PÉREZ GONZÁLEZ",
    "juan carlos pérez gonzález",
    "Juan CARLOS pérez González",
    "González Pérez, María José",
    "Juan G. Pérez",
    "María O’Kelan",
    "José Ros-Vaak",
    "Juan de la Cruz",
    "Juan del Valle",
    "Juan Carlos\nPérez Gómez",
    "María\nJosé González",
    "Juan van der Berg",
    unicodedata.normalize("NFD", "María Pérez"),
])
def test_complete_names_preserve_original_offsets(name):
    text = f"{name} declaró ante el tribunal."
    mentions = pipeline.run_detection(text, ["PERSONA"])
    assert [item.surface for item in mentions] == [name]
    assert text[mentions[0].start:mentions[0].end] == name


@pytest.mark.parametrize("prefix, name", [
    ("Nombre y apellido: ", "tashi dorji"),
    ("Apellidos y nombres:\n", "qorven zella"),
    ("El imputado ", "tashi dorji"),
    ("la víctima: ", "Tashi Dorji"),
    ("Dra. ", "Zella Qorven"),
    ("Sr.\n\n", "Donati"),
    ("Nombre y apellido | ", "Irina Zorvik"),
    ("Nombre | ", "irina zorvik"),
    ("Nombre completo: ", "tashi dorji"),
    ("Nombre y apellido:" + " " * 200, "tashi dorji"),
])
def test_explicit_context_supports_names_outside_catalog(prefix, name):
    text = f"{prefix}{name} declaró ante el tribunal."
    mentions = pipeline.run_detection(text, ["PERSONA"])
    assert [item.surface for item in mentions] == [name]


@pytest.mark.parametrize("text, expected", [
    ("Marcos Benítez y Camila Ferreyra declararon.", ["Marcos Benítez", "Camila Ferreyra"]),
    ("Juan Pérez, María Gómez declararon.", ["Juan Pérez", "María Gómez"]),
    ("El señor Donati adquirió un vehículo.", ["Donati"]),
    ("El señor Donati suscribió el contrato.", ["Donati"]),
    ("Firman Juan Pérez y Roberto Nolasco.", ["Juan Pérez", "Roberto Nolasco"]),
])
def test_separate_people_and_narrative_boundaries(text, expected):
    assert [item.surface for item in pipeline.run_detection(text, ["PERSONA"])] == expected


@pytest.mark.parametrize("text", [
    "La denunciante se presentó ante el tribunal.", "Nombre: no consta",
    "Víctima del hecho desconocida", "Señor Director de la Escuela",
])
def test_person_fields_do_not_turn_prose_or_roles_into_names(text):
    assert pipeline.run_detection(text, ["PERSONA"]) == []


def test_detection_uses_current_catalog_without_regenerating_regex(monkeypatch):
    monkeypatch.setattr(dictionaries, "_nombres", {"zella"})
    monkeypatch.setattr(dictionaries, "_apellidos", {"qorven"})
    monkeypatch.setattr(regex_catalog, "load_catalog_patterns", lambda: ())
    matches = detect_regex_ar("zella qorven declaró.")
    assert any(item.cat == "PERSONA" and item.original == "zella qorven" for item in matches)


def test_compound_catalog_entries_supply_runtime_anchors(monkeypatch):
    monkeypatch.setattr(dictionaries, "_nombres", {"zella norven"})
    monkeypatch.setattr(dictionaries, "_apellidos", {"de la qorven"})
    monkeypatch.setattr(regex_catalog, "load_catalog_patterns", lambda: ())
    name = "zella norven de la qorven"
    assert [item.surface for item in pipeline.run_detection(name, ["PERSONA"])] == [name]


@pytest.mark.parametrize("separator", ["\n", "\n\n", "\r\n\r\n"])
def test_lines_with_distinct_people_are_not_joined(separator):
    text = f"Juan Pérez{separator}María Gómez"
    assert [item.surface for item in pipeline.run_detection(text, ["PERSONA"])] == ["Juan Pérez", "María Gómez"]


def write_catalog(base, name, values, encoding="utf-8"):
    folder = base / "dictionaries"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(json.dumps(values, ensure_ascii=False), encoding=encoding)


def test_portable_merges_embedded_and_external_catalogs(tmp_path, monkeypatch):
    bundle, external = tmp_path / "_internal", tmp_path / "portable"
    write_catalog(bundle, "nombres.json", ["Juan", "María"])
    write_catalog(external, "nombres.json", ["Zella", "MARIA"], encoding="utf-8-sig")
    monkeypatch.setattr(dictionaries, "RESOURCE_DATA_DIR", bundle)
    monkeypatch.setattr(dictionaries, "DATA_DIR", external)
    assert dictionaries._load_json("nombres.json") == {"juan", "maria", "zella"}
    assert len(dictionaries.catalog_paths("nombres.json")) == 2


@pytest.mark.parametrize("content", [None, "[]", "{}", '["Juan", null]', "not json"])
def test_missing_or_broken_catalog_fails_without_caching_empty_set(tmp_path, monkeypatch, content):
    monkeypatch.setattr(dictionaries, "RESOURCE_DATA_DIR", tmp_path)
    monkeypatch.setattr(dictionaries, "DATA_DIR", tmp_path)
    monkeypatch.setattr(dictionaries, "_nombres", None)
    folder = tmp_path / "dictionaries"
    folder.mkdir()
    if content is not None:
        (folder / "nombres.json").write_text(content, encoding="utf-8")
    with pytest.raises(dictionaries.CatalogLoadError):
        dictionaries.get_nombres()
    assert dictionaries._nombres is None
    write_catalog(tmp_path, "nombres.json", ["Zella"])
    assert dictionaries.get_nombres() == {"zella"}
