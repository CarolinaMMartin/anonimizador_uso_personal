"""Ejecutar servidor de desarrollo."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from app.main import run_server

if __name__ == "__main__":
    from app.config import FRONTEND_DIR

    print(f"Directorio de trabajo: {ROOT}")
    print(f"Frontend servido desde: {FRONTEND_DIR}")
    print("Servidor: http://127.0.0.1:8787")
    run_server(open_browser=True)
