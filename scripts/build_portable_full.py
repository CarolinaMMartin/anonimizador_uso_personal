"""Construye paquete portable COMPLETO (Presidio + spaCy + modelo es_core_news_md).

Uso (desde la raíz del proyecto, con venv activo o .venv\\Scripts\\python):
  .venv\\Scripts\\python scripts\\install_nlp.py
  .venv\\Scripts\\python scripts\\build_portable_full.py
  .venv\\Scripts\\python scripts\\build_portable_full.py --zip   # incluir ZIP (solo si lo necesitás ya)

Salida:
  dist\\AnonimizadorJudicial-NLP\\   (carpeta para probar / instalar)
  dist\\AnonimizadorJudicial-NLP.zip (solo con --zip; si no, usá package_release.py)
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_NAME = "AnonimizadorJudicial-NLP"
SPACY_MODEL = "es_core_news_md"


def is_windows() -> bool:
    return sys.platform == "win32"


def is_mac() -> bool:
    return sys.platform == "darwin"


def default_stage_root() -> Path:
    if is_windows():
        return Path(r"C:\anon_build")
    return Path.home() / "anon_build"


# PyInstaller escribe miles de archivos durante el build. En Windows, si la carpeta
# destino está dentro de OneDrive, el sincronizador bloquea archivos a mitad de
# proceso. Por eso compilamos en una ruta local fuera de OneDrive (Windows) o en
# ~/anon_build (macOS) y al final copiamos el resultado a dist/.
STAGE_ROOT = Path(os.environ.get("ANON_BUILD_DIR", str(default_stage_root()))).resolve()


def run(cmd: list[str], **kwargs) -> None:
    print(">", " ".join(str(c) for c in cmd))
    subprocess.check_call(cmd, cwd=ROOT, **kwargs)


def robust_rmtree(path: Path, attempts: int = 5) -> None:
    """Borra un árbol tolerando bloqueos transitorios (OneDrive/antivirus)."""
    for i in range(attempts):
        if not path.exists():
            return
        shutil.rmtree(path, ignore_errors=(i < attempts - 1))
        if not path.exists():
            return
        time.sleep(2)
    if path.exists():
        raise SystemExit(f"No se pudo borrar {path} (cerrá OneDrive/antivirus).")


def robust_copytree(src: Path, dst: Path, attempts: int = 5) -> None:
    """Copia un árbol reintentando ante bloqueos transitorios."""
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            robust_rmtree(dst)
            shutil.copytree(src, dst)
            return
        except (PermissionError, OSError) as exc:  # noqa: PERF203
            last_exc = exc
            print(f"  Reintento copia ({i + 1}/{attempts}) tras: {exc}")
            time.sleep(3)
    raise SystemExit(f"No se pudo copiar a {dst}: {last_exc}")


def ensure_nlp() -> Path:
    """Verifica Presidio/spaCy y devuelve ruta del modelo."""
    if importlib.util.find_spec("spacy") is None:
        raise SystemExit(
            "spaCy no instalado. Ejecutá: .venv\\Scripts\\python scripts\\install_nlp.py"
        )
    import spacy

    try:
        spacy.load(SPACY_MODEL)
    except OSError:
        run([sys.executable, "-m", "spacy", "download", SPACY_MODEL])

    import spacy as sp

    nlp = sp.load(SPACY_MODEL)
    model_path = Path(nlp._path).resolve()
    if not (model_path / "config.cfg").exists():
        raise SystemExit(
            f"Modelo incompleto en {model_path}. Reinstalá: "
            f"{sys.executable} -m spacy download {SPACY_MODEL}"
        )
    if not (model_path / "LICENSE").is_file():
        raise SystemExit(
            f"Falta LICENSE (GPL-3.0) en {model_path}. "
            f"Reinstalá el modelo con: {sys.executable} -m spacy download {SPACY_MODEL}"
        )
    return model_path


def find_package_dir(stage_dist: Path) -> Path:
    """Ubica la carpeta o .app generada por PyInstaller."""
    expected = stage_dist / DIST_NAME
    app_bundle = stage_dist / f"{DIST_NAME}.app"
    if app_bundle.is_dir():
        return app_bundle
    if expected.is_dir():
        return expected
    raise SystemExit(f"No se generó paquete en {stage_dist}")


def find_launcher_binary(pkg_dir: Path) -> Path | None:
    """Ejecutable principal dentro del paquete (Windows .exe o binario Mac)."""
    if is_windows():
        exe = pkg_dir / f"{DIST_NAME}.exe"
        return exe if exe.exists() else None
    if pkg_dir.suffix == ".app":
        candidate = pkg_dir / "Contents" / "MacOS" / DIST_NAME
        return candidate if candidate.exists() else None
    candidate = pkg_dir / DIST_NAME
    return candidate if candidate.exists() else None


def build_onedir() -> Path:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    stage_dist = STAGE_ROOT / "dist"
    stage_work = STAGE_ROOT / "build"
    out_dir = stage_dist / DIST_NAME
    robust_rmtree(out_dir)
    robust_rmtree(stage_dist / f"{DIST_NAME}.app")
    robust_rmtree(stage_work)
    stage_dist.mkdir(parents=True, exist_ok=True)
    stage_work.mkdir(parents=True, exist_ok=True)
    # Limpiar spec viejo en STAGE para evitar reusar configuración previa.
    old_spec = STAGE_ROOT / f"{DIST_NAME}.spec"
    if old_spec.exists():
        old_spec.unlink()

    sep = ";" if sys.platform == "win32" else ":"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        DIST_NAME,
        "--onedir",
        "--windowed",
        "--noconfirm",
        f"--distpath={stage_dist}",
        f"--workpath={stage_work}",
        f"--specpath={STAGE_ROOT}",
        "--collect-all",
        "spacy",
        "--collect-all",
        "presidio_analyzer",
        "--collect-all",
        "presidio_anonymizer",
        "--collect-all",
        "thinc",
        "--collect-data",
        "tldextract",
        "--collect-submodules",
        "spacy",
        # Excluir módulos de tests/benchmarks que no se usan en runtime y
        # demoran enormemente la fase de Analysis (>1500 módulos extra).
        "--exclude-module",
        "thinc.tests",
        "--exclude-module",
        "thinc.benchmarks",
        "--exclude-module",
        "spacy.tests",
        "--exclude-module",
        "pytest",
        "--exclude-module",
        "hypothesis",
        # Excluir paquetes pesados que no usa la app (venv de desarrollo sucio)
        "--exclude-module",
        "cv2",
        "--exclude-module",
        "onnxruntime",
        "--exclude-module",
        "rapidocr_onnxruntime",
        "--add-data",
        f"{ROOT / 'frontend'}{sep}frontend",
        "--add-data",
        f"{ROOT / 'data' / 'dictionaries'}{sep}data/dictionaries",
        str(ROOT / "scripts" / "launcher.py"),
    ]
    run(cmd)

    pkg_dir = find_package_dir(stage_dist)
    if find_launcher_binary(pkg_dir) is None:
        raise SystemExit(f"No se encontró ejecutable en {pkg_dir}")
    return pkg_dir


def package_root(pkg_dir: Path) -> Path:
    """Carpeta de entrega (contiene .app, lanzadores, etc.)."""
    if is_mac() and pkg_dir.suffix == ".app":
        return pkg_dir.parent
    return pkg_dir


def runtime_dir(pkg_dir: Path) -> Path:
    """Directorio junto al ejecutable en runtime (para models/, frontend/)."""
    if is_mac() and pkg_dir.suffix == ".app":
        return pkg_dir / "Contents" / "MacOS"
    return pkg_dir


def copy_model(pkg_dir: Path, model_src: Path) -> None:
    dest = runtime_dir(pkg_dir) / "models" / SPACY_MODEL
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(model_src, dest)
    if not (dest / "LICENSE").is_file():
        raise SystemExit(
            f"El modelo copiado no incluye LICENSE (GPL-3.0): {dest / 'LICENSE'}"
        )
    print(f"Modelo copiado -> {dest}")


def copy_frontend_overlay(pkg_dir: Path) -> None:
    """Carpeta frontend/ junto al ejecutable: permite actualizar UI sin rebuild."""
    src = ROOT / "frontend"
    dest = runtime_dir(pkg_dir) / "frontend"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    print(f"Frontend overlay -> {dest}")


def write_launchers(pkg_dir: Path) -> None:
    deliver = package_root(pkg_dir)
    readme = deliver / "LEEME_INSTALACION.txt"

    if is_windows():
        exe_name = f"{DIST_NAME}.exe"
        (pkg_dir / "INICIAR.bat").write_text(
            f"""@echo off
title Anonimizador IALAB
cd /d "%~dp0"
taskkill /IM {exe_name} /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8787 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
echo Iniciando Anonimizador IALAB...
echo Abrira http://127.0.0.1:8787
start "" "{exe_name}"
""",
            encoding="ascii",
        )
        (pkg_dir / "VERIFICAR.bat").write_text(
            """@echo off
cd /d "%~dp0"
start "" "http://127.0.0.1:8787/health"
""",
            encoding="ascii",
        )
        readme.write_text(_readme_windows(), encoding="utf-8")
        return

    # macOS — lanzadores al lado del .app
    launcher = deliver / "INICIAR.command"
    if is_mac() and stage_pkg.suffix == ".app":
        open_line = f'open "{pkg_dir.name}"'
    elif (deliver / f"{DIST_NAME}.app").is_dir():
        open_line = f'open "{DIST_NAME}.app"'
    else:
        open_line = f'./"{DIST_NAME}"'

    launcher.write_text(
        f"""#!/bin/bash
cd "$(dirname "$0")"
lsof -ti:8787 | xargs kill -9 2>/dev/null || true
echo "Iniciando Anonimizador IALAB..."
echo "Abrí http://127.0.0.1:8787 si no se abre solo"
{open_line}
""",
        encoding="utf-8",
    )
    launcher.chmod(0o755)

    verificar = deliver / "VERIFICAR.command"
    verificar.write_text(
        """#!/bin/bash
open "http://127.0.0.1:8787/health"
""",
        encoding="utf-8",
    )
    verificar.chmod(0o755)
    readme.write_text(_readme_mac(), encoding="utf-8")


def _readme_windows() -> str:
    return """ANONIMIZADOR JUDICIAL — IALAB (Windows)
==============================================================

IMPORTANTE: NO hay que instalar Python, pip ni dependencias.
Solo descomprimir este ZIP y ejecutar INICIAR.bat.

Requisitos
----------
- Windows 10/11 (64 bits)
- NO requiere Python ni Internet para funcionar
- ~250–400 MB en disco

Instalación (3 pasos)
---------------------
1. Descomprimir el ZIP completo en una carpeta fija.
2. Doble clic en INICIAR.bat
3. Se abre el navegador en http://127.0.0.1:8787

Verificación: VERIFICAR.bat o /health (presidio y spacy en true).

Manuales: MANUAL_INSTALACION.md, MANUAL_USUARIO.md

Privacidad: todo local (127.0.0.1). Sin conexión a Internet requerida.

Licencias: LICENSE (código app), THIRD_PARTY_NOTICES.txt,
           models/es_core_news_md/LICENSE (modelo GPL-3.0)
"""


def _readme_mac() -> str:
    return """ANONIMIZADOR JUDICIAL — IALAB (macOS)
==============================================================

Requisitos
----------
- macOS 11+ (Intel o Apple Silicon)
- NO requiere Python ni Internet para funcionar
- ~250–400 MB en disco

Instalación
-----------
1. Descomprimir el ZIP completo.
2. Primera vez: clic derecho en INICIAR.command → Abrir (Gatekeeper).
   Si macOS lo bloquea: Preferencias → Privacidad → abrir igualmente.
3. Se abre el navegador en http://127.0.0.1:8787

Verificación: ejecutar VERIFICAR.command o abrir /health
- app_version indica la versión
- presidio.available y spacy.available: true

Uso
---
1. Cargar Word (.docx) o PDF digital
2. Analizar → Revisar → Verificar y exportar (Word/PDF)

Privacidad: todo local (127.0.0.1).
"""


def make_zip(pkg_dir: Path) -> Path:
    zip_path = ROOT / "dist" / f"{pkg_dir.name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", pkg_dir.parent, pkg_dir.name)
    return zip_path


def smoke_test_pkg(pkg_dir: Path | None = None) -> None:
    """Verifica NLP en build o en el paquete portable generado."""
    sys.path.insert(0, str(ROOT))
    if pkg_dir:
        candidates = [
            pkg_dir / "models" / SPACY_MODEL / "config.cfg",
            pkg_dir / f"{DIST_NAME}.app" / "Contents" / "MacOS" / "models" / SPACY_MODEL / "config.cfg",
        ]
        for cfg in candidates:
            if cfg.exists():
                print(f"Modelo empaquetado OK: {cfg.parent}")
                return
    from app.detection.nlp_status import get_nlp_layers_status

    status = get_nlp_layers_status()
    if not status["presidio"].get("available") or not status["spacy"].get("available"):
        raise SystemExit(f"NLP no disponible en build: {status}")
    print("NLP OK en entorno de build")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build portable NLP completo")
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Generar ZIP al terminar (por defecto no; usá package_release.py cuando esté listo)",
    )
    args = parser.parse_args()

    print("=== Build portable NLP completo ===\n")
    plat = "Windows" if is_windows() else "macOS" if is_mac() else sys.platform
    print(f"Plataforma: {plat}")
    if not is_windows() and not is_mac():
        raise SystemExit("Build portable soportado solo en Windows y macOS.")
    print(f"Staging: {STAGE_ROOT}")
    print("Verificando NLP en venv…")
    model_src = ensure_nlp()
    print(f"Modelo fuente: {model_src}")
    stage_pkg = build_onedir()
    copy_model(stage_pkg, model_src)
    copy_frontend_overlay(stage_pkg)
    smoke_test_pkg(stage_pkg)

    # En Mac: carpeta de entrega con .app + lanzadores.
    if is_mac() and stage_pkg.suffix == ".app":
        deliver = stage_pkg.parent / DIST_NAME
        robust_rmtree(deliver)
        deliver.mkdir(parents=True)
        shutil.move(str(stage_pkg), str(deliver / stage_pkg.name))
        stage_pkg = deliver

    write_launchers(stage_pkg)

    final_dir = ROOT / "dist" / DIST_NAME
    print(f"\nCopiando paquete a {final_dir} …")
    robust_copytree(stage_pkg, final_dir)

    sys.path.insert(0, str(ROOT / "scripts"))
    from bundle_compliance import bundle_compliance  # noqa: E402

    print("Copiando avisos legales y licencias…")
    bundle_compliance(final_dir)

    print(f"\nListo:")
    print(f"  Carpeta: {final_dir}")
    if args.zip:
        zip_path = make_zip(final_dir)
        size_mb = zip_path.stat().st_size / 1024 / 1024
        print(f"  ZIP:     {zip_path} ({size_mb:.1f} MB)")
    else:
        print("  ZIP:     (omitido)")
        print("           Cuando la versión esté lista para alumnos:")
        print("           .venv\\Scripts\\python scripts\\package_release.py --suffix IALAB-v3.1")
    print("\nPara probar cambios de interfaz sin rebuild: scripts\\sync_frontend.py")


if __name__ == "__main__":
    main()
