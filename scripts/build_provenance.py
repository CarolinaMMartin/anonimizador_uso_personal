"""Capture build inputs once and verify them before repackaging a portable."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib.metadata import distributions
import json
import platform
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = Path('LICENSES/INVENTARIO_BUILD.json')
FROZEN_PATH = Path('DEPENDENCIAS_BUILD.txt')
PROVENANCE_PATH = Path('BUILD_PROVENANCE.json')
SOURCE_DIRECTORIES = ('app', 'frontend', 'data/dictionaries', 'scripts/pyinstaller_hooks', 'scripts/windows')
SOURCE_FILES = (
    'requirements.txt', 'requirements-dev.txt',
    'scripts/launcher.py', 'scripts/build_portable_full.py', 'scripts/install_nlp.py',
    'scripts/bundle_compliance.py', 'scripts/package_release.py',
    'scripts/build_provenance.py', 'scripts/portable_docs.py',
)


def digest_file(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonical_name(name: str) -> str:
    return re.sub(r'[-_.]+', '-', name).lower()


def source_manifest(root: Path | None = None) -> dict[str, str]:
    root = ROOT if root is None else root
    files = {root / name for name in SOURCE_FILES if (root / name).is_file()}
    for directory in SOURCE_DIRECTORIES:
        files.update(path for path in (root / directory).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts
                     and path.suffix.lower() not in {'.pyc', '.pyo'})
    result = {}
    for path in sorted(files):
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f'Un archivo de compilación apunta fuera del repositorio: {path}')
        result[path.relative_to(root).as_posix()] = digest_file(path)
    return result


def environment_identity(installed=None) -> dict:
    installed = tuple(distributions()) if installed is None else installed
    packages = []
    for distribution in installed:
        name = distribution.metadata.get('Name')
        if not name:
            raise ValueError('Una distribución instalada no identifica su nombre.')
        record = {'name': name, 'version': distribution.version}
        direct_url = distribution.read_text('direct_url.json')
        if direct_url:
            record['direct_url'] = json.loads(direct_url)
        packages.append(record)
    packages.sort(key=lambda item: canonical_name(item['name']))
    names = [canonical_name(item['name']) for item in packages]
    if len(names) != len(set(names)):
        raise ValueError('El entorno contiene distribuciones duplicadas; reconstruí el entorno.')
    return {
        'python': platform.python_version(),
        'implementation': platform.python_implementation(),
        'platform': sys.platform,
        'machine': platform.machine(),
        'packages': packages,
    }


@dataclass(frozen=True)
class BuildSnapshot:
    environment: dict
    source_inputs: dict[str, str]
    installed: tuple


def capture_build_snapshot(root: Path | None = None) -> BuildSnapshot:
    from packaging.requirements import Requirement

    installed = tuple(sorted(distributions(),
                             key=lambda item: canonical_name(item.metadata.get('Name') or '')))
    environment = environment_identity(installed)
    repository = ROOT if root is None else root
    versions = {canonical_name(item['name']): item['version'] for item in environment['packages']}
    for name in ('requirements.txt', 'requirements-dev.txt'):
        path = repository / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.split('#', 1)[0].strip()
            if not line:
                continue
            required = Requirement(line)
            if required.marker and not required.marker.evaluate():
                continue
            installed_version = versions.get(canonical_name(required.name))
            if installed_version is None or not required.specifier.contains(installed_version, prereleases=True):
                raise ValueError(f'El entorno no coincide con {name}: {required}. Instalá las dependencias fijadas.')
    return BuildSnapshot(environment, source_manifest(root), installed)


def verify_build_snapshot(snapshot: BuildSnapshot, root: Path | None = None) -> None:
    if snapshot.environment != environment_identity():
        raise ValueError('El entorno de dependencias cambió desde la compilación; reconstruí el portable.')
    if snapshot.source_inputs != source_manifest(root):
        raise ValueError('Los archivos fuente cambiaron desde la compilación; reconstruí el portable.')


def binary_manifest(root: Path) -> dict[str, str]:
    candidates = (
        Path('AnonimizadorJudicial-NLP.exe'),
        Path('AnonimizadorJudicial-NLP'),
        Path('AnonimizadorJudicial-NLP.app/Contents/MacOS/AnonimizadorJudicial-NLP'),
        Path('Contents/MacOS/AnonimizadorJudicial-NLP'),
    )
    binaries = {}
    for relative in candidates:
        path = root / relative
        if path.is_file():
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError(f'El ejecutable apunta fuera del paquete: {relative}')
            binaries[relative.as_posix()] = digest_file(path)
    if not binaries:
        raise ValueError('No se encontró un ejecutable para registrar la compilación.')
    return binaries


def runtime_manifest(root: Path) -> dict[str, str]:
    """Fingerprint shipped code/model assets without reading user documents."""
    result = binary_manifest(root)
    for name in ('INICIAR.bat', 'VERIFICAR.bat', 'iniciar.ps1', 'VERSION_APP.txt',
                 'INICIAR.command', 'VERIFICAR.command'):
        path = root / name
        if path.is_file():
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError(f'Un lanzador apunta fuera del paquete: {name}')
            result[name] = digest_file(path)
    for directory in ('_internal', 'frontend', 'models', 'AnonimizadorJudicial-NLP.app', 'Contents'):
        for path in sorted((root / directory).rglob('*')):
            relative = path.relative_to(root)
            if not path.is_file():
                continue
            if any(part in {'__pycache__', '.git', '.venv', 'uploads', 'exports'}
                   or part.startswith('.env') for part in relative.parts):
                continue
            # Export templates are separately checked against installed wheels
            # by the ZIP writer; user documents must never be read here.
            if path.suffix.lower() in {'.db', '.log', '.docx', '.pdf', '.csv'} or path.name.endswith('.db-journal'):
                continue
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError(f'Un recurso apunta fuera del paquete: {relative}')
            result[relative.as_posix()] = digest_file(path)
    return result


def frozen_inventory(inventory: list[dict], environment: dict) -> str:
    header = (
        '# Inventario capturado durante la compilación; incluye herramientas de desarrollo.\n'
        f"# Python {environment['python']} ({environment['implementation']}), "
        f"{environment['platform']} {environment['machine']}.\n"
        '# Mismas distribuciones que LICENSES/INVENTARIO_BUILD.json.\n'
    )
    return header + ''.join(f"{item['name']}=={item['version']}\n" for item in inventory)


def write_build_inventory(root: Path, snapshot: BuildSnapshot) -> None:
    """Write the paired inventories only for a newly compiled package."""
    if any((root / path).exists() for path in (INVENTORY_PATH, FROZEN_PATH, PROVENANCE_PATH)):
        raise ValueError('El paquete ya tiene inventario de compilación; se conserva sin cambios.')
    verify_build_snapshot(snapshot)
    binaries = binary_manifest(root)
    inventory = []
    for distribution in snapshot.installed:
        name = distribution.metadata['Name']
        copied = []
        for item in distribution.files or ():
            if not (any(part.lower() in {'licenses', 'licences'} for part in item.parts)
                    or item.name.upper().startswith(('LICENSE', 'LICENCE', 'COPYING', 'NOTICE'))):
                continue
            source = Path(distribution.locate_file(item))
            if not source.is_file():
                continue
            destination = root / 'LICENSES/third_party' / name / str(item)
            if not destination.resolve().is_relative_to((root / 'LICENSES/third_party').resolve()):
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
            copied.append(destination.relative_to(root).as_posix())
        inventory.append({
            'name': name, 'version': distribution.version,
            'license_expression': distribution.metadata.get('License-Expression'),
            'license_files': copied,
        })
    (root / INVENTORY_PATH).parent.mkdir(parents=True, exist_ok=True)
    (root / INVENTORY_PATH).write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (root / FROZEN_PATH).write_text(frozen_inventory(inventory, snapshot.environment), encoding='utf-8')
    provenance = {
        'schema': 1,
        'environment': snapshot.environment,
        'source_inputs': snapshot.source_inputs,
        'binaries': binaries,
        'runtime_files': runtime_manifest(root),
        'inventory_sha256': digest_file(root / INVENTORY_PATH),
        'frozen_sha256': digest_file(root / FROZEN_PATH),
    }
    (root / PROVENANCE_PATH).write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def verify_build_provenance(root: Path) -> None:
    """Refuse stale sources/environments without changing the existing delivery."""
    try:
        provenance = json.loads((root / PROVENANCE_PATH).read_text(encoding='utf-8'))
        inventory = json.loads((root / INVENTORY_PATH).read_text(encoding='utf-8'))
        if provenance.get('schema') != 1:
            raise ValueError('Versión de procedencia de compilación desconocida.')
        for path, key in ((INVENTORY_PATH, 'inventory_sha256'), (FROZEN_PATH, 'frozen_sha256')):
            if digest_file(root / path) != provenance[key]:
                raise ValueError(f'El inventario de compilación fue modificado: {path}')
        expected = frozen_inventory(inventory, provenance['environment'])
        if (root / FROZEN_PATH).read_text(encoding='utf-8') != expected:
            raise ValueError('Los inventarios JSON y texto de la compilación no coinciden.')
        recorded = [(item['name'], item['version']) for item in inventory]
        packages = [(item['name'], item['version']) for item in provenance['environment']['packages']]
        if recorded != packages:
            raise ValueError('El inventario no corresponde al entorno de compilación registrado.')
        if binary_manifest(root) != provenance['binaries']:
            raise ValueError('El ejecutable no corresponde al inventario de compilación.')
        if runtime_manifest(root) != provenance['runtime_files']:
            raise ValueError('Los recursos o dependencias del portable cambiaron desde la compilación.')
        snapshot = BuildSnapshot(provenance['environment'], provenance['source_inputs'], ())
        verify_build_snapshot(snapshot)
    except (OSError, KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        raise ValueError('Falta una procedencia de compilación válida; reconstruí el portable.') from exc
