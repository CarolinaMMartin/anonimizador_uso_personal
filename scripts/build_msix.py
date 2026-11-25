"""Arma el paquete MSIX para Microsoft Store a partir del portable ya construido.

Uso (después de scripts/build_portable_full.py):
  python scripts/build_msix.py
  python scripts/build_msix.py --layout-only      # solo la carpeta, sin Windows SDK
  python scripts/build_msix.py --package dist/AnonimizadorJudicial-NLP-3.4.5

Salida:
  build/msix/AnonimizadorUsoPersonal/                  carpeta del paquete
  dist/AnonimizadorUsoPersonal-VERSION-x64.msix        paquete sin firmar

El MSIX es una salida adicional del mismo build: no modifica el portable.
No se firma: Microsoft Store lo firma al certificarlo.

La carpeta del paquete lleva el ejecutable, ``_internal`` (con los
diccionarios), ``frontend``, el modelo, las licencias, el manifiesto y los
íconos. No lleva ``INICIAR.bat``, ``VERIFICAR.bat`` ni ``iniciar.ps1``: un
paquete de Store arranca directamente el ``.exe``.

``makepri.exe`` y ``makeappx.exe`` se buscan en ``ANON_WINDOWS_SDK_BIN``, en el
PATH y en el Windows SDK instalado.

Prueba local sin firmar (con el modo de desarrollador de Windows activo):
  Add-AppxPackage -Register build\\msix\\AnonimizadorUsoPersonal\\AppxManifest.xml
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import msix_manifest  # noqa: E402
from portable_docs import PDF_MANUALS  # noqa: E402
from package_release import (  # noqa: E402
    DIST_NAME, RESOURCE_TYPES, SPACY_MODEL, app_version, trusted_wheel_resources,
)

PACKAGE_NAME = "AnonimizadorUsoPersonal"
LAYOUT_DIR = ROOT / "build" / "msix" / PACKAGE_NAME
PRI_WORK_DIR = ROOT / "build" / "msix" / "pri"
DEFAULT_LANGUAGE = "es-AR"

# Lo que viaja en el paquete. Todo lo demás del portable queda afuera.
PACKAGE_DIRECTORIES = ("_internal", "frontend", "models", "LICENSES")
PACKAGE_FILES = (
    f"{DIST_NAME}.exe",
    "LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.txt", "COMPLIANCE.md",
    "MANUAL_USUARIO.md", "CHANGELOG.md",
    "DEPENDENCIAS_BUILD.txt", "BUILD_PROVENANCE.json", "SOURCE_COMMIT.txt",
)
REQUIRED_FILES = (
    "AppxManifest.xml",
    *(f"Manuales/{name}" for name in PDF_MANUALS),
    f"{DIST_NAME}.exe",
    "LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.txt",
    "frontend/index.html",
    f"models/{SPACY_MODEL}/config.cfg",
    f"models/{SPACY_MODEL}/LICENSE",
)
REQUIRED_DIRECTORIES = ("_internal", "LICENSES", "Assets")
# Scripts de arranque del portable y cualquier otro script de consola.
SCRIPT_SUFFIXES = frozenset({".bat", ".cmd", ".ps1"})
STATE_SUFFIXES = frozenset({".db", ".log"})
STATE_NAMES = frozenset({"PUERTO_ACTUAL.txt", "VERSION_APP.txt"})
EXCLUDED_PARTS = frozenset({"__pycache__", ".git", ".venv", "uploads", "exports"})


def msix_filename(version: str | None = None) -> str:
    return f"{PACKAGE_NAME}-{version or app_version()}-x64.msix"


def is_excluded(relative: Path) -> bool:
    """Scripts de arranque, estado local y datos que nunca se empaquetan."""
    if any(part in EXCLUDED_PARTS or part.startswith(".env") for part in relative.parts):
        return True
    suffix = relative.suffix.lower()
    return (suffix in SCRIPT_SUFFIXES or suffix in STATE_SUFFIXES
            or relative.name in STATE_NAMES or relative.name.endswith(".db-journal"))


def check_layout_path(path: Path) -> None:
    """Solo se borra dentro de build/msix del repositorio."""
    target = path.resolve()
    parent = (ROOT / "build" / "msix").resolve()
    if target == parent or not target.is_relative_to(parent):
        raise ValueError(f"La carpeta del paquete debe quedar dentro de build/msix: {target}")


def stage_layout(package: Path, layout: Path = LAYOUT_DIR, *, version: str | None = None,
                 trusted_resources: dict[str, Path] | None = None) -> list[str]:
    """Copia el portable a la carpeta del paquete y devuelve lo que dejó afuera."""
    version = version or app_version()
    if not (package / f"{DIST_NAME}.exe").is_file():
        raise SystemExit(f"No se encontró {DIST_NAME}.exe en {package}.\n"
                         "Primero: python scripts/build_portable_full.py")
    if trusted_resources is None:
        trusted_resources = trusted_wheel_resources()
    if layout.exists():
        check_layout_path(layout)
        shutil.rmtree(layout)
    layout.mkdir(parents=True)

    skipped: list[str] = []
    for source in sorted(package.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(package)
        in_scope = relative.parts[0] in PACKAGE_DIRECTORIES or relative.as_posix() in PACKAGE_FILES
        if not in_scope:
            continue
        if is_excluded(relative):
            skipped.append(relative.as_posix())
            continue
        if relative.suffix.lower() in RESOURCE_TYPES:
            trusted = trusted_resources.get(relative.as_posix())
            if trusted is None or source.read_bytes() != trusted.read_bytes():
                skipped.append(relative.as_posix())
                continue
        if not source.resolve().is_relative_to(package.resolve()):
            raise ValueError(f"El archivo apunta fuera del paquete: {relative}")
        target = layout / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    manuals = layout / "Manuales"
    manuals.mkdir()
    for name in PDF_MANUALS:
        shutil.copyfile(ROOT / "docs" / "manuales" / name, manuals / name)

    manifest = msix_manifest.render_manifest(version)
    errors = msix_manifest.validate_manifest(manifest, version)
    if errors:
        raise SystemExit("Manifiesto inválido:\n  - " + "\n  - ".join(errors))
    (layout / "AppxManifest.xml").write_text(manifest, encoding="utf-8")
    shutil.copytree(msix_manifest.ASSETS_DIR, layout / "Assets")
    return skipped


def verify_layout(layout: Path, version: str | None = None) -> list[str]:
    """Errores de estructura de la carpeta del paquete (lista vacía si está bien)."""
    version = version or app_version()
    errors: list[str] = []
    for name in REQUIRED_FILES:
        if not (layout / name).is_file():
            errors.append(f"Falta {name}")
    for name in REQUIRED_DIRECTORIES:
        if not (layout / name).is_dir():
            errors.append(f"Falta la carpeta {name}/")
    manifest_path = layout / "AppxManifest.xml"
    if manifest_path.is_file():
        manifest = manifest_path.read_text(encoding="utf-8")
        errors += msix_manifest.validate_manifest(manifest, version)
        if not errors or not any("XML válido" in error for error in errors):
            for logo in msix_manifest.logo_paths(manifest):
                if not (layout / logo).is_file():
                    errors.append(f"El manifiesto referencia un ícono inexistente: {logo}")
    for path in sorted(layout.rglob("*")):
        if path.is_file() and is_excluded(path.relative_to(layout)):
            errors.append(f"Archivo que no debe empaquetarse: {path.relative_to(layout).as_posix()}")
    return errors


def verify_msix(msix: Path, version: str | None = None) -> list[str]:
    """Errores de un ``.msix`` ya empaquetado (es un ZIP con manifiesto y mapa de bloques)."""
    version = version or app_version()
    errors: list[str] = []
    try:
        with zipfile.ZipFile(msix) as archive:
            names = archive.namelist()
            manifest = (archive.read("AppxManifest.xml").decode("utf-8-sig")
                        if "AppxManifest.xml" in names else None)
    except (OSError, zipfile.BadZipFile) as exc:
        return [f"No se pudo leer el paquete: {exc}"]
    if manifest is None:
        return ["El paquete no contiene AppxManifest.xml"]
    errors += msix_manifest.validate_manifest(manifest, version)
    for required in ("AppxBlockMap.xml", "[Content_Types].xml", "resources.pri", *REQUIRED_FILES):
        if required not in names:
            errors.append(f"El paquete no contiene {required}")
    if not any(name.startswith("_internal/") for name in names):
        errors.append("El paquete no contiene _internal/")
    for name in names:
        if is_excluded(Path(name)):
            errors.append(f"Archivo que no debe empaquetarse: {name}")
    return errors


# ── Herramientas del Windows SDK ──────────────────────────────────────────

def _sdk_version_key(path: Path) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", path.parent.parent.name))


def find_sdk_tool(name: str) -> Path:
    """Ubica ``makeappx.exe`` o ``makepri.exe`` (x64)."""
    override = os.environ.get("ANON_WINDOWS_SDK_BIN", "").strip()
    if override:
        candidate = Path(override) / name
        if candidate.is_file():
            return candidate
        raise SystemExit(f"ANON_WINDOWS_SDK_BIN no contiene {name}: {override}")
    on_path = shutil.which(name)
    if on_path:
        return Path(on_path)
    roots = [Path(os.environ.get(variable, "")) / "Windows Kits" / "10" / "bin"
             for variable in ("ProgramFiles(x86)", "ProgramFiles") if os.environ.get(variable)]
    candidates = [path for root in roots if root.is_dir() for path in root.glob(f"10.*/x64/{name}")]
    if not candidates:
        raise SystemExit(
            f"No se encontró {name}. Instalá el Windows SDK o definí ANON_WINDOWS_SDK_BIN.\n"
            "Para armar solo la carpeta del paquete: python scripts/build_msix.py --layout-only")
    return max(candidates, key=_sdk_version_key)


def run(command: list[str]) -> None:
    print(">", " ".join(str(part) for part in command), flush=True)
    subprocess.check_call([str(part) for part in command])


def generate_pri(layout: Path, work: Path = PRI_WORK_DIR) -> Path:
    """Genera ``resources.pri`` para que Windows resuelva los íconos calificados.

    Se indexan solo el manifiesto y ``Assets``: los nombres ``scale-200`` y
    ``targetsize-24_altform-unplated`` no se resuelven sin este índice. Indexar
    ``_internal`` no aporta nada y haría que MakePri interprete carpetas como
    ``lang/es`` como recursos por idioma.
    """
    makepri = find_sdk_tool("makepri.exe")
    if work.exists():
        check_layout_path(work)
        shutil.rmtree(work)
    project = work / "project"
    project.mkdir(parents=True)
    shutil.copy2(layout / "AppxManifest.xml", project / "AppxManifest.xml")
    shutil.copytree(layout / "Assets", project / "Assets")
    config = work / "priconfig.xml"
    run([makepri, "createconfig", "/cf", config, "/dq", DEFAULT_LANGUAGE, "/o"])
    # Un solo resources.pri: sin esta sección MakePri reparte los recursos por
    # idioma y escala en paquetes de recursos separados.
    text = config.read_text(encoding="utf-8")
    config.write_text(re.sub(r"<packaging>.*?</packaging>\s*", "", text, flags=re.S), encoding="utf-8")
    output = layout / "resources.pri"
    run([makepri, "new", "/pr", project, "/cf", config, "/mn", project / "AppxManifest.xml",
         "/of", output, "/o"])
    if not output.is_file():
        raise SystemExit("MakePri no generó resources.pri")
    return output


def pack(layout: Path, output: Path) -> Path:
    makeappx = find_sdk_tool("makeappx.exe")
    output.parent.mkdir(parents=True, exist_ok=True)
    run([makeappx, "pack", "/o", "/h", "SHA256", "/d", layout, "/p", output])
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Paquete MSIX para Microsoft Store")
    parser.add_argument("--package", type=Path, default=ROOT / "dist" / DIST_NAME,
                        help="Carpeta portable generada por build_portable_full.py")
    parser.add_argument("--output", type=Path,
                        help="Ruta del .msix (por defecto, dist/AnonimizadorUsoPersonal-VERSION-x64.msix)")
    parser.add_argument("--layout-only", action="store_true",
                        help="Arma y verifica la carpeta del paquete sin usar el Windows SDK")
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("El paquete MSIX se arma solo en Windows.")

    package = args.package.expanduser().resolve()
    version = app_version()
    marker = package / "VERSION_APP.txt"
    if not marker.is_file() or marker.read_text(encoding="ascii").strip() != version:
        raise SystemExit("La versión del portable no coincide con los fuentes. "
                         "Compilá con scripts/build_portable_full.py antes de empaquetar.")

    print(f"=== Paquete MSIX {msix_manifest.store_version(version)} ===\n")
    print(f"Portable: {package}")
    skipped = stage_layout(package, LAYOUT_DIR, version=version)
    print(f"Carpeta del paquete: {LAYOUT_DIR}")
    for name in skipped:
        print(f"  No se empaqueta: {name}")

    if not args.layout_only:
        generate_pri(LAYOUT_DIR)
    errors = verify_layout(LAYOUT_DIR, version)
    if errors:
        raise SystemExit("Carpeta del paquete incompleta:\n  - " + "\n  - ".join(errors))
    if args.layout_only:
        print("\nCarpeta lista (sin resources.pri ni .msix).")
        return

    output = (args.output.expanduser().resolve() if args.output
              else ROOT / "dist" / msix_filename(version))
    pack(LAYOUT_DIR, output)
    errors = verify_msix(output, version)
    if errors:
        raise SystemExit("Paquete MSIX inválido:\n  - " + "\n  - ".join(errors))
    size_mb = output.stat().st_size / 1024 / 1024
    print(f"\nMSIX listo (sin firmar; la Store lo firma al certificarlo):\n  {output}\n  {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
