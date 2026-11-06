import pytest

from app.detection.identifiers import detect_identifiers


@pytest.mark.parametrize('text,value', [
    ('CAE N°: 74123456789012', '74123456789012'),
    ('CAI: 74123456789012', '74123456789012'),
    ('CAEA Nro. 74123456789012', '74123456789012'),
    ('Código de autorización electrónica: 74123456789012', '74123456789012'),
    ('Código de autorización de impresión: 74123456789012', '74123456789012'),
    ('Comp. Nro: 00000427', '00000427'),
    ('Comprobante N° 00003-00000427', '00003-00000427'),
    ('Factura electrónica número 00003 00000427', '00003 00000427'),
    ('Ingresos Brutos: 901-2345678-9', '901-2345678-9'),
    ('IIBB: 90123456789', '90123456789'),
])
def test_fiscal_identifiers_are_bounded_and_repeated_consistently(text, value):
    full_text = f'{text}. Fecha de emisión: 05/10/2026. Repite: {value}.'
    matches = [item for item in detect_identifiers(full_text) if item.cat == 'OTRO']
    assert [item.original for item in matches] == [value, value]
    assert all(full_text[item.start:item.end] == value for item in matches)


@pytest.mark.parametrize('text', [
    'Fecha de Vto. de CAE: 15/10/2026',
    'Factura emitida el 05/10/2026.',
    'Ingresos Brutos: 00000000000',
    'CAE: 00000000000000',
    'Factura Nro. pendiente.',
    'Factura correspondiente a septiembre de 2026.',
])
def test_fiscal_labels_do_not_consume_dates_or_empty_values(text):
    assert not [item for item in detect_identifiers(text) if item.cat == 'OTRO']
