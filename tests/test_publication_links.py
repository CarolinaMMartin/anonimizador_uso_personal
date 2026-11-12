"""Prevent download instructions from drifting from the version being built."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_repository import check_publication_links, release_download_info


VERSION = '8.2.1'
REPOSITORY = 'CarolinaMMartin/anonimizador_uso_personal'
ASSET = f'AnonimizadorJudicial-{VERSION}-Windows.zip'
URL = f'https://github.com/{REPOSITORY}/releases/download/v{VERSION}/{ASSET}'


def documents(extra=''):
    return {'README.md': f'[Descargar Windows]({URL})\n[SHA-256]({URL}.sha256)',
            'docs/MANUAL_INSTALACION.md': f'[Descargar]({URL})\n{extra}'}


@pytest.mark.parametrize('repository', [
    'CarolinaMMartin/anonimizador_mpf',
    'CarolinaMMartin/anonimizador_mpff',
    'OtherOwner/anonimizador_uso_personal',
    'OtherOwner/unrelated-project',
])
def test_wrong_repository_cannot_redirect_operators_to_an_old_project(repository):
    current = documents(URL.replace(REPOSITORY, repository))
    assert any('Wrong publication repository' in error
               for error in check_publication_links(current, VERSION))


def test_release_tag_must_match_source_even_when_filename_is_current():
    current = documents(URL.replace('/v8.2.1/', '/v8.1.0/'))
    assert any('Stale release version' in error
               for error in check_publication_links(current, VERSION))


@pytest.mark.parametrize('asset', ['AnonimizadorJudicial-Windows.zip', 'missing.zip', ASSET + '.sha255'])
def test_manual_cannot_link_to_an_asset_different_from_the_readme(asset):
    current = documents(URL.replace(ASSET, asset))
    assert any('Inconsistent' in error and 'download asset' in error
               for error in check_publication_links(current, VERSION))


def test_current_tag_does_not_hide_an_old_version_in_the_filename():
    current = {'README.md': URL.replace(ASSET, ASSET.replace(VERSION, '8.1.0'))}
    assert any('filename must contain current version' in error
               for error in check_publication_links(current, VERSION))


def test_history_dependency_versions_and_current_checksum_are_allowed():
    current = documents(URL + '.sha256')
    current['CHANGELOG.md'] = '## 8.1.0\nPrevious release.\n## 3.3.12\nOlder history.'
    current['docs/DESARROLLO.md'] = (
        'Python 3.12.14; spaCy 3.8.14; model 3.8.0.\n'
        f'git clone https://github.com/{REPOSITORY}.git\n'
        'https://github.com/explosion/spacy-models/releases/download/es_core_news_md-3.8.0/model.whl'
    )
    assert check_publication_links(current, VERSION) == []


def test_readme_must_have_one_unambiguous_windows_download():
    current = documents()
    current['README.md'] += '\n' + URL.replace(ASSET, f'AnonimizadorJudicial-{VERSION}-other-Windows.zip')
    assert any('exactly one Windows ZIP' in error
               for error in check_publication_links(current, VERSION))


@pytest.mark.parametrize('checksum', ['AnonimizadorJudicial-Windows.zip.sha256', ASSET + '.sha255'])
def test_readme_checksum_must_belong_to_its_windows_zip(checksum):
    current = documents()
    current['README.md'] += '\n' + URL.replace(ASSET, checksum)
    assert any('Inconsistent Windows download asset' in error
               for error in check_publication_links(current, VERSION))


def test_readme_requires_its_windows_checksum():
    current = documents()
    current['README.md'] = URL
    assert any('missing the matching ZIP checksum' in error
               for error in check_publication_links(current, VERSION))


@pytest.mark.parametrize('filename', ['unrelated.zip', 'unrelated.zip.sha256',
                                     'AnonimizadorJudicial-8.1.0-macOS-arm64.zip'])
def test_readme_cannot_authorize_unrelated_or_stale_archives(filename):
    current = documents()
    current['README.md'] += '\n' + URL.replace(ASSET, filename)
    assert any('Inconsistent download asset' in error
               for error in check_publication_links(current, VERSION))


def test_mac_architectures_each_use_their_own_archive_checksum():
    current = documents()
    intel = f'AnonimizadorJudicial-{VERSION}-macOS-Intel.zip'
    silicon = f'AnonimizadorJudicial-{VERSION}-macOS-arm64.zip'
    for filename in (intel, silicon):
        url = URL.replace(ASSET, filename)
        current['README.md'] += '\n' + url + '\n' + url + '.sha256'
    assert check_publication_links(current, VERSION) == []
    current['README.md'] = current['README.md'].replace(intel + '.sha256', intel + '.sha255')
    errors = check_publication_links(current, VERSION)
    assert any('missing the matching ZIP checksum' in error for error in errors)
    assert any('Inconsistent download asset' in error for error in errors)


def test_metadata_uses_source_version_and_ignores_archived_reports(tmp_path):
    (tmp_path / 'app').mkdir()
    (tmp_path / 'app/config.py').write_text(f'APP_VERSION = "{VERSION}"\n', encoding='utf-8')
    (tmp_path / 'README.md').write_text(documents()['README.md'], encoding='utf-8')
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs/VERIFICACION_8.1.0.md').write_text('Historical checks for 8.1.0.', encoding='utf-8')
    info = release_download_info(tmp_path)
    assert info == {'repository': REPOSITORY, 'version': VERSION,
                    'asset_name': ASSET, 'download_url': URL}
    (tmp_path / 'app/config.py').write_text('APP_VERSION = "8.2.2"\n', encoding='utf-8')
    with pytest.raises(ValueError, match='Stale release version'):
        release_download_info(tmp_path)
