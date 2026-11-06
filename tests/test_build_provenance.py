"""A release must describe the environment and sources that built its binary."""
import importlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
provenance = importlib.import_module('build_provenance')
compliance = importlib.import_module('bundle_compliance')
package = importlib.import_module('package_release')


class InstalledDistribution:
    metadata = {'Name': 'demo-package', 'License-Expression': 'MIT'}
    version = '1.2.3'
    files = (Path('demo_package-1.2.3.dist-info/licenses/LICENSE'),)

    def __init__(self, root):
        self.root = root
        license_file = self.locate_file(self.files[0])
        license_file.parent.mkdir(parents=True)
        license_file.write_text('Original license', encoding='utf-8')

    def locate_file(self, item):
        return self.root / item

    def read_text(self, name):
        return json.dumps({'url': 'https://example.org/demo-package.whl'})


@pytest.fixture
def build(tmp_path, monkeypatch):
    repository = tmp_path / 'repository'
    (repository / 'app').mkdir(parents=True)
    (repository / 'app/config.py').write_text('APP_VERSION = "9.0.0"\n', encoding='utf-8')
    (repository / 'docs').mkdir()
    installed = InstalledDistribution(tmp_path / 'installed')
    monkeypatch.setattr(provenance, 'ROOT', repository)
    monkeypatch.setattr(provenance, 'distributions', lambda: (installed,))
    monkeypatch.setattr(compliance, 'ROOT', repository)
    monkeypatch.setattr(package, 'ROOT', repository)
    monkeypatch.setattr(package, 'app_version', lambda: '9.0.0')
    delivery = tmp_path / 'delivery'
    delivery.mkdir()
    (delivery / 'AnonimizadorJudicial-NLP.exe').write_bytes(b'compiled executable')
    (delivery / 'VERSION_APP.txt').write_text('9.0.0', encoding='ascii')
    return repository, delivery, installed


def test_text_json_and_provenance_come_from_the_same_build_snapshot(build):
    repository, delivery, _ = build
    snapshot = provenance.capture_build_snapshot()
    provenance.write_build_inventory(delivery, snapshot)
    inventory = json.loads((delivery / provenance.INVENTORY_PATH).read_text(encoding='utf-8'))
    recorded = json.loads((delivery / provenance.PROVENANCE_PATH).read_text(encoding='utf-8'))
    frozen = (delivery / provenance.FROZEN_PATH).read_text(encoding='utf-8')
    assert [line for line in frozen.splitlines() if not line.startswith('#')] == ['demo-package==1.2.3']
    assert [(item['name'], item['version']) for item in inventory] == [('demo-package', '1.2.3')]
    assert recorded['environment']['packages'][0]['direct_url']['url'].endswith('demo-package.whl')
    assert recorded['source_inputs']['app/config.py'] == provenance.digest_file(repository / 'app/config.py')
    assert (delivery / inventory[0]['license_files'][0]).read_text() == 'Original license'
    provenance.verify_build_provenance(delivery)


def test_build_refuses_an_environment_that_does_not_match_required_versions(build):
    repository, delivery, _ = build
    (repository / 'requirements.txt').write_text('demo-package==2.0.0\n', encoding='utf-8')
    with pytest.raises(ValueError, match='requirements.txt'):
        provenance.capture_build_snapshot()
    assert not (delivery / provenance.PROVENANCE_PATH).exists()


def test_repack_preserves_captured_inventories_and_third_party_licenses(build):
    repository, delivery, _ = build
    provenance.write_build_inventory(delivery, provenance.capture_build_snapshot())
    originals = {path.relative_to(delivery): path.read_bytes() for path in delivery.rglob('*') if path.is_file()}
    (repository / 'docs/dependencies-frozen.txt').write_text('unrelated-new-package==99.0\n')
    (repository / 'LICENSES/third_party').mkdir(parents=True)
    (repository / 'LICENSES/INVENTARIO_BUILD.json').write_text('[]')
    (repository / 'LICENSES/third_party/new-license').write_text('unrelated license')
    package.bundle_docs(delivery)
    compliance.bundle_compliance(delivery)
    assert {path.relative_to(delivery): path.read_bytes() for path in delivery.rglob('*') if path.is_file()} == originals


@pytest.mark.parametrize('changed', ['environment', 'source', 'binary', 'runtime', 'inventory', 'missing'])
def test_repack_refuses_mismatched_provenance_before_rewriting_any_file(build, monkeypatch, changed):
    repository, delivery, installed = build
    provenance.write_build_inventory(delivery, provenance.capture_build_snapshot())
    if changed == 'environment':
        monkeypatch.setattr(installed, 'version', '2.0.0')
    elif changed == 'source':
        (repository / 'app/config.py').write_text('APP_VERSION = "9.1.0"\n')
    elif changed == 'binary':
        (delivery / 'AnonimizadorJudicial-NLP.exe').write_bytes(b'other build')
    elif changed == 'runtime':
        (delivery / '_internal').mkdir()
        (delivery / '_internal/runtime.pyd').write_bytes(b'other dependency')
    elif changed == 'inventory':
        (delivery / provenance.FROZEN_PATH).write_text('demo-package==2.0.0\n')
    else:
        (delivery / provenance.PROVENANCE_PATH).unlink()
    before = {path.relative_to(delivery): path.read_bytes() for path in delivery.rglob('*') if path.is_file()}
    monkeypatch.setattr(sys, 'argv', ['package_release.py', '--package', str(delivery)])
    monkeypatch.setattr(package, 'verify_package', lambda _: None)
    monkeypatch.setattr(package, 'bundle_docs', lambda _: pytest.fail('Must reject before touching documentation.'))
    with pytest.raises(ValueError):
        package.main()
    assert {path.relative_to(delivery): path.read_bytes() for path in delivery.rglob('*') if path.is_file()} == before


@pytest.mark.parametrize('changed', ['environment', 'source'])
def test_build_detects_changes_while_compiling(build, monkeypatch, changed):
    repository, delivery, installed = build
    snapshot = provenance.capture_build_snapshot()
    if changed == 'environment':
        monkeypatch.setattr(installed, 'version', '2.0.0')
    else:
        (repository / 'app/config.py').write_text('APP_VERSION = "9.1.0"\n')
    with pytest.raises(ValueError, match='cambi'):
        provenance.write_build_inventory(delivery, snapshot)
    assert not (delivery / provenance.PROVENANCE_PATH).exists()
    assert not (delivery / provenance.INVENTORY_PATH).exists()
