"""Copia avisos legales y licencias al paquete portable de entrega."""
from __future__ import annotations

import shutil
import json
from importlib.metadata import distributions
from pathlib import Path
from portable_docs import portable_text

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
                    if item.suffix == '.md':
                        target.write_text(portable_text(item.read_text(encoding='utf-8'), item,
                                                       Path(dirname) / rel), encoding='utf-8')
                    else:
                        shutil.copy2(item, target)
            print(f"  Legal -> {dest}/")

    for relpath in COMPLIANCE_DOCS:
        src = ROOT / relpath
        if src.is_file():
            text = portable_text(src.read_text(encoding='utf-8'), src, Path(src.name))
            dest_md = pkg_dir / src.name
            dest_md.write_text(text, encoding="utf-8")
            dest_txt = pkg_dir / f"{src.stem}.txt"
            dest_txt.write_text(text, encoding="utf-8")
            print(f"  Legal -> {dest_md}")

    inventory = []
    for distribution in sorted(distributions(), key=lambda item: (item.metadata.get('Name') or '').lower()):
        name = distribution.metadata.get('Name') or 'unknown'
        copied = []
        for item in distribution.files or ():
            if not (any(part.lower() in {'licenses', 'licences'} for part in item.parts)
                    or item.name.upper().startswith(('LICENSE', 'LICENCE', 'COPYING', 'NOTICE'))):
                continue
            source = Path(distribution.locate_file(item))
            if not source.is_file():
                continue
            destination = pkg_dir / 'LICENSES' / 'third_party' / name / str(item)
            if not destination.resolve().is_relative_to((pkg_dir / 'LICENSES/third_party').resolve()):
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            copied.append(destination.relative_to(pkg_dir).as_posix())
        inventory.append({'name': name, 'version': distribution.version,
                          'license_expression': distribution.metadata.get('License-Expression'),
                          'license_files': copied})
    (pkg_dir / 'LICENSES/INVENTARIO_BUILD.json').write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


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
