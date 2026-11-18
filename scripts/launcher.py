"""Entry point para PyInstaller.

La lógica de arranque (instancia única, puerto libre, reutilización) vive en
``app/launcher.py`` para poder probarla sin compilar el ejecutable.
"""
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    ROOT = Path(sys._MEIPASS)
else:
    ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))

from app.launcher import main

if __name__ == "__main__":
    raise SystemExit(main())
