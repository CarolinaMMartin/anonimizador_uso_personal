# -*- mode: python ; coding: utf-8 -*-
"""Referencia de compilación del ejecutable con PyInstaller.

En la práctica el build se hace con `scripts/build_portable_full.py`,
que arma su propia spec vía flags de línea de comandos para garantizar
paths reproducibles entre máquinas. Esta spec se conserva como
**referencia legible**. No produce por sí sola una entrega completa:
para incluir modelo, lanzadores, manuales y licencias usar el constructor.

Rutas relativas a `SPECPATH` para que el archivo sea portable.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH)
APP_NAME = "AnonimizadorJudicial-NLP"

datas = [
    (str(ROOT / "frontend"), "frontend"),
    (str(ROOT / "data" / "dictionaries"), "data/dictionaries"),
]
binaries = []
hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
]

for pkg in ("spacy", "presidio_analyzer", "presidio_anonymizer", "thinc"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(
        pkg, include_py_files=False,
        filter_submodules=lambda name: not name.startswith((f'{pkg}.tests', f'{pkg}.benchmarks')),
        exclude_datas=['**/tests/**', '**/benchmarks/**'],
    )
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

a = Analysis(
    [str(ROOT / "scripts" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(ROOT / 'scripts/pyinstaller_hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "thinc.tests",
        "thinc.benchmarks",
        "spacy.tests",
        "pytest",
        "hypothesis",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
