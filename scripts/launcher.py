"""Entry point para PyInstaller."""
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    ROOT = Path(sys._MEIPASS)
else:
    ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))

from app.main import run_server

if __name__ == "__main__":
    run_server(open_browser=True)
