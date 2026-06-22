"""Genera el ZIP de entrega para alumnos / IT solo cuando la versión está lista.

Uso:
  .venv\\Scripts\\python scripts\\package_release.py
  .venv\\Scripts\\python scripts\\package_release.py --suffix IALAB-v3.1

Requisito: existir dist\\AnonimizadorJudicial-NLP\\ (build previo).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_NAME = "AnonimizadorJudicial-NLP"
SPACY_MODEL = "es_core_news_md"

# Archivos obligatorios en el portable de entrega
REQUIRED_FILES = (
    "LICENSE",
    "THIRD_PARTY_NOTICES.txt",
    "LEEME_INSTALACION.txt",
    "INICIAR.bat",
    "VERIFICAR.bat",
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


def find_pkg_dir() -> Path:
    dist = ROOT / "dist"
    for name in (DIST_NAME, f"{DIST_NAME}.app"):
        candidate = dist / name
        if candidate.is_dir():
            return candidate
    raise SystemExit(
        f"No existe paquete en dist/{DIST_NAME}.\n"
        "Primero: python scripts/build_portable_full.py"
    )


def verify_package(pkg_dir: Path) -> None:
    if sys.platform == "win32":
        if not (pkg_dir / f"{DIST_NAME}.exe").exists():
            raise SystemExit(f"No se encontró {DIST_NAME}.exe en {pkg_dir}")
    elif sys.platform == "darwin":
        app = pkg_dir if pkg_dir.suffix == ".app" else pkg_dir / f"{DIST_NAME}.app"
        binary = pkg_dir / DIST_NAME
        macos_bin = app / "Contents" / "MacOS" / DIST_NAME if app.is_dir() else None
        if not any(p and p.exists() for p in (binary, macos_bin)):
            raise SystemExit(f"No se encontró ejecutable Mac en {pkg_dir}")
    else:
        if not (pkg_dir / DIST_NAME).exists() and not (pkg_dir / f"{DIST_NAME}.exe").exists():
            raise SystemExit(f"Paquete incompleto: {pkg_dir}")


def verify_portable_compliance(pkg_dir: Path) -> None:
    """Comprueba que el ZIP cumple licencias y no falta el modelo."""
    missing: list[str] = []
    for name in REQUIRED_FILES:
        if not (pkg_dir / name).is_file():
            missing.append(name)
    for name in REQUIRED_DIRS:
        if not (pkg_dir / name).is_dir():
            missing.append(f"{name}/")
    for rel in REQUIRED_MODEL_FILES:
        if not (pkg_dir / rel).is_file():
            missing.append(rel)
    if missing:
        raise SystemExit(
            "Paquete incompleto para entrega:\n  - " + "\n  - ".join(missing)
        )

    gpl = pkg_dir / "models" / SPACY_MODEL / "LICENSE"
    head = gpl.read_text(encoding="utf-8", errors="replace")[:200]
    if "GNU GENERAL PUBLIC LICENSE" not in head:
        raise SystemExit(f"LICENSE del modelo no parece GPL-3.0: {gpl}")

    notices = (pkg_dir / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")
    if "models/es_core_news_md/LICENSE" not in notices:
        raise SystemExit("THIRD_PARTY_NOTICES.txt no referencia models/es_core_news_md/LICENSE")

    print("  Cumplimiento OK (LICENSE, modelo GPL, avisos legales, manuales)")


def bundle_docs(pkg_dir: Path) -> None:
    """Incluye manuales en la carpeta/ZIP de entrega."""
    docs_dir = ROOT / "docs"
    for name in ("MANUAL_INSTALACION.md", "MANUAL_USUARIO.md", "DEPLOY.md"):
        src = docs_dir / name
        if not src.is_file():
            continue
        text = src.read_text(encoding="utf-8")
        (pkg_dir / name).write_text(text, encoding="utf-8")
        (pkg_dir / name.replace(".md", ".txt")).write_text(text, encoding="utf-8")
        print(f"  Manual -> {pkg_dir / name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Empaquetar ZIP de entrega")
    parser.add_argument(
        "--suffix",
        default="",
        help="Sufijo opcional, ej. IALAB-v3.1 → AnonimizadorJudicial-NLP-IALAB-v3.1.zip",
    )
    args = parser.parse_args()

    pkg_dir = find_pkg_dir()
    verify_package(pkg_dir)
    print("Copiando manuales al paquete…")
    bundle_docs(pkg_dir)
    print("Copiando avisos legales y licencias…")
    bundle_compliance(pkg_dir)
    print("Verificando paquete portable…")
    verify_portable_compliance(pkg_dir)

    zip_base = pkg_dir.name + (f"-{args.suffix}" if args.suffix else "")
    zip_path = ROOT / "dist" / f"{zip_base}.zip"
    if zip_path.exists():
        zip_path.unlink()

    print(f"Comprimiendo {pkg_dir} …")
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", pkg_dir.parent, pkg_dir.name)

    size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"\nZIP listo para entregar:")
    print(f"  {zip_path}")
    print(f"  {size_mb:.1f} MB")
    launcher = "INICIAR.bat" if sys.platform == "win32" else "INICIAR.command"
    print(f"\nEntregá el ZIP. Descomprimen y ejecutan {launcher}.")


if __name__ == "__main__":
    main()
