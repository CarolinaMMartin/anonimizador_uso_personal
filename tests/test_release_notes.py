"""Release notes must not depend on the Release page resolving relative links."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from release_notes import render_release_notes

COMMIT = '1' * 40


def test_release_notes_link_to_files_at_the_released_commit(tmp_path):
    docs = tmp_path / 'docs'
    docs.mkdir()
    source = docs / 'NOTAS_VERSION.md'
    (tmp_path / 'CHANGELOG.md').write_text('history', encoding='utf-8')
    (docs / 'MANUAL_INSTALACION.md').write_text('installation', encoding='utf-8')
    text = ('[changes](../CHANGELOG.md) '
            '[install](MANUAL_INSTALACION.md#abrir) '
            '[download](https://github.com/owner/repo/releases/download/v1/app.zip) '
            '[section](#limits)')
    result = render_release_notes(text, source, tmp_path, 'owner/repo', COMMIT)
    base = f'https://github.com/owner/repo/blob/{COMMIT}/'
    assert f'[changes]({base}CHANGELOG.md)' in result
    assert f'[install]({base}docs/MANUAL_INSTALACION.md#abrir)' in result
    assert '[download](https://github.com/owner/repo/releases/download/v1/app.zip)' in result
    assert '[section](#limits)' in result


@pytest.mark.parametrize('target', ['missing.md', '../../outside.md'])
def test_release_notes_reject_missing_or_outside_targets(tmp_path, target):
    source = tmp_path / 'docs/NOTAS_VERSION.md'
    with pytest.raises(ValueError, match='does not exist in repository'):
        render_release_notes(f'[link]({target})', source, tmp_path, 'owner/repo', COMMIT)


def test_release_notes_require_immutable_commit(tmp_path):
    with pytest.raises(ValueError, match='complete source commit'):
        render_release_notes('notes', tmp_path / 'notes.md', tmp_path, 'owner/repo', 'main')
