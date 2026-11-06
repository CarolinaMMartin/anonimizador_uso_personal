"""Verify distinct identities from case captions through every export format."""
import argparse
import csv
import io
import json
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
PARAGRAPHS = [
    'El expediente caratulado “Benítez Quiroga, Lucía c/ Ferraro, Tomás s/ daños y perjuicios”, '
    'Expte. N.º 27463/2026, tramita ante el Juzgado Civil N.º 12. En la presentación inicial, '
    'Lucía Benítez Quiroga manifestó que el conflicto se originó a partir de una reunión '
    'mantenida con Tomás Ferraro el día 4 de abril de 2026.',
    'Según relató Lucía, durante esa reunión también estuvo presente Eliana Molina, quien '
    'habría intervenido como testigo de parte de las conversaciones previas. Más adelante, '
    'Benítez Quiroga sostuvo que Ferraro asumió ciertos compromisos que luego no fueron cumplidos.',
    'Por su parte, Tomás negó los hechos atribuidos y afirmó que la documentación acompañada '
    'por Eliana no reflejaba correctamente lo ocurrido. En su descargo, Ferraro indicó que '
    'Molina solo participó en una instancia informal y que no tenía conocimiento directo '
    'de todos los antecedentes.',
    'Finalmente, el juzgado dispuso correr traslado de la presentación y requirió a Eliana Molina '
    'que acompañara toda la información vinculada con las comunicaciones mantenidas con '
    'Lucía Benítez Quiroga y Tomás Ferraro, incluyendo mensajes, correos electrónicos '
    'y cualquier otro registro relevante para la causa.',
]
IDENTITIES = [
    (['Benítez Quiroga, Lucía', 'Lucía Benítez Quiroga', 'Lucía', 'Benítez Quiroga'], 5),
    (['Ferraro, Tomás', 'Tomás Ferraro', 'Ferraro', 'Tomás'], 6),
    (['Eliana Molina', 'Eliana', 'Molina'], 4),
]


def normalize(value):
    return ' '.join(value.casefold().split())


CAPTION_CASES = [
    ('lucia benitez c/ narel volsen', ['lucia benitez', 'narel volsen'], ''),
    ('narel volsen c/ tevan drumek', ['narel volsen', 'tevan drumek'], ''),
    ('narel volsen c/  tevan drumek s/ daños y perjuicios', ['narel volsen', 'tevan drumek'], 'daños y perjuicios'),
    ('NAREL VOLSEN C./ TEVAN DRUMEK S./ DAÑOS Y PERJUICIOS', ['NAREL VOLSEN', 'TEVAN DRUMEK'], 'DAÑOS Y PERJUICIOS'),
    ('narel volsen s/ sucesión ab intestato', ['narel volsen'], 'sucesión ab intestato'),
    ('Lucía Benítez c/ Tomás Ferraro', ['Lucía Benítez', 'Tomás Ferraro'], ''),
    ('narel volsen c/\ntevan drumek s/\ndaños y perjuicios', ['narel volsen', 'tevan drumek'], 'daños y perjuicios'),
    ('Volsen, Narel c/ Drumek, Tevan s/ daños', ['Volsen, Narel', 'Drumek, Tevan'], 'daños'),
    ('volsen, narel c/ drumek, tevan s/ daños', ['volsen, narel', 'drumek, tevan'], 'daños'),
    ('Lucía Benítez s/ declaración de certeza', ['Lucía Benítez'], 'declaración de certeza'),
    ('informe técnico sobre salud', [], 'informe técnico sobre salud'),
    ('solicita medidas c/ que corresponda', [], 'solicita medidas c/ que corresponda'),
    ('informe técnico s/ cumplimiento', [], 'informe técnico s/ cumplimiento'),
    ('recurso extraordinario s/ nulidad', [], 'recurso extraordinario s/ nulidad'),
    ('Zorlan vexor gundor c/ Altra zexor pellor s/ daños', ['Zorlan vexor gundor', 'Altra zexor pellor'], 'daños'),
    ('Mario vexor gundor c/ Tomas ferrao s/ daños', ['Mario vexor gundor', 'Tomas ferrao'], 'daños'),
    ('Zorlan perez gundor c/ Altra zexor pellor s/ daños', ['Zorlan perez gundor', 'Altra zexor pellor'], 'daños'),
    ('zorlan de la vexor del monte azul c/ tevan drumek s/ daños', ['zorlan de la vexor del monte azul', 'tevan drumek'], 'daños'),
    ('acme servicios s.a. c/ zorlan vexor s/ cobro', ['zorlan vexor'], 'cobro', {'EMPRESA': ['acme servicios s.a.']}),
    ('consulta pendiente c/ resolución administrativa', [], 'consulta pendiente c/ resolución administrativa'),
]


def document_bytes(extension, paragraphs=None):
    paragraphs = PARAGRAPHS if paragraphs is None else paragraphs
    buffer = io.BytesIO()
    if extension == 'docx':
        from docx import Document
        document = Document()
        for paragraph in paragraphs:
            document.add_paragraph(paragraph)
        document.save(buffer)
    else:
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        style = getSampleStyleSheet()['Normal']
        story = []
        for paragraph in paragraphs:
            story.extend([Paragraph(escape(paragraph), style), Spacer(1, 12)])
        SimpleDocTemplate(buffer).build(story)
    return buffer.getvalue()


def exported_text(raw, extension):
    if extension == 'docx':
        from docx import Document
        return '\n'.join(p.text for p in Document(io.BytesIO(raw)).paragraphs)
    import pdfplumber
    with pdfplumber.open(io.BytesIO(raw)) as document:
        return '\n'.join(page.extract_text() or '' for page in document.pages)


def verify(call):
    results = []
    for extension in ('docx', 'pdf'):
        upload = call('POST', '/api/upload', file=(f'identidades_ficticias.{extension}', document_bytes(extension)))
        sid = upload['session_id']
        analysis = call('POST', '/api/analyze', {'session_id': sid, 'label_mode': 'cat'})
        people = [d for d in analysis['detections'] if d['cat'] == 'PERSONA']
        by_surface = {normalize(d['original']): d for d in people}
        checks = {}
        group_ids, labels = [], []
        for index, (aliases, occurrences) in enumerate(IDENTITIES, 1):
            rows = [by_surface.get(normalize(alias)) for alias in aliases]
            checks[f'identity_{index}_all_variants_detected'] = all(rows)
            owners = {row['cluster_id'] for row in rows if row}
            checks[f'identity_{index}_one_group'] = len(owners) == 1 and None not in owners
            checks[f'identity_{index}_occurrences'] = sum(len(row['positions']) for row in rows if row) == occurrences
            if checks[f'identity_{index}_one_group']:
                owner = next(iter(owners))
                group_ids.append(owner)
                confirmed = call('POST', f'/api/clusters/{owner}/confirm?session_id={sid}')
                label = confirmed['cluster']['placeholder']
                labels.append((label, occurrences))
                checks[f'identity_{index}_one_confirmed_label'] = all(
                    row['placeholder'] == label for row in confirmed['detections']
                    if normalize(row['original']) in {normalize(alias) for alias in aliases})
        checks['exactly_three_separate_identities'] = len(set(group_ids)) == 3
        checks['no_combined_parties_or_extra_people'] = set(by_surface) == {
            normalize(alias) for aliases, _ in IDENTITIES for alias in aliases}
        preview = call('POST', '/api/export/preview', {'session_id': sid})['text']
        texts = {'preview': preview}
        for output in ('docx', 'pdf'):
            texts[output] = exported_text(call('POST', '/api/export/' + output, {'session_id': sid}, raw=True), output)
        for output, text in texts.items():
            checks[f'{output}_identity_occurrences'] = len(labels) == 3 and all(text.count(label) == count for label, count in labels)
            checks[f'{output}_no_original_names'] = not any(
                normalize(alias) in normalize(text) for aliases, _ in IDENTITIES for alias in aliases)
            flat = ' '.join(text.split())
            checks[f'{output}_case_caption_and_prose_preserved'] = all(
                term in flat for term in (' c/ ', ' s/ daños y perjuicios', 'Según relató', 'asumió ciertos compromisos', 'Por su parte'))
        raw_csv = call('POST', '/api/export/csv', {'session_id': sid}, raw=True)
        rows = list(csv.DictReader(io.StringIO(raw_csv.decode('utf-8-sig')), delimiter=';'))
        csv_people = {normalize(row['Original']): row for row in rows if row['Tipo'] == 'PERSONA'}
        checks['csv_has_three_consistent_labels'] = len({r['Sustitución'] for r in csv_people.values()}) == 3 and all(
            all(normalize(alias) in csv_people for alias in aliases) and
            len({csv_people[normalize(alias)]['Sustitución'] for alias in aliases}) == 1
            for aliases, _ in IDENTITIES)
        results.append({'input': extension, 'checks': checks})
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)
    return results


def verify_case_boundaries(call):
    import re
    results = []
    for index, case in enumerate(CAPTION_CASES, 1):
        text, expected, subject = case[:3]
        other_entities = case[3] if len(case) > 3 else {}
        upload = call('POST', '/api/upload', file=('caratula_ficticia.docx', document_bytes('docx', [text])))
        sid = upload['session_id']
        analysis = call('POST', '/api/analyze', {'session_id': sid, 'label_mode': 'cat'})
        people = [d for d in analysis['detections'] if d['cat'] == 'PERSONA']
        labels = {row['placeholder'] for row in people}
        if not expected:
            results.append({'case': index, 'checks': {'ordinary_prose_not_detected': not analysis['detections']}})
            print(json.dumps(results[-1]), flush=True)
            continue
        checks = {
            'complete_separate_parties': {normalize(row['original']) for row in people} == {normalize(name) for name in expected},
            'distinct_replacements': len(labels) == len(expected),
        }
        for category, values in other_entities.items():
            checks[category.lower() + '_classified_completely'] = all(any(
                row['cat'] == category and normalize(row['original']).rstrip('.') == normalize(value).rstrip('.')
                for row in analysis['detections']) for value in values)
        texts = {'preview': call('POST', '/api/export/preview', {'session_id': sid})['text']}
        for extension in ('docx', 'pdf'):
            texts[extension] = exported_text(call('POST', '/api/export/' + extension, {'session_id': sid}, raw=True), extension)
        connectors = re.findall(r'(?<!\w)[cs]\s*\.?\s*/', text, flags=re.I)
        for output, value in texts.items():
            secrets = expected + [name for names in other_entities.values() for name in names]
            checks[output + '_names_hidden'] = not any(normalize(name).rstrip('.') in normalize(value) for name in secrets)
            checks[output + '_one_label_per_party'] = sum(value.count(label) for label in labels) == len(expected)
            checks[output + '_separators_preserved'] = re.findall(r'(?<!\w)[cs]\s*\.?\s*/', value, flags=re.I) == connectors
            if subject:
                checks[output + '_subject_or_prose_preserved'] = normalize(subject) in normalize(value)
        results.append({'case': index, 'checks': checks})
        print(json.dumps(results[-1]), flush=True)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', action='store_true')
    parser.add_argument('--url', default='http://127.0.0.1:8789')
    parser.add_argument('--caption-cases', action='store_true')
    args = parser.parse_args()
    checker = verify_case_boundaries if args.caption_cases else verify
    if args.source:
        import sys
        sys.path.insert(0, str(ROOT))
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app) as client:
            def call(method, path, payload=None, file=None, raw=False):
                response = client.request(method, path, json=payload, files={'file': file} if file else None)
                response.raise_for_status()
                return response.content if raw else response.json()
            results = checker(call)
    else:
        opener = build_opener(ProxyHandler({}))
        def call(method, path, payload=None, file=None, raw=False):
            headers = {'Content-Type': 'application/json'} if payload is not None else {}
            body = json.dumps(payload).encode() if payload is not None else None
            if file:
                name, data = file
                boundary = 'identity-flow-regression'
                body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
                        'Content-Type: application/octet-stream\r\n\r\n').encode() + data + f'\r\n--{boundary}--\r\n'.encode()
                headers['Content-Type'] = 'multipart/form-data; boundary=' + boundary
            request = Request(args.url.rstrip('/') + path, data=body, headers=headers, method=method)
            with opener.open(request, timeout=120) as response:
                data = response.read()
            return data if raw else json.loads(data)
        results = checker(call)
    prefix = 'caption_boundaries' if args.caption_cases else 'identity_flow'
    output = ROOT / 'build/validation' / (prefix + ('_source.json' if args.source else '_portable.json'))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not all(all(result['checks'].values()) for result in results):
        raise AssertionError(f'Falló la verificación de identidades: {output.name}')


if __name__ == '__main__':
    main()
