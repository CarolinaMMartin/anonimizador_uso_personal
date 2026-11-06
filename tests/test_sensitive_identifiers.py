import re

import pytest

from app.detection.identifiers import detect_identifiers, is_sensitive_identifier
from app.detection.regex_catalog import _match_surface


CASES = [
    ("Nro de seguimiento de denuncia: MPF-2026-00981234", "OTRO", "MPF-2026-00981234"),
    ("Número de seguimiento: 000019887766", "OTRO", "000019887766"),
    ("Código de seguimiento de la denuncia: 2a6f9e71-830a-4db7-bc12-d59be7a424d1", "OTRO", "2a6f9e71-830a-4db7-bc12-d59be7a424d1"),
    ("Código de seguimiento: AbCdEfGh", "OTRO", "AbCdEfGh"),
    ("Número de seguimiento de la denuncia: ABCD-EFGH-IJKL.", "OTRO", "ABCD-EFGH-IJKL"),
    ("Seguimiento | ABCD/EFGH/IJKL", "OTRO", "ABCD/EFGH/IJKL"),
    ("Nro seguimiento denuncia: D-99887766", "OTRO", "D-99887766"),
    ("Denuncia N° 123456/2026", "OTRO", "123456/2026"),
    ("ID de reclamo: REC-12345678", "OTRO", "REC-12345678"),
    ("Consulte https://denuncias.example/consulta?codigo=AbC123456&tipo=penal.", "OTRO", "https://denuncias.example/consulta?codigo=AbC123456&tipo=penal"),
    ("Enlace: www.example.test/expedientes/12345678", "OTRO", "www.example.test/expedientes/12345678"),
    ("DNI: 12345678", "DNI", "12345678"),
    ("D.N.I. Nro. 12.345.678", "DNI", "12.345.678"),
    ("Documento Nacional de Identidad Nº 12 345 678", "DNI", "12 345 678"),
    ("L.E. 1234567", "DNI", "1234567"),
    ("DNI:\n12345678", "DNI", "12345678"),
    ("DNI | 12.345.678", "DNI", "12.345.678"),
    ("DNI: 12 345\n678", "DNI", "12 345\n678"),
    ("DNI N° 12.34O.678", "DNI", "12.34O.678"),
    ("Se reclama la suma de $30.000. DNI: 12345678", "DNI", "12345678"),
    ("CUIT 20-12345678-9", "CUIT", "20-12345678-9"),
    ("Teléfono: 1155554444", "TELEFONO", "1155554444"),
    ("Celular 5491155554444", "TELEFONO", "5491155554444"),
    ("Tel. (011) 15-5555-4444", "TELEFONO", "(011) 15-5555-4444"),
    ("Teléfono particular: 4444-3333", "TELEFONO", "4444-3333"),
    ("Cel.: 223 555 1234", "TELEFONO", "223 555 1234"),
    ("WhatsApp: +54 9 11 5555 4444", "TELEFONO", "+54 9 11 5555 4444"),
    ("Contacto +54 9 351 555 4444", "TELEFONO", "+54 9 351 555 4444"),
    ("Teléfono: 4444-3333 int. 42", "TELEFONO", "4444-3333 int. 42"),
    ("Teléfono: 011/4444-3333", "TELEFONO", "011/4444-3333"),
    ("Teléfonos | 4444-3333", "TELEFONO", "4444-3333"),
    ("Celulares: 11 5555\n4444", "TELEFONO", "11 5555\n4444"),
    ("54 9 11 5555 4444", "TELEFONO", "54 9 11 5555 4444"),
    ("Teléfono: 4014-5851/6149", "TELEFONO", "4014-5851/6149"),
    ("teléfono 0205-123456", "TELEFONO", "0205-123456"),
    ("Patente AB 123 CD", "PATENTE", "AB 123 CD"),
    ("Dominio abc123", "PATENTE", "abc123"),
    ("Matrícula A123BCD", "PATENTE", "A123BCD"),
    ("Patente de la moto: 123ABC", "PATENTE", "123ABC"),
    ("Dominio B1234567", "PATENTE", "B1234567"),
    ("Patente AB.123.CD", "PATENTE", "AB.123.CD"),
    ("Expediente N° EX-2026-12345678-GCABA-MPF", "EXPEDIENTE", "EX-2026-12345678-GCABA-MPF"),
    ("Expte. Nro. CCF 1234/2026", "EXPEDIENTE", "CCF 1234/2026"),
    ("Expediente N 12345/2024. Juzgado Nacional en lo Criminal", "EXPEDIENTE", "12345/2024"),
    ("Causa: 123456 / 2026 - 1", "EXPEDIENTE", "123456 / 2026 - 1"),
    ("Legajo N° 987654", "EXPEDIENTE", "987654"),
    ("I.P.P. 01-00-123456-26/00", "EXPEDIENTE", "01-00-123456-26/00"),
    ("J-01-00056958-1/2026-0", "EXPEDIENTE", "J-01-00056958-1/2026-0"),
    ("Póliza de seguro Nro. AUTO-123456/09", "OTRO", "AUTO-123456/09"),
    ("PÓLIZA: 00412345678", "OTRO", "00412345678"),
    ("N° de chasis: 9BWZZZ377VT004251", "OTRO", "9BWZZZ377VT004251"),
    ("Identificado por 9BWZZZ377VT004251.", "OTRO", "9BWZZZ377VT004251"),
    ("Motor N° D4D-1234567", "OTRO", "D4D-1234567"),
    ("Número de bastidor: VF1AB123456789012", "OTRO", "VF1AB123456789012"),
    ("Pasaporte colombiano AB123456", "OTRO", "AB123456"),
    ("Pasaporte peruano P1234567", "OTRO", "P1234567"),
    ("Cédula de identidad colombiana CC-12345678", "OTRO", "CC-12345678"),
    ("CBU: 2850590940090418135201", "OTRO", "2850590940090418135201"),
    ("Cuenta bancaria N° 1234-567890/1", "OTRO", "1234-567890/1"),
]


@pytest.mark.parametrize("text,cat,value", CASES)
def test_complete_identifier_and_shared_validation(text, cat, value):
    items = detect_identifiers(text)
    found = [item for item in items if item.cat == cat and item.original == value]
    assert found, [(item.cat, item.original) for item in items]
    for item in found:
        assert text[item.start:item.end] == item.original
        assert is_sensitive_identifier(cat, item.original, text, item.start)


@pytest.mark.parametrize("text", [
    "La denuncia presentada describe los hechos.",
    "Denuncia 3 hechos distintos.",
    "El expediente fue remitido al juzgado.",
    "La póliza está vigente.",
    "El motor fue reparado.",
    "Documento recibido en la mesa de entradas.",
    "Código de seguimiento: pendiente.",
    "Ley 471 y Art 123 del código.",
    "LEY471 ART123",
    "La suma de $12.345.678 deberá abonarse.",
    "Monto: 12.345.678 pesos.",
    "En el año 2026 se registraron 1234 denuncias.",
])
def test_prose_money_and_legal_citations_are_not_identifiers(text):
    assert detect_identifiers(text) == []


@pytest.mark.parametrize("text,values", [
    ("Teléfono 4444-3333 / 5555-2222", ["4444-3333", "5555-2222"]),
    ("Celular: 1155554444, 1166667777", ["1155554444", "1166667777"]),
    ("Teléfono 4444-3333 5555-2222", ["4444-3333", "5555-2222"]),
    ("Teléfono 1155554444 1166667777", ["1155554444", "1166667777"]),
    ("DNI: 12 345 678, teléfonos: 4444-3333 y 5555-2222.", ["4444-3333", "5555-2222"]),
])
def test_multiple_phone_numbers_are_separate_complete_fields(text, values):
    phones = [item.original for item in detect_identifiers(text) if item.cat == "TELEFONO"]
    assert sorted(phones) == sorted(values)


@pytest.mark.parametrize("text,cat,value", CASES)
def test_identifier_survives_full_pipeline(monkeypatch, text, cat, value):
    from app.detection import pipeline

    monkeypatch.setattr(pipeline, "ENABLE_SPACY", False)
    monkeypatch.setattr(pipeline, "ENABLE_PRESIDIO", False)
    mentions = pipeline.run_detection(text)
    start = text.index(value)
    assert any(m.cat == cat and m.start <= start and m.end >= start + len(value) for m in mentions), [
        (m.cat, m.surface) for m in mentions
    ]


@pytest.mark.parametrize("pattern,text", [(r"(\s+ABC123\s+)", "  ABC123  "), (r"\s+ABC123\s+", "  ABC123  ")])
def test_catalog_surface_and_offsets_remain_identical(pattern, text):
    surface, start, end = _match_surface(re.search(pattern, text))
    assert surface == "ABC123"
    assert text[start:end] == surface


@pytest.mark.parametrize("prefix,value", [
    ("Motor N° ", "ABC123456"),
    ("Póliza ", "998877/01"),
    ("Denuncia Nro. ", "MPF-123456"),
    ("Expediente ", "EX-2026-998877-ABC"),
])
@pytest.mark.parametrize("tail", [". Juzgado Nacional", ".\nJuzgado Nacional", "; DNI: 12345678", ", Teléfono: 1155554444"])
def test_identifier_stops_before_sentence_or_next_field(prefix, value, tail):
    text = prefix + value + tail
    items = detect_identifiers(text)
    matching = [item for item in items if item.start == len(prefix)]
    assert matching
    assert all(item.end <= len(prefix) + len(value) for item in matching)
    assert any(item.original == value for item in matching)


@pytest.mark.parametrize("label,seed,aliases,cat", [
    ("DNI", "30.456.789", ["30456789", "30 456 789"], "DNI"),
    ("CUIT", "20-12345678-9", ["20123456789", "20 12345678 9"], "CUIT"),
    ("Teléfono", "11 5555 4444", ["1155554444", "11-5555-4444"], "TELEFONO"),
    ("Seguimiento", "ABCD-EFGH", ["ABCD-EFGH", "abcdefgh"], "OTRO"),
    ("Póliza", "POL-12345678", ["POL-12345678", "pol12345678"], "OTRO"),
    ("Motor", "D4D-1234567", ["D4D-1234567", "d4d1234567"], "OTRO"),
    ("Expediente", "12345/2026", ["12345/2026", "123452026"], "EXPEDIENTE"),
])
def test_labeled_identifiers_propagate_to_distant_references(monkeypatch, label, seed, aliases, cat):
    from app.detection import pipeline

    monkeypatch.setattr(pipeline, "ENABLE_SPACY", False)
    monkeypatch.setattr(pipeline, "ENABLE_PRESIDIO", False)
    text = f"{label}: {seed}. " + "Se agregó la documentación. " * 30
    for alias in aliases:
        start = len(text)
        text += alias + ". Se verificó el dato. "
        mentions = pipeline.run_detection(text)
        assert any(m.cat == cat and m.start <= start and m.end >= start + len(alias) for m in mentions), [
            (m.cat, m.surface) for m in mentions
        ]


@pytest.mark.parametrize("seed,tail", [
    ("DNI 12345678", "A12345678B 123456789 912345678 XY-12345678-ZZ"),
    ("Seguimiento: ABCD-EFGH", "QABCD-EFGH ABCD-EFGHZ QQ-ABCD-EFGH-ZZ ABCD-EFGH/2026"),
    ("Motor: D4D-1234567", "D4D-12345678 A-D4D-1234567 D4D-1234567-ZZ"),
])
def test_identifier_aliases_do_not_match_inside_other_codes(seed, tail):
    text = seed + ". " + tail
    assert not [item for item in detect_identifiers(text) if item.source_layer == "structured_alias"]


def test_short_field_values_are_not_propagated():
    text = "Expediente 12/26. En el artículo 12/26 se establecen las condiciones."
    assert not [item for item in detect_identifiers(text) if item.source_layer == "structured_alias"]


def test_unlabeled_matches_do_not_become_alias_seeds():
    text = "Se registró 30.456.789. Luego se indicó 30456789."
    assert not [item for item in detect_identifiers(text) if item.source_layer == "structured_alias"]


def test_dni_stops_before_telephone_label():
    text = "DNI 29.882.104. Tel +54 11 5555-4444"
    assert [item.original for item in detect_identifiers(text) if item.cat == "DNI"] == ["29.882.104"]


def test_alias_shared_by_two_categories_stays_sensitive(monkeypatch):
    from app.detection import pipeline

    monkeypatch.setattr(pipeline, "ENABLE_SPACY", False)
    monkeypatch.setattr(pipeline, "ENABLE_PRESIDIO", False)
    text = "DNI: 12345678. Teléfono: 12345678. Se comprobó el número 12345678."
    aliases = [item for item in detect_identifiers(text) if item.source_layer == "structured_alias"]
    assert [(item.cat, item.original) for item in aliases] == [("OTRO", "12345678")]
    for cat, label in [("DNI", "DNI: "), ("TELEFONO", "Teléfono: ")]:
        mentions = pipeline.run_detection(text, enabled_categories=[cat])
        start = text.index(label) + len(label)
        assert any(m.cat == cat and m.start == start and m.surface == "12345678" for m in mentions)
        assert all(m.cat == cat for m in mentions)


def test_dni_and_phone_remain_separate_with_real_nlp(monkeypatch):
    from app.detection import pipeline
    from app.detection.presidio_layer import detect_presidio
    from app.detection.spacy_layer import detect_spacy

    text = "DNI 29.882.104. Tel +54 9 11 5931-7720."
    detect_presidio(text)
    detect_spacy(text)
    monkeypatch.setattr(pipeline, "ENABLE_PRESIDIO", True)
    monkeypatch.setattr(pipeline, "ENABLE_SPACY", True)
    mentions = pipeline.run_detection(text)
    assert [(m.cat, m.surface) for m in mentions] == [
        ("DNI", "29.882.104"), ("TELEFONO", "+54 9 11 5931-7720")
    ]


@pytest.mark.parametrize("cat,surface", [
    ("DNI", "29.882.104. Tel"),
    ("DNI", "Documento 29.882.104"),
    ("TELEFONO", "+54 11 5555 4444 informó"),
    ("TELEFONO", "TEL 11 5555 4444"),
])
def test_identifier_validation_rejects_words_from_neighboring_fields(cat, surface):
    from app.detection.filters import is_valid_detection

    assert not is_valid_detection(cat, surface)


def test_many_distinct_identifiers_keep_every_repeated_reference():
    codes = [f"TRACK-{i:08d}-XYZ" for i in range(1000)]
    text = "\n".join("Seguimiento: " + code + "." for code in codes)
    text += "\n" + "\n".join("Se verificó " + code + "." for code in codes for _ in range(2))
    items = detect_identifiers(text)
    assert len(items) == 3000
    assert sum(item.source_layer == "structured_alias" for item in items) == 2000
    assert {item.original for item in items} == set(codes)
