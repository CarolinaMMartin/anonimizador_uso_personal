"""Make repository documentation links usable from a GitHub Release."""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def render_release_notes(text: str, source: Path, root: Path,
                         repository: str, commit: str) -> str:
    if not re.fullmatch(r'[0-9a-fA-F]{40}', commit):
        raise ValueError('Release notes require a complete source commit SHA.')

    def replace(match):
        target = match.group(2)
        if urlsplit(target).scheme or target.startswith('#'):
            return match.group(0)
        path, marker, anchor = target.partition('#')
        resolved = (source.parent / path).resolve()
        if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
            raise ValueError(f'Release note link does not exist in repository: {target}')
        relative = resolved.relative_to(root.resolve()).as_posix()
        url = f'https://github.com/{repository}/blob/{commit}/{quote(relative)}'
        return match.group(1) + url + (marker + anchor if marker else '') + ')'

    return re.sub(r'(!?\[[^\]\n]*\]\()([^\)\n]+)\)', replace, text)


def main() -> None:
    from audit_repository import release_download_info

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    metadata = release_download_info()
    source = ROOT / 'docs/NOTAS_VERSION.md'
    rendered = render_release_notes(source.read_text(encoding='utf-8'), source, ROOT,
                                    metadata['repository'], args.commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding='utf-8')


if __name__ == '__main__':
    main()
