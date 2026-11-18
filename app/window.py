"""Ventana propia de la aplicación (pywebview sobre Microsoft Edge WebView2).

Se usa en el paquete de Microsoft Store. El frontend sigue sirviéndose desde
``127.0.0.1``; la ventana solo lo muestra. Si WebView2 o pywebview no están
disponibles, ``run_window`` devuelve ``False`` y quien llama abre el navegador.

Este módulo no importa ``webview`` al cargarse: en el portable y en las
pruebas de Linux/macOS no hace falta tenerlo instalado.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

WINDOW_SIZE = (1280, 860)
WINDOW_MIN_SIZE = (960, 640)
MIN_WEBVIEW2_BUILD = (86, 0, 622, 0)
# Identificadores con los que el instalador de Edge registra cada canal de
# WebView2. El primero es el runtime estable que trae Windows 11.
_WEBVIEW2_CLIENTS = (
    "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
    "{2CD8A007-E189-409D-A2C8-9AF4EF3C72AA}",
    "{0D50BFEC-CD6A-4F9A-964C-C7416E3ACB10}",
    "{65C35B14-6C1D-4122-AC46-7148CC9D6497}",
)
LOCALIZATION = {
    "global.quitConfirmation": (
        "Al cerrar la ventana se termina la aplicación y se descarta el documento "
        "en revisión. ¿Querés cerrarla?"
    ),
    "global.ok": "Aceptar",
    "global.quit": "Cerrar",
    "global.cancel": "Cancelar",
    "global.saveFile": "Guardar archivo",
    "windows.fileFilter.allFiles": "Todos los archivos",
}


def parse_build(value: object) -> tuple[int, ...]:
    """``"157.0.4341.60"`` → ``(157, 0, 4341, 60)``; un valor inválido → ``()``."""
    try:
        return tuple(int(part) for part in str(value).strip().split("."))
    except ValueError:
        return ()


def _registered_builds() -> list[str]:
    """Versiones de WebView2 anotadas en el registro (solo Windows)."""
    if sys.platform != "win32":
        return []
    import winreg

    builds = []
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for client in _WEBVIEW2_CLIENTS:
            for prefix in (r"SOFTWARE\WOW6432Node", "SOFTWARE"):
                try:
                    with winreg.OpenKey(
                            hive, rf"{prefix}\Microsoft\EdgeUpdate\Clients\{client}") as key:
                        builds.append(str(winreg.QueryValueEx(key, "pv")[0]))
                except OSError:
                    continue
    return builds


def webview2_available(builds: list[str] | None = None) -> bool:
    """True si hay un runtime de WebView2 suficientemente nuevo instalado."""
    builds = _registered_builds() if builds is None else builds
    return any(parse_build(build) >= MIN_WEBVIEW2_BUILD for build in builds)


def clear_storage(storage_dir: Path, attempts: int = 10, delay: float = 0.3) -> bool:
    """Borra los datos temporales del motor de la ventana.

    pywebview intenta borrarlos al cerrar, pero los procesos de WebView2
    pueden tardar en soltar los archivos. Se reintenta unos segundos y, si
    queda algo, se limpia en el próximo inicio. Devuelve True si no quedó nada.
    """
    import shutil
    import time

    for attempt in range(attempts):
        shutil.rmtree(storage_dir, ignore_errors=True)
        if not storage_dir.exists():
            return True
        if attempt < attempts - 1:
            time.sleep(delay)
    return False


def run_window(url: str, title: str, storage_dir: Path) -> bool:
    """Muestra ``url`` en una ventana propia y espera a que se cierre.

    Devuelve ``True`` si la ventana se mostró (y ya fue cerrada) y ``False``
    si no pudo crearse, para que quien llama use el navegador.
    Debe ejecutarse en el hilo principal.
    """
    if not webview2_available():
        logger.warning("Microsoft Edge WebView2 no está instalado.")
        return False
    try:
        import webview
    except Exception:  # noqa: BLE001 - falta pywebview o .NET: se usa el navegador.
        logger.exception("No se pudo cargar pywebview.")
        return False

    shown = False

    def on_shown():
        nonlocal shown
        shown = True

    # Restos de un cierre abrupto anterior.
    clear_storage(storage_dir, attempts=1)
    try:
        # En pywebview las descargas vienen deshabilitadas; las exportaciones
        # (Word, PDF, CSV, Markdown) son descargas de un blob.
        webview.settings["ALLOW_DOWNLOADS"] = True
        webview.settings["ALLOW_FILE_URLS"] = False
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
        window = webview.create_window(
            title, url,
            width=WINDOW_SIZE[0], height=WINDOW_SIZE[1], min_size=WINDOW_MIN_SIZE,
            text_select=True,      # la revisión manual selecciona texto
            zoomable=True,
            confirm_close=True,    # la sesión vive solo en memoria
            localization=LOCALIZATION,
        )
        window.events.shown += on_shown
        # Modo privado: sin cookies ni almacenamiento persistentes. Los datos
        # temporales del motor quedan en la carpeta de datos del usuario y se
        # borran al cerrar.
        webview.start(gui="edgechromium", private_mode=True, storage_path=str(storage_dir),
                      localization=LOCALIZATION)
    except Exception:  # noqa: BLE001 - cualquier fallo del motor deriva al navegador.
        logger.exception("No se pudo abrir la ventana propia.")
        clear_storage(storage_dir)
        return shown
    clear_storage(storage_dir)
    return True
