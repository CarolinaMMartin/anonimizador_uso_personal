"""Copia avisos legales y licencias al paquete portable de entrega."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Archivos/carpetas de cumplimiento en la raíz del repo
COMPLIANCE_FILES = (
    "LICENSE",
    "NOTICE",
    "THIRD_PARTY_NOTICES.txt",
)

COMPLIANCE_DIRS = (
    "LICENSES",
)

COMPLIANCE_DOCS = (
    "docs/COMPLIANCE.md",
)


def bundle_compliance(pkg_dir: Path) -> None:
    """Incluye licencias y avisos en la carpeta de entrega (junto al .exe)."""
    for name in COMPLIANCE_FILES:
        src = ROOT / name
        if src.is_file():
            shutil.copy2(src, pkg_dir / name)
            print(f"  Legal -> {pkg_dir / name}")

    for dirname in COMPLIANCE_DIRS:
        src = ROOT / dirname
        if src.is_dir():
            dest = pkg_dir / dirname
            dest.mkdir(parents=True, exist_ok=True)
            for item in src.rglob("*"):
                rel = item.relative_to(src)
                target = dest / rel
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)
            print(f"  Legal -> {dest}/")

    for relpath in COMPLIANCE_DOCS:
        src = ROOT / relpath
        if src.is_file():
            text = src.read_text(encoding="utf-8")
            dest_md = pkg_dir / src.name
            dest_md.write_text(text, encoding="utf-8")
            dest_txt = pkg_dir / f"{src.stem}.txt"
            dest_txt.write_text(text, encoding="utf-8")
            print(f"  Legal -> {dest_md}")


if __name__ == "__main__":
    import sys

    target = ROOT / "dist" / "AnonimizadorJudicial-NLP"
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    if not target.is_dir():
        raise SystemExit(f"No existe paquete: {target}")
    print(f"Empaquetando cumplimiento en {target}…")
    bundle_compliance(target)
    print("Listo.")
