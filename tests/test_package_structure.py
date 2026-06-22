"""Verifica que el paquete portable contenga los archivos obligatorios.

El paquete no se versiona en Git: se construye con
``scripts/build_portable_full.py``. Por eso, si no hay un paquete
construido, el test se omite (skip). Cuando el paquete existe, el test
**falla** si falta cualquiera de los elementos obligatorios para la
entrega (ejecutable, launcher, manuales, licencias, modelo, frontend).

Para apuntar a un paquete en otra ubicación:
    ANON_PKG_DIR=/ruta/al/paquete python -m pytest tests/test_package_structure.py
"""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DIST_NAME = "AnonimizadorJudicial-NLP"
SPACY_MODEL = "es_core_news_md"


def _find_pkg_dir() -> Path | None:
    env = os.environ.get("ANON_PKG_DIR", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        return p if p.is_dir() else None
    for name in (DIST_NAME, f"{DIST_NAME}.app"):
        candidate = ROOT / "dist" / name
        if candidate.is_dir():
            return candidate
    return None


def _runtime_dir(pkg_dir: Path) -> Path:
    """Carpeta junto al ejecutable (en macOS, dentro del .app)."""
    if pkg_dir.suffix == ".app":
        return pkg_dir / "Contents" / "MacOS"
    return pkg_dir


def _has_any(*paths: Path) -> bool:
    return any(p.exists() for p in paths)


pkg_dir = _find_pkg_dir()

requires_package = pytest.mark.skipif(
    pkg_dir is None,
    reason=(
        "No hay paquete portable construido en dist/. "
        "Generá uno con scripts/build_portable_full.py o definí ANON_PKG_DIR."
    ),
)


@requires_package
def test_executable_present():
    rt = _runtime_dir(pkg_dir)
    assert _has_any(rt / f"{DIST_NAME}.exe", rt / DIST_NAME), "Falta el ejecutable principal"


@requires_package
def test_launcher_present():
    assert _has_any(
        pkg_dir / "INICIAR.bat",
        pkg_dir / "INICIAR.command",
        pkg_dir.parent / "INICIAR.bat",
        pkg_dir.parent / "INICIAR.command",
    ), "Falta el launcher (INICIAR.bat / INICIAR.command)"


@requires_package
def test_manuals_present():
    assert _has_any(
        pkg_dir / "MANUAL_INSTALACION.md", pkg_dir / "MANUAL_INSTALACION.txt"
    ), "Falta MANUAL_INSTALACION"
    assert _has_any(
        pkg_dir / "MANUAL_USUARIO.md", pkg_dir / "MANUAL_USUARIO.txt"
    ), "Falta MANUAL_USUARIO"


@requires_package
def test_licenses_present():
    assert (pkg_dir / "LICENSE").is_file(), "Falta LICENSE"
    assert (pkg_dir / "NOTICE").is_file(), "Falta NOTICE"
    assert (pkg_dir / "THIRD_PARTY_NOTICES.txt").is_file(), "Falta THIRD_PARTY_NOTICES.txt"
    assert (pkg_dir / "LICENSES").is_dir(), "Falta la carpeta LICENSES/"


@requires_package
def test_model_present():
    model = _runtime_dir(pkg_dir) / "models" / SPACY_MODEL
    assert model.is_dir(), "Falta el modelo es_core_news_md"
    assert (model / "LICENSE").is_file(), "Falta LICENSE (GPL-3.0) del modelo"


@requires_package
def test_frontend_present():
    assert (_runtime_dir(pkg_dir) / "frontend").is_dir(), "Falta la carpeta frontend/"
