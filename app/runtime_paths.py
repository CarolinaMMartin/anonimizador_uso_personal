"""Rutas en desarrollo vs ejecutable empaquetado (PyInstaller)."""
import sys
from pathlib import Path

SPACY_MODEL_NAME = "es_core_news_md"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Carpeta del .exe (datos persistentes: sesiones, logs)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundle_dir() -> Path:
    """Recursos embebidos (_MEIPASS o raíz del proyecto)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", app_dir()))
    return Path(__file__).resolve().parent.parent


def spacy_model_dir() -> Path | None:
    """Ruta al modelo empaquetado en portable (carpeta models/ junto al .exe)."""
    for base in (app_dir(), bundle_dir()):
        candidate = base / "models" / SPACY_MODEL_NAME
        if (candidate / "meta.json").exists() and (candidate / "config.cfg").exists():
            return candidate
    return None
