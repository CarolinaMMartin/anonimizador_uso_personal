"""Copia frontend/ del proyecto al portable en dist (sin rebuild completo).

Uso:
  .venv\\Scripts\\python scripts\\sync_frontend.py

Actualiza:
  - dist\\AnonimizadorJudicial-NLP\\frontend\\          (prioridad al ejecutar .exe)
  - dist\\AnonimizadorJudicial-NLP\\_internal\\frontend\\
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend"
DIST_PKG = ROOT / "dist" / "AnonimizadorJudicial-NLP"


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"  OK -> {dst}")


def main() -> None:
    if not SRC.is_dir():
        raise SystemExit(f"No existe {SRC}")
    if not DIST_PKG.is_dir():
        raise SystemExit(
            f"No existe {DIST_PKG}. Ejecutá build_portable_full.py al menos una vez."
        )

    print(f"Sincronizando {SRC} …")
    targets = [
        DIST_PKG / "frontend",
        DIST_PKG / "_internal" / "frontend",
    ]
    for target in targets:
        copy_tree(SRC, target)

    print("\nListo. Reiniciá el .exe portable y abrí /health (app_version + frontend_dir).")


if __name__ == "__main__":
    main()
