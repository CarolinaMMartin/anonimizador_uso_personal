"""Run the portable against a fictitious DOCX using only the standard library.

Starts one owned process; never stops existing instances. Results contain only
synthetic data. Startup is headless; existing application processes remain untouched.
"""
import io
import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8787'
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
TEXT = [
    'Dr. Juan Perez solicita que se rechace la demanda.',
    'JUAN PÉREZ presentó un escrito.',
    'MARÍA JOSÉ GONZÁLEZ declaró como testigo.',
    'PÉREZ, JUAN CARLOS compareció.',
    'Sr. PÉREZ manifestó su voluntad.',
    'PODER JUDICIAL DE LA NACIÓN',
    'JUZGADO NACIONAL EN LO CIVIL',
]
CATEGORY_TEXT = [
    'Cámara Nacional de Apelaciones en lo Comercial',
    'Sala B',
    'Firmado por: CARINA ZORVIK, JUEZ DE CÁMARA',
    'Firmado por: ESTEBAN NOLVIK ZELKIN, PROSECRETARIO DE CAMARA',
    'CARINA E. ZORVIK',
    'ESTEBAN NOLVIK ZELKIN',
    'PROSECRETARIO DE CÁMARA',
    'El señor Zorvik adquirió de Aurora SA un vehículo Fiat Toro.',
    'La Cámara dictaminó a fojas 215.',
    'Corresponde confirmar la responsabilidad de AQR Ahorro SA.',
    'Comercial\n\nSala B\n\nVI. AQR Ahorro SA se agravió.',
    'Aurora SA y AQR de Ahorro para fines determinados SA.',
    '"Zelkin, Andrea\n\nLaura c/ Fiat Auto SA s/ ordinario"',
    '"Quirna de Zorlen, Ethel B. c/ Universal Assistance SA"',
]


def request(path, data=None, headers=None):
    req = urllib.request.Request(BASE + path, data=data, headers=headers or {})
    with OPENER.open(req, timeout=90) as response:
        return response.read()


def post(path, payload):
    return json.loads(request(path, json.dumps(payload).encode(), {'Content-Type': 'application/json'}))


def fictitious_docx():
    contents = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    relations = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    document = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + ''.join('<w:p><w:r><w:t>' + escape(p) + '</w:t></w:r></w:p>' for p in TEXT) + '<w:sectPr/></w:body></w:document>'
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        archive.writestr('[Content_Types].xml', contents)
        archive.writestr('_rels/.rels', relations)
        archive.writestr('word/document.xml', document)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--use-existing', action='store_true', help='Use an existing server, only with a new fictitious session; never stop it.')
    parser.add_argument('--package', type=Path, default=ROOT / 'dist/AnonimizadorJudicial-NLP')
    parser.add_argument('--port', type=int, default=8787)
    parser.add_argument('--category-cases', action='store_true', help='Include general category and signature regressions.')
    parser.add_argument('--all-categories', action='store_true', help='Analyze with every category enabled.')
    args = parser.parse_args()
    if args.category_cases:
        TEXT.extend(CATEGORY_TEXT)
    global BASE
    BASE = f'http://127.0.0.1:{args.port}'
    package = args.package.resolve()
    existing = False
    try:
        request('/health')
    except (urllib.error.URLError, TimeoutError):
        pass
    else:
        if not args.use_existing:
            raise RuntimeError(f'Ya hay una instancia en {args.port}; usar --use-existing para probar una sesión ficticia independiente.')
        existing = True
    result_name = ('portable_categories_all' if args.all_categories else 'portable_categories_names') if args.category_cases else 'portable_smoke'
    results_dir = ROOT / 'build/validation'
    results_dir.mkdir(parents=True, exist_ok=True)
    log = results_dir / (result_name + '.log')
    result = {}
    with log.open('w', encoding='utf-8') as output:
        env = {**os.environ, 'ANON_PORT': str(args.port), 'ANON_NO_BROWSER': '1'}
        process = None if existing else subprocess.Popen([str(package / 'AnonimizadorJudicial-NLP.exe')], cwd=package, env=env,
                                   stdout=output, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            result['existing_instance'] = existing
            result['package'] = str(package)
            result['port'] = args.port
            print('Probando sesión independiente con documento ficticio...', flush=True)
            for _ in range(60):
                if process is not None and process.poll() is not None:
                    raise RuntimeError(f'El portable terminó con código {process.returncode}; ver {log.name}')
                try:
                    result['health'] = json.loads(request('/health'))
                    break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(0.5)
            else:
                raise TimeoutError('La instancia no inició en 30 segundos.')
            print('Motor iniciado. Analizando documento ficticio...', flush=True)
            schema = json.loads(request('/openapi.json'))
            result['paths'] = sorted(schema.get('paths', {}))
            result['schemas'] = schema.get('components', {}).get('schemas', {})
            boundary = 'smoke-' + uuid.uuid4().hex
            body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="prueba_ficticia.docx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n'.encode() + fictitious_docx() + f'\r\n--{boundary}--\r\n'.encode())
            upload = json.loads(request('/api/upload', body, {'Content-Type': 'multipart/form-data; boundary=' + boundary}))
            sid = upload['session_id']
            analysis = post('/api/analyze', {'session_id': sid, 'label_mode': 'cat',
                'enabled_categories': None if args.all_categories else ['PERSONA']})
            result['analysis'] = analysis
            result['preview'] = post('/api/export/preview', {'session_id': sid, 'use_confirmed_only': False})
            people = [d for d in analysis['detections'] if d['cat'] == 'PERSONA']
            noisy = [d['original'] for d in people if any(term in d['original'].casefold() for term in ('solicita', 'rechace', 'poder judicial', 'juzgado nacional'))]
            result['checks'] = {
                'no_sentence_as_person': not noisy,
                'uppercase_name_detected': any('JUAN PÉREZ' in p['raw']
                    for d in people for p in d['positions']),
                'accented_compound_name_detected': any('MARÍA JOSÉ GONZÁLEZ' in d['original'] for d in people),
                'uppercase_surname_context_detected': any('PÉREZ' in d['original'] and any(
                    p['start'] <= sum(len(t) + 1 for t in TEXT[:4]) + 4 < p['end']
                    for p in d['positions']) for d in people),
                'surname_first_fully_anonymized': 'PÉREZ,' not in result['preview']['text'],
            }
            result['noisy_surfaces'] = noisy
            if result['health'].get('app_version'):
                result['checks']['catalogs_loaded'] = all(v['available'] for v in result['health']['nlp_layers']['dictionaries'].values())
            if args.category_cases:
                preview = result['preview']['text']
                result['checks'].update({
                    'signatures_and_initial_variant_hidden': not any(word in preview for word in ('CARINA', 'ZORVIK', 'ESTEBAN', 'NOLVIK', 'ZELKIN')),
                    'unknown_surname_after_honorific_hidden': 'Zorvik' not in preview,
                    'multiline_and_rare_cited_names_hidden': not any(word in preview for word in ('Zelkin', 'Laura', 'Quirna', 'Zorlen', 'Ethel')),
                    'vehicle_is_preserved': 'Fiat Toro' in preview and not any(d['original'] == 'Fiat Toro' for d in people),
                    'institution_prose_is_preserved': 'La Cámara dictaminó a fojas 215.' in preview,
                    'company_prose_is_preserved': 'confirmar la responsabilidad de' in preview,
                })
                if args.all_categories:
                    companies = [d['original'] for d in analysis['detections'] if d['cat'] == 'EMPRESA']
                    result['checks']['company_names_are_bounded'] = all(not any(
                        word in name.lower() for word in ('responsabilidad', 'zorvik', 'sala b', 'comercial')) for name in companies)
                    result['checks']['full_institution_name_detected'] = any(d['original'] == CATEGORY_TEXT[0]
                        for d in analysis['detections'] if d['cat'] == 'ORGANISMO')
            export_payload = {'session_id': sid, 'use_confirmed_only': False, 'text': result['preview']['text']}
            for extension in ('docx', 'pdf'):
                raw = request('/api/export/' + extension, json.dumps(export_payload).encode(), {'Content-Type': 'application/json'})
                if extension == 'docx':
                    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                        xml = archive.read('word/document.xml').decode('utf-8')
                    if args.category_cases:
                        result['checks']['docx_additional_names_gone'] = not any(word in xml
                            for word in ('CARINA', 'ZORVIK', 'ESTEBAN', 'Zorvik', 'Zelkin', 'Quirna'))
                    result['checks']['docx_no_original_names'] = 'PÉREZ' not in xml and 'Perez' not in xml and 'GONZÁLEZ' not in xml
                else:
                    result['checks']['pdf_valid_signature'] = raw.startswith(b'%PDF-')
            csv = request('/api/export/csv', json.dumps({'session_id': sid}).encode(), {'Content-Type': 'application/json'})
            result['checks']['csv_downloads'] = b'PERSONA' in csv
            print(json.dumps(result['checks'], ensure_ascii=False), flush=True)
        finally:
            (results_dir / (result_name + '_results.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    if not all(result.get('checks', {}).values()) or not result.get('checks'):
        raise AssertionError(f'Falló la verificación del portable. Consultar {result_name}_results.json.')


if __name__ == '__main__':
    main()
