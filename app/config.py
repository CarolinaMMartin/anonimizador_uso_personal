"""Configuración de la aplicación."""
import os
from pathlib import Path

from app.runtime_paths import app_dir, bundle_dir

HOST = "127.0.0.1"
PORT = 8787
APP_VERSION = "3.3.11"

# Recursos embebidos (frontend, diccionarios en el bundle)
BUNDLE_DIR = bundle_dir()


def _resolve_frontend_dir() -> Path:
    """Frontend: ANON_FRONTEND_DIR > carpeta junto al .exe > bundle embebido."""
    env = os.environ.get("ANON_FRONTEND_DIR", "").strip()
    if env:
        path = Path(env).expanduser().resolve()
        if (path / "index.html").exists():
            return path
    overlay = app_dir() / "frontend"
    if (overlay / "index.html").exists():
        return overlay
    return BUNDLE_DIR / "frontend"


FRONTEND_DIR = _resolve_frontend_dir()

# Recursos de datos SOLO LECTURA empaquetados (diccionarios, fórmulas).
# En el .exe viven dentro de _internal (BUNDLE_DIR), no junto al ejecutable.
RESOURCE_DATA_DIR = BUNDLE_DIR / "data"

# Datos persistentes junto al .exe (sesiones SQLite)
DATA_DIR = app_dir() / "data"
DB_PATH = DATA_DIR / "sessions.db"

# Límite de tamaño para documentos cargados (protege la memoria del proceso)
MAX_UPLOAD_BYTES = 40 * 1024 * 1024  # 40 MB

# Umbrales de similitud (RapidFuzz)
FUZZY_HIGH = 92
FUZZY_MEDIUM = 85
PROXIMITY_CHARS = 200

# Capas NLP activas
ENABLE_PRESIDIO = True
ENABLE_SPACY = True
