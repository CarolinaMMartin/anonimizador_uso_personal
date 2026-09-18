"""Genera el ZIP de entrega cuando la versión está lista.

Uso:
  python scripts/package_release.py
  python scripts/package_release.py --output dist/AnonimizadorJudicial-Windows.zip

Requisito: existir dist/AnonimizadorJudicial-NLP/ (build previo).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import shutil
import sys
import zipfile
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_NAME = "AnonimizadorJudicial-NLP"
SPACY_MODEL = "es_core_news_md"


def app_version() -> str:
    tree = ast.parse((ROOT / 'app/config.py').read_text(encoding='utf-8'))
    return next(ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == 'APP_VERSION' for target in node.targets))

# Archivos comunes obligatorios en cualquier paquete de entrega.
COMMON_REQUIRED_FILES = (
    "LICENSE",
    "NOTICE",
    "THIRD_PARTY_NOTICES.txt",
    "LEEME_INSTALACION.txt",
    "COMPLIANCE.md",
    "MANUAL_INSTALACION.md",
    "MANUAL_USUARIO.md",
    "CHANGELOG.md",
)
REQUIRED_DIRS = ("LICENSES",)
REQUIRED_MODEL_FILES = (
    f"models/{SPACY_MODEL}/LICENSE",
    f"models/{SPACY_MODEL}/config.cfg",
)

sys.path.insert(0, str(ROOT / "scripts"))
from bundle_compliance import bundle_compliance  # noqa: E402
from portable_docs import portable_text


def required_launchers() -> tuple[str, ...]:
    """Launchers obligatorios según el sistema donde se construye."""
    if sys.platform == "win32":
        return ("INICIAR.bat", "VERIFICAR.bat", "iniciar.ps1", "VERSION_APP.txt")
    if sys.platform == "darwin":
        return ("INICIAR.command", "VERIFICAR.command")
    return ()


def find_pkg_dir(explicit: Path | None = None) -> Path:
    """Busca la carpeta de entrega generada por build_portable_full.py."""
    if explicit is not None:
        package = explicit.expanduser().resolve()
        if not package.is_dir():
            raise SystemExit(f"No existe el paquete: {package}")
        return package
    dist = ROOT / "dist"
    candidate = dist / DIST_NAME
    if candidate.is_dir():
        return candidate

    # Compatibilidad con builds antiguos que hayan dejado solo la .app.
    app_candidate = dist / f"{DIST_NAME}.app"
    if app_candidate.is_dir():
        return app_candidate

    raise SystemExit(
        f"No existe paquete en dist/{DIST_NAME}.\n"
        "Primero: python scripts/build_portable_full.py"
    )


def delivery_root(pkg_dir: Path) -> Path:
    """Raíz que contiene launchers, manuales y licencias."""
    return pkg_dir.parent if pkg_dir.suffix == ".app" else pkg_dir


def runtime_dir(pkg_dir: Path) -> Path:
    """Carpeta donde viven frontend y modelo durante la ejecución."""
    if sys.platform == "darwin":
        app = pkg_dir if pkg_dir.suffix == ".app" else pkg_dir / f"{DIST_NAME}.app"
        if app.is_dir():
            return app / "Contents" / "MacOS"
    return pkg_dir


def verify_package(pkg_dir: Path) -> None:
    if sys.platform == "win32":
        if not (pkg_dir / f"{DIST_NAME}.exe").exists():
            raise SystemExit(f"No se encontró {DIST_NAME}.exe en {pkg_dir}")
        marker = pkg_dir / 'VERSION_APP.txt'
        if not marker.is_file() or marker.read_text(encoding='ascii').strip() != app_version():
            raise SystemExit('La versión del paquete no coincide con los fuentes. Compilá antes de empaquetar.')
    elif sys.platform == "darwin":
        app = pkg_dir if pkg_dir.suffix == ".app" else pkg_dir / f"{DIST_NAME}.app"
        binary = app / "Contents" / "MacOS" / DIST_NAME
        if not binary.exists():
            raise SystemExit(f"No se encontró el ejecutable de macOS en {binary}")
    else:
        raise SystemExit("El empaquetado portable se admite solo en Windows y macOS.")


def verify_portable_compliance(pkg_dir: Path) -> None:
    """Comprueba estructura, licencias, launchers y modelo local."""
    root = delivery_root(pkg_dir)
    runtime = runtime_dir(pkg_dir)
    missing: list[str] = []

    for name in COMMON_REQUIRED_FILES + required_launchers():
        if not (root / name).is_file():
            missing.append(name)

    for name in REQUIRED_DIRS:
        if not (root / name).is_dir():
            missing.append(f"{name}/")

    if not (runtime / "frontend").is_dir():
        missing.append("frontend/")

    for rel in REQUIRED_MODEL_FILES:
        if not (runtime / rel).is_file():
            missing.append(rel)

    if missing:
        raise SystemExit(
            "Paquete incompleto para entrega:\n  - " + "\n  - ".join(missing)
        )

    gpl = runtime / "models" / SPACY_MODEL / "LICENSE"
    head = gpl.read_text(encoding="utf-8", errors="replace")[:200]
    if "GNU GENERAL PUBLIC LICENSE" not in head:
        raise SystemExit(f"LICENSE del modelo no parece GPL-3.0: {gpl}")

    notices = (root / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")
    if "models/es_core_news_md/LICENSE" not in notices:
        raise SystemExit(
            "THIRD_PARTY_NOTICES.txt no referencia models/es_core_news_md/LICENSE"
        )

    print(
        "  Cumplimiento OK "
        "(ejecutable, launchers, frontend, modelo, licencias y manuales)"
    )


def bundle_docs(pkg_dir: Path) -> None:
    """Incluye manuales en la raíz del paquete de entrega."""
    root = delivery_root(pkg_dir)
    docs_dir = ROOT / "docs"
    for name in ('MANUAL_INSTALACION.md', 'MANUAL_USUARIO.md', 'DEPLOY.md',
                 'NOTAS_VERSION.md', f'VERIFICACION_{app_version()}.md'):
        src = docs_dir / name
        if not src.is_file():
            continue
        text = portable_text(src.read_text(encoding='utf-8'), src, Path(name))
        (root / name).write_text(text, encoding="utf-8")
        (root / name.replace(".md", ".txt")).write_text(text, encoding="utf-8")
        print(f"  Manual -> {root / name}")
    for source, name in ((ROOT / 'CHANGELOG.md', 'CHANGELOG.md'),
                         (docs_dir / 'dependencies-frozen.txt', 'DEPENDENCIAS_BUILD.txt')):
        if source.is_file():
            shutil.copyfile(source, root / name)


def write_release_zip(root: Path, output: Path) -> None:
    """Package the application resources without sessions or personal exports."""
    files = set(COMMON_REQUIRED_FILES) | set(required_launchers()) | {
        f'{DIST_NAME}.exe', DIST_NAME, 'COMPLIANCE.txt',
        'MANUAL_USUARIO.txt', 'MANUAL_INSTALACION.txt', 'DEPLOY.md', 'DEPLOY.txt',
        'DEPENDENCIAS_BUILD.txt', 'SOURCE_COMMIT.txt', 'SOURCE_TREE.txt',
        'NOTAS_VERSION.md', 'NOTAS_VERSION.txt',
        f'VERIFICACION_{app_version()}.md', f'VERIFICACION_{app_version()}.txt',
    }
    directories = {'_internal', 'frontend', 'models', 'LICENSES', f'{DIST_NAME}.app'}
    versioned_name = f'{DIST_NAME}-{app_version()}'
    # Some dependencies need DOCX/PDF/CSV resources (for example export
    # templates). Keep only files matching installed wheel resources byte
    # for byte; a user's document under the same directory is still excluded.
    resource_types = {'.docx', '.pdf', '.csv'}
    trusted_resources = {}
    for distribution in distributions():
        for record in distribution.files or ():
            if record.suffix.lower() in resource_types and '..' not in record.parts:
                source = Path(distribution.locate_file(record))
                if source.is_file():
                    trusted_resources['_internal/' + record.as_posix()] = source
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file in sorted(root.rglob('*')):
            if not file.is_file():
                continue
            relative = file.relative_to(root)
            if relative.parts[0] not in directories and relative.as_posix() not in files:
                continue
            if any(part in {'__pycache__', '.git', '.venv', 'uploads', 'exports'} for part in relative.parts):
                continue
            if any(part.startswith('.env') for part in relative.parts):
                continue
            if file.suffix.lower() in {'.db', '.log'} or file.name.endswith('.db-journal'):
                continue
            if file.suffix.lower() in resource_types:
                trusted = trusted_resources.get(relative.as_posix())
                if trusted is None or file.read_bytes() != trusted.read_bytes():
                    continue
            if not file.resolve().is_relative_to(root.resolve()):
                raise ValueError(f'El archivo apunta fuera del paquete: {relative}')
            archive.write(file, str(Path(versioned_name) / relative))
    with zipfile.ZipFile(output) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f'El ZIP contiene una entrada corrupta: {bad}')
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    output.with_name(output.name + '.sha256').write_text(f'{digest}  {output.name}\n', encoding='ascii')


def main() -> None:
    parser = argparse.ArgumentParser(description="Empaquetar ZIP de entrega")
    parser.add_argument("--package", type=Path, help="Carpeta portable, incluso fuera de dist/")
    parser.add_argument('--output', type=Path, help='Nombre y ruta del ZIP de entrega')
    parser.add_argument(
        "--suffix",
        default="",
        help=(
            "Sufijo opcional para el nombre del ZIP generado"
        ),
    )
    args = parser.parse_args()

    pkg_dir = find_pkg_dir(args.package)
    root = delivery_root(pkg_dir)
    verify_package(pkg_dir)

    print("Copiando manuales al paquete…")
    bundle_docs(pkg_dir)
    print("Copiando avisos legales y licencias…")
    bundle_compliance(root)
    print("Verificando paquete portable…")
    verify_portable_compliance(pkg_dir)

    platform = 'Windows-x64' if sys.platform == 'win32' else 'macOS'
    zip_base = f'{DIST_NAME}-{app_version()}-{args.suffix or platform}'
    zip_path = args.output.resolve() if args.output else ROOT / 'dist' / f'{zip_base}.zip'

    print(f"Comprimiendo {root} …")
    write_release_zip(root, zip_path)

    size_mb = zip_path.stat().st_size / 1024 / 1024
    print("\nZIP listo para entregar:")
    print(f"  {zip_path}")
    print(f"  {size_mb:.1f} MB")
    launcher = "INICIAR.bat" if sys.platform == "win32" else "INICIAR.command"
    print(f"\nEntregá el ZIP. Descomprimen y ejecutan {launcher}.")


if __name__ == "__main__":
    main()
