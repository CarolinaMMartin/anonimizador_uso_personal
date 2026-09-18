"""Exercise real DOCX detection, grouping, review and export with fictitious data."""
import argparse
import csv
import io
import json
import sys
import urllib.request
from pathlib import Path

import portable_smoke as fixture

ROOT = Path(__file__).resolve().parents[1]
PARAGRAPHS = [
    'RAMÍREZ, ALICIA compareció.',
    'Alicia Ramírez presentó un escrito.',
    'Alicia ratificó su declaración.',
    'La Sra. Ramírez declaró.',
    'SUÁREZ, LUIS compareció.',
    'Luis Suárez presentó un escrito.',
    'Luis ratificó su declaración.',
    'El Sr. Suárez declaró.',
    'Juan Pérez compareció.',
    'Juana Pérez compareció.',
    'El Sr. Pérez declaró.',
    'J. Pérez compareció.',
]
EXPECTED = [
    ['Ramírez, Alicia', 'Alicia Ramírez', 'Alicia', 'Ramírez'],
    ['Suárez, Luis', 'Luis Suárez', 'Luis', 'Suárez'],
]

LEARNED_PARAGRAPHS = [
    'Firmado por: IRINA ZORVIK, JUEZA',
    'Más adelante, Zorvik asumió compromisos.',
    'En su descargo, ZORVIK indicó lo sucedido.',
    'Dra. Mariana de la Quirna Zelkin declaró.',
    'Quirna Zelkin indicó lo sucedido.',
    'Dr. Matías Nolvik compareció.',
    'Dra. Juana Nolvik declaró.',
    'Nolvik indicó lo sucedido.',
    'Zorvik SA tiene su sede en Calle Zorvik 123.',
    'El código Zorvik123 se conserva.',
]


def normalize(value):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', value.casefold())
                   if unicodedata.category(c) != 'Mn').strip()


def verify(call, learned=False):
    fixture.TEXT[:] = PARAGRAPHS + (LEARNED_PARAGRAPHS if learned else [])
    docx = fixture.fictitious_docx()
    results = []
    for categories in (['PERSONA'], None):
        upload = call('POST', '/api/upload', file=docx)
        sid = upload['session_id']
        analysis = call('POST', '/api/analyze', {'session_id': sid, 'enabled_categories': categories})
        detections = {normalize(d['original']): d for d in analysis['detections'] if d['cat'] == 'PERSONA'}
        checks = {}
        group_ids = []
        for index, aliases in enumerate(EXPECTED, 1):
            members = [detections.get(normalize(alias)) for alias in aliases]
            checks[f'identity_{index}_aliases_detected'] = all(members)
            ids = {member['cluster_id'] for member in members if member}
            checks[f'identity_{index}_one_suggested_group'] = len(ids) == 1 and None not in ids
            if checks[f'identity_{index}_one_suggested_group']:
                group_id = next(iter(ids))
                group_ids.append(group_id)
                confirmed = call('POST', f'/api/clusters/{group_id}/confirm?session_id={sid}')
                current = {normalize(d['original']): d for d in confirmed['detections']}
                checks[f'identity_{index}_one_confirmed_label'] = len({current[normalize(alias)]['placeholder'] for alias in aliases}) == 1
        checks['identities_are_separate'] = len(set(group_ids)) == 2
        ambiguous = [detections.get(normalize(name)) for name in ('Juan Pérez', 'Juana Pérez', 'Pérez', 'J. Pérez')]
        checks['shared_surname_and_initial_are_not_merged'] = all(ambiguous) and len({d['cluster_id'] for d in ambiguous if d and d['cluster_id']}) == 0
        exported = call('POST', '/api/export/csv', {'session_id': sid}, raw=True)
        rows = list(csv.DictReader(io.StringIO(exported.decode('utf-8-sig')), delimiter=';'))
        by_surface = {normalize(row['Original']): row for row in rows if row['Tipo'] == 'PERSONA'}
        checks['csv_labels_match_confirmed_groups'] = all(
            all(normalize(alias) in by_surface for alias in aliases) and
            len({by_surface[normalize(alias)]['Sustitución'] for alias in aliases}) == 1
            for aliases in EXPECTED)
        if group_ids:
            first_id = group_ids[0]
            before = call('GET', f'/api/clusters?session_id={sid}')
            old_label = next(c['placeholder'] for c in before['clusters'] if c['cluster_id'] == first_id)
            split = call('POST', f'/api/clusters/{first_id}/remove-surface?session_id={sid}', {'surface': 'Ramírez'})
            detached = next(d for d in split['detections'] if normalize(d['original']) == 'ramirez')
            checks['removed_alias_changes_label'] = detached['placeholder'] != old_label and not detached['cluster_confirmed']
            separate = next(c for c in split['clusters'] if c['cluster_id'] == detached['cluster_id'])
            call('POST', f'/api/clusters/{separate["cluster_id"]}/reject?session_id={sid}')
            refreshed = call('GET', f'/api/clusters?session_id={sid}')
            checks['rejection_persists_on_refresh'] = all(c['cluster_id'] != separate['cluster_id'] for c in refreshed['clusters'])
        # Ensure the delivered binary includes the manual-ID fix too: deleting
        # one of two manual rows must not reuse the surviving mention's ID.
        first = call('POST', '/api/search-and-anonymize', {
            'session_id': sid, 'cat': 'OTRO', 'original': 'Alicia',
            'positions': detections['alicia']['positions'],
        })
        call('POST', '/api/search-and-anonymize', {
            'session_id': sid, 'cat': 'OTRO', 'original': 'Luis',
            'positions': detections['luis']['positions'],
        })
        call('DELETE', f'/api/detections/{first["detection"]["id"]}?session_id={sid}')
        added = call('POST', '/api/search-and-anonymize', {
            'session_id': sid, 'cat': 'OTRO', 'original': 'Alicia',
            'positions': detections['alicia']['positions'],
        })
        manual_ids = [mid for d in added['detections'] if d['cat'] == 'OTRO' for mid in d['mention_ids']]
        checks['manual_ids_are_unique_after_deletion'] = len(manual_ids) == len(set(manual_ids))
        if learned:
            surname = detections.get('zorvik')
            full = detections.get('irina zorvik')
            checks['unknown_surname_repetitions_detected'] = bool(surname and len(surname['positions']) == 2)
            checks['unknown_surname_has_document_evidence'] = bool(surname and 'document_alias' in surname['source_layers'])
            checks['unknown_surname_matches_full_name_group'] = bool(surname and full and surname['cluster_id'] and surname['cluster_id'] == full['cluster_id'])
            if checks['unknown_surname_matches_full_name_group']:
                confirmed = call('POST', f'/api/clusters/{surname["cluster_id"]}/confirm?session_id={sid}')
                current = {normalize(d['original']): d for d in confirmed['detections']}
                checks['unknown_surname_one_confirmed_label'] = current['zorvik']['placeholder'] == current['irina zorvik']['placeholder']
            else:
                checks['unknown_surname_one_confirmed_label'] = False
            compound = detections.get('quirna zelkin')
            complete = detections.get('mariana de la quirna zelkin')
            checks['natural_compound_surname_grouped'] = bool(compound and complete and compound['cluster_id'] and compound['cluster_id'] == complete['cluster_id'])
            ambiguous_surname = detections.get('nolvik')
            checks['ambiguous_unknown_surname_detected_separate'] = bool(ambiguous_surname and ambiguous_surname['cluster_id'] is None)
            preview = call('POST', '/api/export/preview', {'session_id': sid})['text']
            checks['company_and_address_protected_in_names_mode'] = ('Zorvik SA' in preview and 'Calle Zorvik 123' in preview) if categories else bool(surname and len(surname['positions']) == 2)
            checks['code_preserved'] = 'Zorvik123' in preview
            checks['sentences_preserved'] = 'asumió compromisos' in preview and 'indicó lo sucedido' in preview
            raw_word = call('POST', '/api/export/docx', {'session_id': sid}, raw=True)
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(io.BytesIO(raw_word)) as archive:
                extracted = ''.join(ET.fromstring(archive.read('word/document.xml')).itertext())
            checks['word_export_hides_learned_surname'] = 'Zorvik asumió' not in extracted and 'ZORVIK indicó' not in extracted
            import pdfplumber
            raw_pdf = call('POST', '/api/export/pdf', {'session_id': sid}, raw=True)
            with pdfplumber.open(io.BytesIO(raw_pdf)) as pdf:
                extracted = '\n'.join(page.extract_text() or '' for page in pdf.pages)
            checks['pdf_export_hides_learned_surname'] = 'Zorvik asumió' not in extracted and 'ZORVIK indicó' not in extracted and 'asumió' in extracted
        results.append({'categories': categories or 'ALL', 'checks': checks, 'analysis': analysis})
        print(json.dumps({'categories': categories or 'ALL', 'checks': checks}, ensure_ascii=False), flush=True)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', action='store_true')
    parser.add_argument('--learned-alias-cases', action='store_true')
    parser.add_argument('--url', default='http://127.0.0.1:8787')
    args = parser.parse_args()
    if args.source:
        sys.path.insert(0, str(ROOT))
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app) as client:
            def call(method, path, payload=None, file=None, raw=False):
                response = client.request(method, path, json=payload,
                    files={'file': ('agrupacion_ficticia.docx', file)} if file else None)
                response.raise_for_status()
                return response.content if raw else response.json()
            results = verify(call, args.learned_alias_cases)
        filename = 'learned_alias_source_results.json' if args.learned_alias_cases else 'grouping_source_results.json'
    else:
        fixture.BASE = args.url.rstrip('/')
        def call(method, path, payload=None, file=None, raw=False):
            headers = {}
            body = None if payload is None else json.dumps(payload).encode()
            if payload is not None:
                headers['Content-Type'] = 'application/json'
            if file:
                boundary = 'grouping-regression'
                body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="agrupacion_ficticia.docx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n'.encode() + file + f'\r\n--{boundary}--\r\n'.encode())
                headers['Content-Type'] = 'multipart/form-data; boundary=' + boundary
            request = urllib.request.Request(fixture.BASE + path, data=body, headers=headers, method=method)
            with fixture.OPENER.open(request, timeout=90) as response:
                data = response.read()
                return data if raw else json.loads(data)
        health = call('GET', '/health')
        results = verify(call, args.learned_alias_cases)
        for result in results:
            result['health'] = health
        filename = 'learned_alias_portable_results.json' if args.learned_alias_cases else 'grouping_portable_results.json'
    results_dir = ROOT / 'build/validation'
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / filename).write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not all(all(result['checks'].values()) for result in results):
        raise AssertionError(f'Grouping verification failed; see {filename}')


if __name__ == '__main__':
    main()
