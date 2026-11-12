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

PUBLIC_REPOSITORY = 'CarolinaMMartin/anonimizador_uso_personal'
# Current delivery instructions; historical reports retain their versions.
# CHANGELOG is checked for active links, not for historical version prose.
PUBLICATION_DOCUMENTS = (
    'README.md', 'CONTRIBUTING.md', 'SECURITY.md', 'CHANGELOG.md',
    'docs/MANUAL_INSTALACION.md', 'docs/MANUAL_USUARIO.md',
    'docs/NOTAS_VERSION.md', 'docs/DEPLOY.md', 'docs/DESARROLLO.md',
    'docs/RELEASE_CHECKLIST.md', 'docs/COMPLIANCE.md',
    '.github/ISSUE_TEMPLATE/config.yml',
)


def _github_links(text: str):
    # Include Markdown, autolinks and URLs in shell examples. Dependency links
    # are allowed; only this application's repository family is checked below.
    for url in re.findall(r'https?://[^\s<>\[\]()`\"\']+', text):
        url = url.rstrip('.,;')
        parsed = urlsplit(url)
        parts = unquote(parsed.path).strip('/').split('/')
        if parsed.netloc.lower() == 'api.github.com' and parts[:1] == ['repos']:
            parts = parts[1:]
        elif parsed.netloc.lower() not in {'github.com', 'raw.githubusercontent.com'}:
            continue
        if len(parts) >= 2:
            parts[1] = parts[1].removesuffix('.git')
        if len(parts) >= 2 and (parts[1].lower().startswith('anonimizador')
                               or parts[-1].startswith('AnonimizadorJudicial-')):
            yield url, parts


def _windows_downloads(text: str):
    return [
        (url, parts) for url, parts in _github_links(text)
        if len(parts) == 6 and parts[2:4] == ['releases', 'download']
        and 'windows' in parts[5].lower() and parts[5].endswith('.zip')
    ]


def check_publication_links(documents: dict[str, str], version: str,
                            repository: str = PUBLIC_REPOSITORY) -> list[str]:
    """Reject wrong repositories, stale release tags and mismatched assets."""
    errors = []
    downloads = _windows_downloads(documents.get('README.md', ''))
    assets = {parts[5] for _, parts in downloads}
    if len(assets) != 1:
        errors.append('README.md must identify exactly one Windows ZIP download')
    asset = next(iter(assets)) if len(assets) == 1 else None
    if asset and f'-{version}-' not in asset:
        errors.append(f'Windows ZIP filename must contain current version {version}: {asset}')
    readme_assets = {parts[5] for _, parts in _github_links(documents.get('README.md', ''))
                    if len(parts) == 6 and parts[2:4] == ['releases', 'download']}
    # README is the source of the archive name, not an exemption from checking
    # arbitrary assets. Every checksum must belong to a recognized archive.
    archives = {asset} if asset else set()
    mac_archives: dict[str, set[str]] = {}
    for filename in readme_assets:
        lower = filename.lower()
        if not filename.endswith('.zip') or 'mac' not in lower:
            continue
        architecture = next((arch for pattern, arch in (
            (r'arm64|apple[-_]?silicon', 'arm64'),
            (r'intel|x86_64|x64', 'x86_64'),
            (r'universal2', 'universal2'),
        ) if re.search(pattern, lower)), None)
        if (architecture and filename.startswith(f'AnonimizadorJudicial-{version}-')):
            mac_archives.setdefault(architecture, set()).add(filename)
    for architecture, filenames in mac_archives.items():
        if len(filenames) > 1:
            errors.append(f'README.md must identify one Mac ZIP per architecture: {architecture}')
        archives.update(filenames)
    for filename in archives:
        if filename + '.sha256' not in readme_assets:
            errors.append(f'README.md is missing the matching ZIP checksum: {filename}.sha256')
    allowed_assets = archives | {name + '.sha256' for name in archives}
    for name, text in documents.items():
        for url, parts in _github_links(text):
            if '/'.join(parts[:2]).lower() != repository.lower():
                errors.append(f'Wrong publication repository: {name} -> {url}')
            if len(parts) >= 5 and parts[2:4] in (['releases', 'download'], ['releases', 'tag']):
                if parts[4] != f'v{version}':
                    errors.append(f'Stale release version: {name} -> {url}; expected v{version}')
            if len(parts) == 6 and parts[2:4] == ['releases', 'download']:
                filename = parts[5]
                if 'windows' in filename.lower() and asset and filename not in {asset, asset + '.sha256'}:
                    errors.append(f'Inconsistent Windows download asset: {name} -> {url}; expected {asset}')
                elif filename not in allowed_assets:
                    errors.append(f'Inconsistent download asset: {name} -> {url}; not listed in README.md')
    return errors


def release_download_info(root: Path = ROOT) -> dict[str, str]:
    """Return validated release metadata shared by the audit and CI packaging."""
    config = ast.parse((root / 'app/config.py').read_text(encoding='utf-8'))
    version = next(ast.literal_eval(node.value) for node in config.body
                   if isinstance(node, ast.Assign) and any(
                       isinstance(target, ast.Name) and target.id == 'APP_VERSION'
                       for target in node.targets))
    documents = {name: (root / name).read_text(encoding='utf-8')
                 for name in PUBLICATION_DOCUMENTS if (root / name).is_file()}
    errors = check_publication_links(documents, version)
    if errors:
        raise ValueError('\n'.join(errors))
    url, parts = _windows_downloads(documents['README.md'])[0]
    return {'repository': PUBLIC_REPOSITORY, 'version': version,
            'asset_name': parts[5], 'download_url': url}

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
    try:
        release_download_info()
    except (ValueError, OSError, StopIteration) as exc:
        errors.append(f'Publication metadata: {exc}')
    result = {'version': app_version(), 'checked': counts, 'errors': errors}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return not errors

if __name__ == '__main__':
    raise SystemExit(0 if audit() else 1)
