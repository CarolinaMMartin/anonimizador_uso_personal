import pytest

from app.anonymize.apply import anonymize_text
from app.anonymize.placeholders import build_detections_from_mentions
from app.detection import pipeline
from app.detection.filters import is_valid_detection
from app.detection.identifiers import detect_identifiers
from app.detection.organizations import company_alias_spans, company_spans
from app.detection.regex_ar import RawItem


@pytest.mark.parametrize('nlp', [False, True])
def test_invoice_party_names_keep_their_identity_and_field_labels(monkeypatch, nlp):
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', nlp)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', nlp)
    name = 'GOMEZ ANA ZELLA'
    institution = 'MINISTERIO PUBLICO DE LA CIUDAD AUTONOMA DE\n\nBUENOS AIRES'
    text = (
        name + '\n\n'
        'Razón Social: ' + name + ' Fecha de Emisión: 03/04/2026\n'
        'Apellido y Nombre / Razón Social: ' + institution + '\n'
        'COD. 011\nCUIT: 00000000000'
    )
    mentions = pipeline.run_detection(text)
    assert [(item.cat, item.surface) for item in mentions] == [
        ('PERSONA', name), ('PERSONA', name), ('ORGANISMO', institution),
    ]
    detections = build_detections_from_mentions(mentions, 'cat')
    people = [item for item in detections if item.cat == 'PERSONA']
    assert len(people) == 1 and len(people[0].positions) == 2
    result = anonymize_text(text, detections)
    assert result.count(people[0].placeholder) == 2
    assert 'Fecha de Emisión: 03/04/2026' in result
    assert 'Apellido y Nombre / Razón Social:' in result
    assert 'COD. 011' in result
    assert all(text[item.start:item.end] == item.surface for item in mentions)


@pytest.mark.parametrize('name', [
    'GOMEZ ANA ZELLA', 'ANA ZELLA GOMEZ', 'María de los Ángeles Gómez',
    'ZORVIK ANA MARIA', 'JUAN ANA ZELLA',
])
@pytest.mark.parametrize('field', [
    'Fecha de Emisión', 'Fecha de Vencimiento', 'Punto de Venta',
    'Condición frente al IVA', 'Inicio de Actividades',
])
def test_name_field_boundaries_are_shared_by_all_deterministic_layers(monkeypatch, name, field):
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', False)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', False)
    text = f'Apellido y Nombre / Razón Social: {name} {field}: 03/04/2026'
    mentions = pipeline.run_detection(text, ['PERSONA', 'EMPRESA'])
    assert [(item.cat, item.surface) for item in mentions] == [('PERSONA', name)]
    assert company_spans(text) == []


@pytest.mark.parametrize('company', ['Nueva Industria S.A.S.', 'Gomez Ana Zella S.R.L.', 'Acme Servicios'])
def test_actual_businesses_keep_their_category_and_field_boundaries(monkeypatch, company):
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', False)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', False)
    text = f'Razón Social: {company} Fecha de Emisión: 03/04/2026'
    assert [(item.cat, item.surface) for item in pipeline.run_detection(text)] == [('EMPRESA', company)]


@pytest.mark.parametrize('kind', ['Hotel', 'Comercio', 'Aseguradora'])
def test_explicit_business_types_keep_person_shaped_trade_names(monkeypatch, kind):
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', False)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', False)
    text = f'{kind} Juan Carlos, domicilio declarado.'
    assert [(item.cat, item.surface) for item in pipeline.run_detection(text)] == [('EMPRESA', 'Juan Carlos')]


def test_person_shaped_company_base_is_not_propagated_as_a_business():
    text = 'Gomez Ana Zella S.R.L.; Gomez Ana Zella declaró.'
    assert company_alias_spans(text, company_spans(text)) == []


@pytest.mark.parametrize('value', ['COD. 011', 'COD 011', 'NUM. 123', 'NRO. 456', 'TEL 123'])
def test_administrative_codes_are_not_license_plates(value):
    assert not [item for item in detect_identifiers(value) if item.cat == 'PATENTE']
    assert not is_valid_detection('PATENTE', value, value, 0)


@pytest.mark.parametrize('text', ['CUIT: 00000000000', 'CUIL 00-00000000-0', '00000000000'])
def test_zero_tax_identifiers_are_not_reintroduced_by_nlp_layers(monkeypatch, text):
    from app.detection import presidio_layer, spacy_layer

    value = text.split()[-1]
    start = text.index(value)
    candidates = [RawItem('CUIT', value, start, start + len(value), 'presidio')]
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', True)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', True)
    monkeypatch.setattr(presidio_layer, 'detect_presidio', lambda *args, **kwargs: candidates)
    monkeypatch.setattr(spacy_layer, 'detect_spacy', lambda *args, **kwargs: [])
    assert pipeline.run_detection(text) == []
