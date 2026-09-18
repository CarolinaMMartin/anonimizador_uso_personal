"""Audit every publishable file without inspecting local sessions or documents."""
from __future__ import annotations
import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from package_release import app_version

def audit():
    names = subprocess.check_output(
        ['git', '-C', str(ROOT), 'ls-files', '--cached', '--others', '--exclude-standard'],
        text=True).splitlines()
    paths = sorted({ROOT / name for name in names if (ROOT / name).is_file()})
    errors = []
    counts = {'files': len(paths), 'python': 0, 'json': 0, 'markdown_links': 0}
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        parts = path.relative_to(ROOT).parts
        if parts[0] in {'.venv', 'models', 'build', 'dist'} or '__pycache__' in parts:
            errors.append(f'Generated resources tracked: {rel}')
        if path.suffix.lower() in {'.db', '.docx', '.pdf', '.csv', '.exe', '.log'}:
            errors.append(f'Unexpected data/binary file: {rel}')
        if path.name.startswith('.env'):
            errors.append(f'Environment file tracked: {rel}')
        if path.suffix.lower() not in {'.py', '.json', '.md', '.txt', '.js', '.cjs', '.html', '.css', '.yml', '.sh', '.bat', '.ps1', '.spec'}:
            continue
        try:
            text = path.read_text(encoding='utf-8')
            if path.suffix == '.py':
                ast.parse(text, filename=rel)
                counts['python'] += 1
            elif path.suffix == '.json':
                json.loads(text)
                counts['json'] += 1
            if path.suffix == '.md':
                # Code fences can contain example links; inspect actual prose only.
                prose = re.sub(r'```.*?```', '', text, flags=re.S)
                for target in re.findall(r'!?\[[^\]\n]*\]\(([^\)\n]+)\)', prose):
                    target = target.strip().split(' ')[0].strip('<>')
                    if not target or target.startswith('#') or urlsplit(target).scheme:
                        continue
                    counts['markdown_links'] += 1
                    resolved = path.parent / unquote(target.split('#')[0])
                    if not resolved.exists():
                        errors.append(f'Broken link: {rel} -> {target}')
                if '3.3.11-fix' in text and not rel.startswith('docs/propuestas/'):
                    errors.append(f'Old local release label: {rel}')
        except (ValueError, SyntaxError, UnicodeError) as exc:
            errors.append(f'{rel}: {exc}')
    rules = json.loads((ROOT / 'data/dictionaries/regex_limpio_v2.json').read_text(encoding='utf-8'))
    for rule in rules:
        try:
            re.compile(rule['regex'])
        except re.error as exc:
            errors.append(f'Invalid rule {rule.get("nombre_entidad")}: {exc}')
    import yaml
    workflow = yaml.load((ROOT / '.github/workflows/release-windows.yml').read_text(encoding='utf-8'), Loader=yaml.BaseLoader)
    if not {'on', 'jobs', 'permissions'} <= workflow.keys():
        errors.append('Invalid release workflow structure')
    for name in ('README.md', 'CHANGELOG.md', 'THIRD_PARTY_NOTICES.txt', 'docs/MANUAL_INSTALACION.md', 'docs/MANUAL_USUARIO.md', 'docs/DEPLOY.md', 'docs/COMPLIANCE.md'):
        if app_version() not in (ROOT / name).read_text(encoding='utf-8'):
            errors.append(f'Missing current version: {name}')
    for name in ('INICIAR_DESARROLLO.bat', 'INICIAR_DESARROLLO.sh'):
        text = (ROOT / name).read_text(encoding='utf-8').lower()
        if 'taskkill' in text or 'kill -9' in text:
            errors.append(f'Launcher stops unrelated processes: {name}')
    result = {'version': app_version(), 'checked': counts, 'errors': errors}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return not errors

if __name__ == '__main__':
    raise SystemExit(0 if audit() else 1)
