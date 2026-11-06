"""Cobertura y límites de domicilios, organismos y empresas."""
import pytest

from app.anonymize.apply import anonymize_text
from app.anonymize.placeholders import build_detections_from_mentions
from app.detection import pipeline
from app.detection.addresses import address_spans, is_address
from app.detection.organizations import company_alias_spans, company_spans, is_organism_name, organism_spans


@pytest.fixture(autouse=True)
def deterministic_layers(monkeypatch):
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', False)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', False)


@pytest.mark.parametrize('address', [
    'PASEO COLON 1333 4 A',
    'Corrientes 1234 3 B',
    'Campana 39',
    'Av. Rivadavia 5678, piso 4, depto A',
    'Avenida del Libertador 2345, 7° B',
    'Pasaje Tres Sargentos 321, planta baja A',
    'calle San Martín 456, torre 2, piso 4 A',
    'Calle 12 345, manzana 3, lote 4',
    '25 de Mayo 123, 4° A',
    '9 de Julio 450, piso 2, oficina 12',
    'Paseo Colón\n1333\n4 A',
    'Diagonal Norte 1234, departamento 6, CABA',
    'Bv. San Juan 77, piso 3, dpto B, Córdoba',
    'Río de la Plata 124, piso 3 A',
    'Av. Juan B. Justo 1234, 4º "A"',
    'Ruta Provincial 36 km 42,5',
    'PASEO COLON 1333 4',
    'Corrientes 1234 4ºA',
    'Av. Rivadavia 5678 3B',
    'San-Martín 456A, piso 4, dpto B',
    'calle 14 N° 344 entre 45 y 46, La Plata',
    'Barrio Los Robles, Manzana 7, Lote 3, Casa 2',
    'Av. Juan B. Justo 1234, 4ºA, CABA',
    'Belgrano 1600, piso cuarto, departamento A',
    'Av. La Plata 432, sexto piso, dpto 12, Villa Madero',
])
def test_complete_address_grammar(address):
    assert any(value == address for _, _, value in address_spans(address))
    assert is_address(address)


@pytest.mark.parametrize('address', [
    'PASEO COLON 1333 4 A',
    'Corrientes 1234 3 B',
    'Campana 39',
    'Av. Rivadavia 5678, piso 4, depto A',
    '25 de Mayo 123, 4° A',
    'Paseo Colón\n1333\n4 A',
    'calle San Martín 456, torre 2, piso 4 A',
])
def test_address_is_replaced_as_one_entity(address):
    text = f'Se presentó en {address}; luego declaró.'
    mentions = pipeline.run_detection(text)
    addresses = [m for m in mentions if m.cat == 'DOMICILIO']
    assert [m.surface for m in addresses] == [address]
    assert all(text[m.start:m.end] == m.surface for m in mentions)
    result = anonymize_text(text, build_detections_from_mentions(mentions, 'cat'))
    assert result == 'Se presentó en [DOMICILIO_1]; luego declaró.'


def test_lowercase_address_after_explicit_label():
    text = 'Domicilio real: san martín 456 3 B; teléfono: 11 4567 8901.'
    mentions = pipeline.run_detection(text, ['DOMICILIO'])
    assert [m.surface for m in mentions] == ['san martín 456 3 B']


def test_address_context_survives_extraction_whitespace_and_quotes():
    text = 'Domicilio:' + ('\n ' * 100) + '"san martín 456 3 B".'
    mentions = pipeline.run_detection(text, ['DOMICILIO'])
    assert [m.surface for m in mentions] == ['san martín 456 3 B']


@pytest.mark.parametrize('floor', ['1er', '2do', '3ro', '4to', '5to', '7mo', '8vo', 'noveno'])
def test_ordinal_floors_keep_units_and_localities(floor):
    address = f'san martín 567, {floor} piso, departamento 10, Villa Madero'
    mentions = pipeline.run_detection('Dirección: ' + address + '.', ['DOMICILIO'])
    assert [m.surface for m in mentions] == [address]


@pytest.mark.parametrize('text', [
    'Ley 471. Artículo 123. Decreto 234.',
    'Ministerio Público Fiscal de la CABA',
    'El Departamento Ejecutivo dictó la resolución.',
    'La Cámara dictaminó a fojas 215.',
    'DNI 20123456. Teléfono 1145678901.',
    'El total fue 1234 pesos.',
    'Piso que no se encuentra habilitado.',
    'Juan Pérez 30 años.',
    'D.N.I. Nro. 12.345.678',
    'Documento Nacional de Identidad Nº 12 345 678',
    'Patente AB 123 CD',
    'dominio ABC 123',
    'Expte. N 12345/2024. Juzgado Nacional',
    'Referencia B 12345/2024',
    'Código Z 3456',
    'Expediente SAC 12345-2024',
])
def test_non_postal_numbers_do_not_become_addresses(text):
    assert address_spans(text) == []


def test_address_does_not_cross_a_sentence_or_join_two_addresses():
    text = 'Juan Pérez. Corrientes 1234, piso 4 A; Campana 39.'
    assert [value for _, _, value in address_spans(text)] == [
        'Corrientes 1234, piso 4 A', 'Campana 39']


@pytest.mark.parametrize('address', [
    'calle 14 N° 344 entre 45 y 46',
    'Corrientes 1234, piso cuarto',
    'calle Mitre 123 entre Belgrano y Rivadavia',
])
def test_address_preserves_following_time_narrative(address):
    text = address + ' a las 15 horas.'
    assert [value for _, _, value in address_spans(text)] == [address]


@pytest.mark.parametrize('institution', [
    'Ministerio Publico Fiscal de la Caba',
    'MINISTERIO PÚBLICO FISCAL DE LA CABA',
    'Ministerio Público Fiscal de la Ciudad Autónoma de Buenos Aires',
    'Ministerio\nPúblico Fiscal\nde la CABA',
    'Ministerio Público Fiscal de la Provincia de Santa Fe',
    'Juzgado Nacional en lo Criminal y Correccional nro. 12',
    'Cámara Nacional de Apelaciones en lo Comercial',
    'MPF CABA',
])
def test_full_institution_has_one_span(institution):
    assert is_organism_name(institution)
    assert [value for _, _, value in organism_spans(institution)] == [institution]
    mentions = pipeline.run_detection(institution)
    assert [(m.cat, m.surface) for m in mentions] == [('ORGANISMO', institution)]


@pytest.mark.parametrize('text, expected', [
    ('La empresa Acme Servicios informó el cambio.', 'Acme Servicios'),
    ('La firma "transporte del sur" presentó la documentación.', 'transporte del sur'),
    ('Razón social: transportes del sur s.r.l.; domicilio legal', 'transportes del sur s.r.l.'),
    ('Aseguradora Río de la Plata, CUIT 30-12345678-9.', 'Río de la Plata'),
    ('El comercio denominado "El Buen Camino" cerró.', 'El Buen Camino'),
    ('Empresa: Nueva Industria S.A.S.', 'Nueva Industria S.A.S.'),
    ('La empresa Nuevos Servicios S.A.U. manifestó su posición.', 'Nuevos Servicios S.A.U.'),
])
def test_company_context_and_complete_legal_suffixes(text, expected):
    assert any(value == expected for _, _, value in company_spans(text))
    mentions = pipeline.run_detection(text, ['EMPRESA'])
    assert [m.surface for m in mentions] == [expected]


def test_company_context_does_not_consume_next_sentence():
    text = 'Empresa Acme. Luego Compareció Juan Pérez.'
    assert [value for _, _, value in company_spans(text)] == ['Acme']


def test_company_context_survives_extraction_whitespace():
    text = 'Empresa:' + ('\n ' * 100) + 'Acme Servicios; luego compareció.'
    assert [m.surface for m in pipeline.run_detection(text, ['EMPRESA'])] == ['Acme Servicios']


@pytest.mark.parametrize('declaration, reference', [
    ('Transportes del Sur S.R.L.', 'TRANSPORTES DEL SUR'),
    ('empresa Acme Servicios', 'Acme\nServicios'),
    ('firma "transporte del sur"', 'Transporte del Sur'),
])
def test_company_base_is_learned_with_exact_boundaries(declaration, reference):
    text = f'{declaration}; luego {reference} presentó el escrito.'
    seeds = company_spans(text)
    assert [value for _, _, value in company_alias_spans(text, seeds)] == [reference]
    mentions = pipeline.run_detection(text, ['EMPRESA'])
    assert any(m.surface == reference for m in mentions)


def test_ambiguous_company_bases_are_not_propagated():
    text = 'Armada SA. Juan Perez SA. Armada y Juan Perez comparecieron.'
    assert company_alias_spans(text, company_spans(text)) == []
    mentions = pipeline.run_detection(text, ['PERSONA'])
    assert any(m.surface == 'Juan Perez' for m in mentions)


def test_company_alias_does_not_match_inside_a_longer_word():
    text = 'Transportes del Sur SA. Transportes del Sureste.'
    assert company_alias_spans(text, company_spans(text)) == []
