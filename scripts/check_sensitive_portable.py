"""Verify sensitive fields through the running portable's HTTP API."""
import argparse
import hashlib
import io
import json
import urllib.request
import uuid
from html.parser import HTMLParser
from pathlib import Path
from xml.sax.saxutils import escape

import pdfplumber
from docx import Document
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

import portable_smoke as api
from package_release import app_version

ROOT = Path(__file__).resolve().parents[1]
PARAGRAPHS = [
    'Ministerio Publico Fiscal de la Caba',
    'Denunciante: María del Carmen Fernández de la Vega.',
    'Razón Social: María del Carmen Fernández de la Vega Fecha de Emisión: 05/10/2026.',
    'D.N.I. Nro.: 30.456.789; indemnización solicitada: $ 10.000.',
    'Teléfono: 4301-5678. Celular: 1156789012.',
    'Domicilio: PASEO COLON 1333 4 A.',
    'Dirección: Tucumán 2345, piso 6, departamento B.',
    'Empresa: Transportes del Sur S.R.L.',
    'Expediente: EX-2026-98765432-GCABA-DG; patente AB 321 CD.',
    'Chasis: 8AFZZZ54Z6J123456; motor: QX-7890123.',
    'Póliza de seguro Nro. 0042-87654321.',
    'Nro de seguimiento de denuncias: MPF-2026-887766.',
    'Consulta: https://denuncias.example/consulta?seguimiento=MPF-2026-887766.',
    'Comprobante Nro. 00003-00000427. CAE N°: 74123456789012.',
    'Se incorpora la documentación presentada y se deja constancia de su recepción. ' * 4,
    'Se verificó nuevamente 30456789 y MPF-2026-887766. Se notificó a Transportes del Sur.',
    'Se deja constancia de lo informado. Ley 471, artículo 12.',
]
SECRETS = [
    'María', 'Carmen', 'Fernández', 'Vega', '30.456.789', '30456789',
    '4301-5678', '1156789012', 'PASEO COLON', '1333', 'Tucumán', '2345',
    'Transportes del Sur', 'EX-2026-98765432-GCABA-DG', 'AB 321 CD',
    '8AFZZZ54Z6J123456', 'QX-7890123', '0042-87654321',
    'MPF-2026-887766', 'denuncias.example', '27.654.321', '1145678901',
    '00003-00000427', '74123456789012',
]
TABLE_ROWS = [('DNI', '27.654.321'), ('Celular', '1145678901')]


class Categories(HTMLParser):
    def __init__(self):
        super().__init__()
        self.checked = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input' and 'data-cat' in attrs:
            self.checked[attrs['data-cat']] = 'checked' in attrs


def make_input(extension):
    output = io.BytesIO()
    if extension == 'docx':
        document = Document()
        document.sections[0].header.paragraphs[0].text = PARAGRAPHS[0]
        for text in PARAGRAPHS[1:]:
            document.add_paragraph(text)
        table = document.add_table(rows=0, cols=2)
        for label, value in TABLE_ROWS:
            cells = table.add_row().cells
            cells[0].text, cells[1].text = label, value
        document.save(output)
    else:
        style = getSampleStyleSheet()['Normal']
        story = []
        for text in PARAGRAPHS + [f'{label}: {value}' for label, value in TABLE_ROWS]:
            story.extend([Paragraph(escape(text), style), Spacer(1, 6)])
        SimpleDocTemplate(output).build(story)
    return output.getvalue()


def extract_output(extension, data):
    if extension == 'docx':
        document = Document(io.BytesIO(data))
        return '\n'.join(p.text for p in document.paragraphs)
    with pdfplumber.open(io.BytesIO(data)) as document:
        return '\n'.join(page.extract_text() or '' for page in document.pages)


def check_document(extension, output_dir):
    data = make_input(extension)
    (output_dir / f'entrada.{extension}').write_bytes(data)
    boundary = 'sensitive-' + uuid.uuid4().hex
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="prueba_sensible.{extension}"\r\n'
        'Content-Type: application/octet-stream\r\n\r\n'
    ).encode() + data + f'\r\n--{boundary}--\r\n'.encode()
    uploaded = json.loads(api.request('/api/upload', body, {
        'Content-Type': 'multipart/form-data; boundary=' + boundary,
    }))
    sid = uploaded['session_id']
    analysis = api.post('/api/analyze', {'session_id': sid, 'label_mode': 'cat'})
    original = json.loads(api.request(f'/api/preview?session_id={sid}'))['text']
    rows = analysis['detections']
    checks = {
        'institution_is_one_complete_entity': any(
            row['cat'] == 'ORGANISMO' and row['original'] == PARAGRAPHS[0]
            for row in rows
        ),
        'positions_match_extracted_text': all(
            original[p['start']:p['end']] == p['raw']
            for row in rows for p in row['positions']
        ),
        'full_address_including_unit': any(
            row['cat'] == 'DOMICILIO' and row['original'] == 'PASEO COLON 1333 4 A'
            for row in rows
        ),
    }
    payload = {'session_id': sid, 'use_confirmed_only': False}
    texts = {'preview': api.post('/api/export/preview', payload)['text']}
    for target in ('docx', 'pdf'):
        exported = api.request('/api/export/' + target, json.dumps(payload).encode(), {
            'Content-Type': 'application/json',
        })
        (output_dir / f'desde_{extension}.{target}').write_bytes(exported)
        texts[target] = extract_output(target, exported)
    for target, text in texts.items():
        checks[f'{target}_all_sensitive_fields_removed'] = not any(s in text for s in SECRETS)
        checks[f'{target}_legal_prose_preserved'] = all(
            phrase in text for phrase in ('Se deja constancia de lo informado.', 'Ley 471', '$ 10.000', 'Fecha de Emisión:')
        )
    return {'checks': checks, 'detections': rows, 'outputs': texts}


def check_manual_entity_correction(output_dir):
    names = ['RIVERA JULIETA CLARA', 'Julieta Clara Rivera']
    document = Document()
    document.add_paragraph(names[0])
    document.add_paragraph('Razón social: ' + names[1] + ' Fecha de Emisión: 05/10/2026.')
    stream = io.BytesIO()
    document.save(stream)
    boundary = 'review-' + uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            'filename="revision_ficticia.docx"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()
    body += stream.getvalue() + f'\r\n--{boundary}--\r\n'.encode()
    sid = json.loads(api.request('/api/upload', body, {
        'Content-Type': 'multipart/form-data; boundary=' + boundary,
    }))['session_id']
    original = json.loads(api.request(f'/api/preview?session_id={sid}'))['text']
    groups = []
    for name, category in zip(names, ['PERSONA', 'EMPRESA']):
        start = original.index(name)
        row = api.post('/api/manual-detection', {
            'session_id': sid, 'cat': category, 'original': name,
            'start': start, 'end': start + len(name),
        })['detection']
        groups.append(api.post(f'/api/clusters/create?session_id={sid}', {
            'detection_ids': [row['id']], 'cat': category,
        })['cluster'])
    target, source = groups
    confirmed = api.post(f'/api/clusters/{target["cluster_id"]}/confirm?session_id={sid}', {})
    placeholder = confirmed['cluster']['placeholder']
    url = f'/api/clusters/{source["cluster_id"]}?session_id={sid}'
    request = urllib.request.Request(api.BASE + url, data=json.dumps({'cat': 'PERSONA'}).encode(),
        headers={'Content-Type': 'application/json'}, method='PATCH')
    with api.OPENER.open(request, timeout=30) as response:
        recategorized = json.loads(response.read())
    merged = api.post(f'/api/clusters/{target["cluster_id"]}/absorb?session_id={sid}', {
        'source_cluster_id': source['cluster_id'],
    })
    checks = {
        'category_correction': recategorized['cluster']['cat'] == 'PERSONA',
        'single_person_identity': len(merged['clusters']) == 1 and all(
            row['cat'] == 'PERSONA' and row['placeholder'] == placeholder
            for row in merged['detections']
        ),
    }
    payload = {'session_id': sid, 'use_confirmed_only': False}
    for extension in ('docx', 'pdf'):
        raw = api.request('/api/export/' + extension, json.dumps(payload).encode(), {
            'Content-Type': 'application/json',
        })
        (output_dir / ('revision_manual.' + extension)).write_bytes(raw)
        text = extract_output(extension, raw)
        checks[extension + '_corrected_identity'] = (
            text.count(placeholder) == 2 and 'EMPRESA' not in text
            and not any(name in text for name in names)
            and 'Fecha de Emisión:' in text
        )
    return {'checks': checks}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8787)
    parser.add_argument('--package', type=Path, default=ROOT / 'dist/AnonimizadorJudicial-NLP')
    parser.add_argument('--result-name', default='portable_sensitive')
    args = parser.parse_args()
    if not args.result_name.replace('_', '').replace('-', '').isalnum():
        parser.error('result-name must contain only letters, digits, underscores or hyphens')
    api.BASE = f'http://127.0.0.1:{args.port}'
    output_dir = ROOT / 'build/validation' / args.result_name
    output_dir.mkdir(parents=True, exist_ok=True)
    health = json.loads(api.request('/health'))
    package = args.package.resolve()
    assert Path(health['frontend_dir']).resolve() == package / 'frontend', health
    assert health['app_version'] == app_version(), health
    result = {'health': health, 'package': str(package), 'port': args.port}
    categories = Categories()
    categories.feed(api.request('/').decode('utf-8'))
    result['checks'] = {
        'all_eleven_categories_enabled': len(categories.checked) == 11 and all(categories.checked.values()),
        'catalogs_loaded': all(v['available'] for v in health['nlp_layers']['dictionaries'].values()),
        'served_assets_match_sources': all(
            hashlib.sha256(api.request('/static/' + name)).digest()
            == hashlib.sha256((ROOT / 'frontend' / name).read_bytes()).digest()
            for name in (
                'app.js', 'styles.css',
                'assets/ialab/logo_blanco_navy.png',
                'assets/ialab/logo_azul.png',
                'assets/ialab/isotype_azul.png',
                'assets/fonts/Roboto.ttf',
                'assets/fonts/OFL.txt',
            )
        ),
    }
    for extension in ('docx', 'pdf'):
        result[extension] = check_document(extension, output_dir)
        result['checks'][extension + '_input_and_exports'] = all(result[extension]['checks'].values())
    result['manual_review'] = check_manual_entity_correction(output_dir)
    result['checks']['manual_category_and_merge'] = all(result['manual_review']['checks'].values())
    (output_dir / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['checks'], ensure_ascii=False))
    if not all(result['checks'].values()):
        raise AssertionError(f'Falló la verificación: {output_dir / "results.json"}')


if __name__ == '__main__':
    main()
