import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('name_rules', ROOT / 'scripts/update_name_rules.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class NameRulesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = json.loads((ROOT / 'data/dictionaries/regex_limpio_v2.json').read_text(encoding='utf-8'))
        cls.names = [re.compile(cls.rules[i]['regex']) for i in (1, 2, 27)]

    def surfaces(self, text):
        return {m.group(1) for pattern in self.names for m in pattern.finditer(text)}

    def test_names_case_accents_and_surname_order(self):
        for text, expected in [
            ('Dr. Juan Perez solicita que se rechace la demanda', 'Juan Perez'),
            ('DR. JUAN PÉREZ SOLICITA QUE SE RECHACE LA DEMANDA', 'JUAN PÉREZ'),
            ('Dra. MARÍA JOSÉ GONZÁLEZ solicita medidas', 'MARÍA JOSÉ GONZÁLEZ'),
            ('Comparece PÉREZ, JUAN CARLOS y declara', 'PÉREZ, JUAN CARLOS'),
            ('Sr. PÉREZ manifestó su voluntad', 'PÉREZ'),
            ('Juan de la Cruz declaró', 'Juan de la Cruz'),
            ('JUAN DEL VALLE DECLARA', 'JUAN DEL VALLE'),
            ('juan perez solicita una medida', 'juan perez'),
            ('JUAN PEREZ\nABOGADO', 'JUAN PEREZ'),
        ]:
            with self.subTest(text=text):
                surfaces = self.surfaces(text)
                self.assertIn(expected, surfaces)
                self.assertTrue(all(s in text and 'solicita' not in s.lower() and 'rechace' not in s.lower()
                                    for s in surfaces), surfaces)

    def test_judicial_prose_is_not_a_person(self):
        for text in ['JUZGADO NACIONAL EN LO CIVIL', 'PODER JUDICIAL DE LA NACIÓN',
                     'SR. SOLICITA QUE SE RECHACE LA DEMANDA', 'Sr. solicita que se rechace',
                     'JUAN\nPEREZ', 'DERECHOS Y GARANTÍAS CONSTITUCIONALES']:
            with self.subTest(text=text):
                self.assertEqual(self.surfaces(text), set())

    def test_all_catalog_entries_support_uppercase(self):
        for filename in ('nombres.json', 'apellidos.json'):
            pattern = re.compile(module.catalog_alternatives(filename))
            values = json.loads((ROOT / 'data/dictionaries' / filename).read_text(encoding='utf-8'))
            for value in values:
                with self.subTest(catalog=filename, value=value):
                    self.assertIsNotNone(pattern.fullmatch(value.upper()))

    def test_all_rules_compile_and_structured_data_still_match(self):
        for rule in self.rules:
            re.compile(rule['regex'])
        for text, category in [('DNI 12.345.678', 'RGX_DNI'), ('correo@example.com', 'RGX_EMAIL'),
                               ('CUIT 20-12345678-9', 'RGX_CUIL_CUIT'), ('calle San Martin 123', 'RGX_DOMICILIO')]:
            self.assertTrue(any(r['activa'] and r['nombre_entidad'] == category and re.search(r['regex'], text)
                                for r in self.rules), text)
        self.assertFalse(self.rules[0]['activa'])

    def test_catalog_regeneration_matches_committed_rules(self):
        self.assertEqual(module.build_rules(write=False), self.rules)


if __name__ == '__main__':
    unittest.main()
