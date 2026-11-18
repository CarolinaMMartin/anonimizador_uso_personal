"""Rutas en desarrollo vs ejecutable empaquetado (PyInstaller / MSIX)."""
import os
import sys
from pathlib import Path

SPACY_MODEL_NAME = "es_core_news_md"
USER_DATA_DIRNAME = "AnonimizadorUsoPersonal"
PORT_FILENAME = "PUERTO_ACTUAL.txt"

# GetCurrentPackageFullName devuelve este código cuando el proceso no tiene
# identidad de paquete (portable, desarrollo).
_APPMODEL_ERROR_NO_PACKAGE = 15700


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def is_packaged() -> bool:
    """True si el proceso corre con identidad de paquete MSIX (Microsoft Store)."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        length = ctypes.c_uint32(0)
        result = ctypes.windll.kernel32.GetCurrentPackageFullName(
            ctypes.byref(length), None
        )
    except (AttributeError, OSError):
        return False
    return result != _APPMODEL_ERROR_NO_PACKAGE


def app_dir() -> Path:
    """Carpeta del .exe. En un paquete de Store es de solo lectura."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def user_data_dir() -> Path:
    """Carpeta para todo lo que la aplicación escribe (puerto, estado, logs).

    - ``ANON_DATA_DIR`` la fija de forma explícita.
    - Con identidad de paquete (MSIX) siempre es ``%LOCALAPPDATA%``: la carpeta
      de instalación es de solo lectura.
    - En portable y desarrollo se conserva la carpeta del ejecutable, que es
      donde ``iniciar.ps1`` y las verificaciones buscan ``PUERTO_ACTUAL.txt``.

    No crea la carpeta: quien escribe la crea en ese momento.
    """
    env = os.environ.get("ANON_DATA_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    if is_packaged():
        base = os.environ.get("LOCALAPPDATA", "").strip()
        root = Path(base) if base else Path.home() / "AppData" / "Local"
        return root / USER_DATA_DIRNAME
    return app_dir()


def port_file() -> Path:
    """Archivo donde el lanzador anota el puerto de la instancia abierta."""
    return user_data_dir() / PORT_FILENAME


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
