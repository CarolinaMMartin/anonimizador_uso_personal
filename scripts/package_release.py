"""Genera el ZIP de entrega cuando la versión está lista.

Uso:
  python scripts/package_release.py
  python scripts/package_release.py --suffix v3.3.10-Windows-x64
  python scripts/package_release.py --suffix v3.3.10-macOS

Requisito: existir dist/AnonimizadorJudicial-NLP/ (build previo).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_NAME = "AnonimizadorJudicial-NLP"
SPACY_MODEL = "es_core_news_md"

# Archivos comunes obligatorios en cualquier paquete de entrega.
COMMON_REQUIRED_FILES = (
    "LICENSE",
    "NOTICE",
    "THIRD_PARTY_NOTICES.txt",
    "LEEME_INSTALACION.txt",
    "COMPLIANCE.md",
    "MANUAL_INSTALACION.md",
    "MANUAL_USUARIO.md",
)
REQUIRED_DIRS = ("LICENSES",)
REQUIRED_MODEL_FILES = (
    f"models/{SPACY_MODEL}/LICENSE",
    f"models/{SPACY_MODEL}/config.cfg",
)

sys.path.insert(0, str(ROOT / "scripts"))
from bundle_compliance import bundle_compliance  # noqa: E402


def required_launchers() -> tuple[str, ...]:
    """Launchers obligatorios según el sistema donde se construye."""
    if sys.platform == "win32":
        return ("INICIAR.bat", "VERIFICAR.bat")
    if sys.platform == "darwin":
        return ("INICIAR.command", "VERIFICAR.command")
    return ()


def find_pkg_dir() -> Path:
    """Busca la carpeta de entrega generada por build_portable_full.py."""
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
    for name in ("MANUAL_INSTALACION.md", "MANUAL_USUARIO.md", "DEPLOY.md"):
        src = docs_dir / name
        if not src.is_file():
            continue
        text = src.read_text(encoding="utf-8")
        (root / name).write_text(text, encoding="utf-8")
        (root / name.replace(".md", ".txt")).write_text(text, encoding="utf-8")
        print(f"  Manual -> {root / name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Empaquetar ZIP de entrega")
    parser.add_argument(
        "--suffix",
        default="",
        help=(
            "Sufijo opcional, por ejemplo v3.3.10-Windows-x64 o "
            "v3.3.10-macOS"
        ),
    )
    args = parser.parse_args()

    pkg_dir = find_pkg_dir()
    root = delivery_root(pkg_dir)
    verify_package(pkg_dir)

    print("Copiando manuales al paquete…")
    bundle_docs(pkg_dir)
    print("Copiando avisos legales y licencias…")
    bundle_compliance(root)
    print("Verificando paquete portable…")
    verify_portable_compliance(pkg_dir)

    zip_base = root.name + (f"-{args.suffix}" if args.suffix else "")
    zip_path = ROOT / "dist" / f"{zip_base}.zip"
    if zip_path.exists():
        zip_path.unlink()

    print(f"Comprimiendo {root} …")
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", root.parent, root.name)

    size_mb = zip_path.stat().st_size / 1024 / 1024
    print("\nZIP listo para entregar:")
    print(f"  {zip_path}")
    print(f"  {size_mb:.1f} MB")
    launcher = "INICIAR.bat" if sys.platform == "win32" else "INICIAR.command"
    print(f"\nEntregá el ZIP. Descomprimen y ejecutan {launcher}.")


if __name__ == "__main__":
    main()
