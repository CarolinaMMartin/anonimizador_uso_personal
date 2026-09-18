"""Build constrained portable regex rules from the bundled name/surname catalogs.

No runtime dependency is added. Run again after editing the catalogs.
"""

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DICTIONARIES = ROOT / 'data/dictionaries'


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.casefold())
                   if unicodedata.category(c) != 'Mn')


def catalog_alternatives(filename):
    catalog = json.loads((DICTIONARIES / filename).read_text(encoding='utf-8'))
    if not isinstance(catalog, list) or not catalog or not all(isinstance(v, str) and v.strip() for v in catalog):
        raise ValueError(f'Invalid catalog: {filename}')
    values = sorted({normalize(value.strip()) for value in catalog}, key=lambda v: (-len(v), v))
    accents = {'a': '[aáàâä]', 'e': '[eéèêë]', 'i': '[iíìîï]',
               'o': '[oóòôö]', 'u': '[uúùûü]', 'n': '[nñ]'}
    alternatives = []
    for value in values:
        alternatives.append(''.join(r'[ \t\u00a0]+' if ch == ' ' else accents.get(ch, re.escape(ch))
                                    for ch in value))
    return '(?i:(?:' + '|'.join(alternatives) + '))'


def build_rules(write=True):
    names = catalog_alternatives('nombres.json')
    surnames = catalog_alternatives('apellidos.json')
    # Horizontal whitespace prevents swallowing the next paragraph/heading.
    space = r'[ \t\u00a0]+'
    particle = r'(?i:(?:de(?:[ \t\u00a0]+la)?|del))[ \t\u00a0]+'
    surname = rf'(?:{particle})?{surnames}\b'
    full_name = rf'{names}\b(?:{space}{names}\b){{0,2}}{space}{surname}(?:{space}{surname})?'
    reversed_name = rf'{surname}(?:{space}{surname})?,[ \t\u00a0]*{names}\b(?:{space}{names}\b){{0,2}}'
    path = DICTIONARIES / 'regex_limpio_v2.json'
    rules = json.loads(path.read_text(encoding='utf-8'))
    rules[1]['descripcion'] = 'Títulos + nombres/apellidos del catálogo; mayúsculas y tildes; sin capturar oraciones'
    rules[1]['regex'] = rf'\b(?i:Dr|Dra|Lic|Sr|Sra|Sres|Sras)\b\.?[ \t\u00a0:]+({reversed_name}|{full_name}|{surname})\b'
    rules[2]['descripcion'] = 'Firmas del catálogo antes de ABOGADO/DNI/CUIT; sin capturar encabezados'
    rules[2]['regex'] = rf'\b({full_name}|{reversed_name})\b(?=[ \t\u00a0\r\n]+(?i:ABOGAD[OA]|D\.?N\.?I\.?|C\.?U\.?I\.?[TL]\.?|T[°º*]))'
    rules[27]['descripcion'] = 'Nombre + apellido o apellido, nombre del catálogo; cualquier capitalización y tildes'
    rules[27]['regex'] = rf'\b({reversed_name}|{full_name})\b'
    # The original case-caption pattern is redundant with the internal party
    # extractor and can include judicial prose within each party's span.
    rules[0]['activa'] = False
    rules[0]['descripcion'] = 'Desactivada por amplitud: usar el extractor interno de partes y las detecciones individuales'
    for rule in rules:
        re.compile(rule['regex'])
    if write:
        path.write_text(json.dumps(rules, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return rules


if __name__ == '__main__':
    build_rules()
