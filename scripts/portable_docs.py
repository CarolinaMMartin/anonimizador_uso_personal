"""Keep documentation links valid after copying repository docs into a portable."""
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DELIVERED = {'LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.txt', 'CHANGELOG.md',
             'MANUAL_INSTALACION.md', 'MANUAL_USUARIO.md', 'DEPLOY.md', 'COMPLIANCE.md'}

def portable_text(text, source, destination):
    from package_release import app_version
    def replace(match):
        target = match.group(2)
        if urlsplit(target).scheme or target.startswith('#'):
            return match.group(0)
        path, marker, anchor = target.partition('#')
        resolved = (source.parent / path).resolve()
        if not resolved.is_relative_to(ROOT):
            return match.group(0)
        relative = resolved.relative_to(ROOT).as_posix()
        if resolved.name in DELIVERED:
            delivered = Path(resolved.name)
        elif relative.startswith('LICENSES/'):
            delivered = Path(relative)
        else:
            url = f'https://github.com/CarolinaMMartin/anonimizador_uso_personal/blob/v{app_version()}/{relative}'
            return match.group(1) + url + (marker + anchor if marker else '') + ')'
        link = Path(os.path.relpath(delivered, destination.parent)).as_posix()
        return match.group(1) + link + (marker + anchor if marker else '') + ')'
    return re.sub(r'(!?\[[^\]\n]*\]\()([^\)\n]+)\)', replace, text)
