"""Regression checks for privacy and guarded release tooling."""
import hashlib
import importlib
import sys
import zipfile
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
package = importlib.import_module('package_release')
builder = importlib.import_module('build_portable_full')

def test_release_zip_excludes_user_data_and_keeps_runtime_resources(tmp_path):
    root = tmp_path / 'portable'
    files = {
        'VERSION_APP.txt': package.app_version(),
        'INICIAR.bat': 'start',
        'AnonimizadorJudicial-NLP.exe': 'binary',
        'models/es_core_news_md/config.cfg': 'model',
        '_internal/data/dictionaries/nombres.json': '[]',
        'frontend/app.js': 'client',
        'LICENSES/third_party/pkg/LICENSE': 'license',
        'PUERTO_ACTUAL.txt': '8792',
        'equivalencias.csv': 'private',
        'data/sessions.db': 'private',
        '_internal/data/sessions.db': 'private',
        '_internal/uploads/private.txt': 'private',
        'frontend/debug.log': 'private',
        'frontend/export.docx': 'private',
        '.env': 'secret',
        '_internal/.env.local': 'secret',
    }
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    output = tmp_path / 'release.zip'
    package.write_release_zip(root, output)
    prefix = f'AnonimizadorJudicial-NLP-{package.app_version()}/'
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        names = {name.removeprefix(prefix) for name in archive.namelist()}
    assert names == set(list(files)[:7])
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    assert output.with_name('release.zip.sha256').read_text().strip() == f'{digest}  release.zip'

def test_package_version_is_checked_before_rewriting_docs(tmp_path, monkeypatch):
    monkeypatch.setattr(package.sys, 'platform', 'win32')
    (tmp_path / 'AnonimizadorJudicial-NLP.exe').write_bytes(b'binary')
    (tmp_path / 'VERSION_APP.txt').write_text('0.0.1')
    with pytest.raises(SystemExit, match='versi'):
        package.verify_package(tmp_path)

@pytest.mark.parametrize('target', [ROOT, ROOT / 'app', ROOT / 'dist', Path(ROOT.anchor)])
def test_recursive_delete_refuses_source_and_roots(target):
    with pytest.raises(ValueError):
        builder.check_generated_path(target)

def test_recursive_delete_accepts_only_generated_descendants():
    builder.check_generated_path(ROOT / 'dist/AnonimizadorJudicial-NLP')
    builder.check_generated_path(builder.STAGE_ROOT / 'dist/AnonimizadorJudicial-NLP')

def test_missing_packaged_model_cannot_pass_by_loading_development_model(tmp_path):
    with pytest.raises(SystemExit, match='modelo'):
        builder.smoke_test_pkg(tmp_path)

def test_mac_launchers_use_package_path_and_preserve_other_processes(tmp_path, monkeypatch):
    monkeypatch.setattr(builder.sys, 'platform', 'darwin')
    builder.write_launchers(tmp_path)
    launcher = (tmp_path / 'INICIAR.command').read_text(encoding='utf-8')
    assert 'kill -9' not in launcher
    assert 'lsof' in launcher
    assert (tmp_path / 'VERIFICAR.command').is_file()

def test_portable_manual_links_point_to_delivered_files_or_versioned_source():
    from portable_docs import portable_text
    source = ROOT / 'docs/DEPLOY.md'
    text = portable_text('[license](../LICENSE) [code](../app/config.py)', source, Path('DEPLOY.md'))
    assert '[license](LICENSE)' in text
    assert f'/blob/v{package.app_version()}/app/config.py)' in text

def test_wheel_export_template_is_preserved_but_modified_documents_are_excluded(tmp_path):
    from importlib.metadata import distribution
    original = Path(distribution('python-docx').locate_file('docx/templates/default.docx'))
    root = tmp_path / 'portable'
    template = root / '_internal/docx/templates/default.docx'
    template.parent.mkdir(parents=True)
    template.write_bytes(original.read_bytes())
    output = tmp_path / 'release.zip'
    package.write_release_zip(root, output)
    with zipfile.ZipFile(output) as archive:
        exported = archive.read(f'AnonimizadorJudicial-NLP-{package.app_version()}/_internal/docx/templates/default.docx')
    assert exported == original.read_bytes()
    from docx import Document
    import io
    assert Document(io.BytesIO(exported)) is not None
    template.write_bytes(b'private document')
    package.write_release_zip(root, output)
    with zipfile.ZipFile(output) as archive:
        assert archive.namelist() == []
