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

def test_release_zip_excludes_user_data_and_keeps_runtime_resources(tmp_path, monkeypatch):
    # Verify a Windows delivery on every CI host; the archive's launchers
    # depend on its destination platform, not on the platform running pytest.
    monkeypatch.setattr(package, 'required_launchers', lambda: ('INICIAR.bat', 'VERSION_APP.txt'))
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

@pytest.mark.parametrize('relative', ['.', 'dist', 'app/new', 'dist/../app/new'])
def test_explicit_build_output_rejects_paths_outside_dist(tmp_path, monkeypatch, relative):
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='dentro de dist'):
        builder.resolve_output_dir(Path(relative))


@pytest.mark.parametrize('kind', ['file', 'directory'])
def test_explicit_build_output_preserves_existing_destination(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    destination = tmp_path / 'dist/existing'
    destination.parent.mkdir()
    if kind == 'directory':
        destination.mkdir()
        original = destination / 'session.db'
    else:
        original = destination
    original.write_bytes(b'existing session')
    source = tmp_path / 'stage'
    source.mkdir()
    (source / 'application.exe').write_bytes(b'new application')
    with pytest.raises(ValueError, match='ya existe'):
        builder.copy_delivery(source, destination)
    assert original.read_bytes() == b'existing session'
    assert not (destination / 'application.exe').exists()


def test_explicit_output_copies_to_new_directory_and_preserves_old_installation(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    previous = tmp_path / 'dist' / builder.DIST_NAME
    previous.mkdir(parents=True)
    (previous / 'session.db').write_bytes(b'active session')
    source = tmp_path / 'stage'
    source.mkdir()
    (source / f'{builder.DIST_NAME}.exe').write_bytes(b'new executable')
    destination = builder.copy_delivery(source, Path('dist/new-version'))
    assert destination == (tmp_path / 'dist/new-version').resolve()
    assert (destination / f'{builder.DIST_NAME}.exe').read_bytes() == b'new executable'
    assert (previous / 'session.db').read_bytes() == b'active session'


def test_explicit_output_rechecks_destination_before_copying(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    requested = Path('dist/new-version')
    destination = builder.resolve_output_dir(requested)
    destination.mkdir(parents=True)
    (destination / 'session.db').write_bytes(b'newly opened session')
    with pytest.raises(ValueError, match='ya existe'):
        builder.copy_delivery(tmp_path / 'stage', requested)
    assert (destination / 'session.db').read_bytes() == b'newly opened session'


@pytest.mark.parametrize('installed_file', [
    'AnonimizadorJudicial-NLP.exe', 'VERSION_APP.txt',
    'AnonimizadorJudicial-NLP.app/Contents/MacOS/AnonimizadorJudicial-NLP',
])
def test_explicit_output_cannot_be_nested_in_an_existing_installation(tmp_path, monkeypatch, installed_file):
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    previous = tmp_path / 'dist/active'
    marker = previous / installed_file
    marker.parent.mkdir(parents=True)
    marker.write_bytes(b'installed application')
    with pytest.raises(ValueError, match='instalación existente'):
        builder.copy_delivery(tmp_path / 'stage', Path('dist/active/new-version'))
    assert marker.read_bytes() == b'installed application'
    assert not (previous / 'new-version').exists()


def test_explicit_output_allows_nested_directory_without_an_installation(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    (tmp_path / 'dist/releases').mkdir(parents=True)
    target = builder.resolve_output_dir(Path('dist/releases/new-version'))
    assert target == (tmp_path / 'dist/releases/new-version').resolve()


def test_explicit_output_rejects_dist_resolved_outside_repository(tmp_path, monkeypatch):
    root = tmp_path / 'repository'
    dist = root / 'dist'
    outside = tmp_path / 'outside'
    resolve = Path.resolve

    def redirected(path, *args, **kwargs):
        absolute = resolve(path, *args, **kwargs)
        return outside / absolute.relative_to(dist) if absolute.is_relative_to(dist) else absolute

    monkeypatch.setattr(builder, 'ROOT', root)
    monkeypatch.setattr(Path, 'resolve', redirected)
    with pytest.raises(ValueError, match='dentro del repositorio'):
        builder.resolve_output_dir(Path('dist/new-version'))


def test_explicit_output_refuses_directory_alias_outside_dist(tmp_path, monkeypatch):
    root = tmp_path / 'repository'
    (root / 'dist').mkdir(parents=True)
    outside = tmp_path / 'outside'
    outside.mkdir()
    alias = root / 'dist/alias'
    try:
        alias.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('Directory symlinks are unavailable on this host.')
    monkeypatch.setattr(builder, 'ROOT', root)
    with pytest.raises(ValueError, match='dentro de dist'):
        builder.resolve_output_dir(Path('dist/alias/new-version'))
    assert list(outside.iterdir()) == []


def test_default_build_output_keeps_legacy_copy_behavior(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    copies = []
    monkeypatch.setattr(builder, 'robust_copytree', lambda src, dst: copies.append((src, dst)))
    source = tmp_path / 'stage'
    destination = builder.copy_delivery(source)
    assert destination == tmp_path / 'dist' / builder.DIST_NAME
    assert copies == [(source, destination)]


def test_invalid_cli_output_fails_before_starting_build(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    monkeypatch.setattr(sys, 'argv', ['build_portable_full.py', '--output', 'app/new'])
    monkeypatch.setattr(builder, 'ensure_nlp', lambda: pytest.fail('Build must not start.'))
    with pytest.raises(SystemExit) as failure:
        builder.main()
    assert failure.value.code == 2


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

def test_portable_manual_links_use_delivered_files_and_identify_source_references():
    from portable_docs import portable_text
    source = ROOT / 'docs/DEPLOY.md'
    text = portable_text('[license](../LICENSE) [code](../app/config.py)', source, Path('DEPLOY.md'))
    assert '[license](LICENSE)' in text
    assert 'code (`app/config.py` en el código fuente)' in text
    assert 'github.com' not in text


def test_portable_release_notes_and_dependency_links_stay_local():
    from portable_docs import portable_text
    source = ROOT / 'docs/NOTAS_VERSION.md'
    original = (f'[verification](VERIFICACION_{package.app_version()}.md) '
                '[notes](NOTAS_VERSION.md) [inventory](dependencies-frozen.txt)')
    converted = portable_text(original, source, Path('NOTAS_VERSION.md'))
    assert f'[verification](VERIFICACION_{package.app_version()}.md)' in converted
    assert '[notes](NOTAS_VERSION.md)' in converted
    assert '[inventory](DEPENDENCIAS_BUILD.txt)' in converted


def test_bundled_changelog_links_resolve_inside_the_delivery(tmp_path, monkeypatch):
    import portable_docs
    repository = tmp_path / 'repository'
    (repository / 'docs').mkdir(parents=True)
    (repository / 'CHANGELOG.md').write_text(
        '[manual](docs/MANUAL_USUARIO.md) [download](README.md)', encoding='utf-8')
    (repository / 'docs/MANUAL_USUARIO.md').write_text('Manual', encoding='utf-8')
    (repository / 'README.md').write_text('Download instructions', encoding='utf-8')
    delivery = tmp_path / 'delivery'
    delivery.mkdir()
    monkeypatch.setattr(package, 'ROOT', repository)
    monkeypatch.setattr(portable_docs, 'ROOT', repository)
    monkeypatch.setattr(package, 'app_version', lambda: '9.0.0')
    package.bundle_docs(delivery)
    changelog = (delivery / 'CHANGELOG.md').read_text(encoding='utf-8')
    assert '[manual](MANUAL_USUARIO.md)' in changelog
    assert (delivery / 'MANUAL_USUARIO.md').is_file()
    assert '[download](README.md)' not in changelog
    assert 'README.md' in changelog

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
