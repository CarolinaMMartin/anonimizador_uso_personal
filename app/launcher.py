"""Arranque directo del ejecutable: instancia única, puerto libre y reutilización.

Un paquete de Microsoft Store inicia el ``.exe`` sin pasar por
``scripts/windows/iniciar.ps1``. Este módulo resuelve en Python lo mismo que
ese script: serializa los arranques simultáneos, busca un puerto libre entre
8787 y 8796 y, si ya hay una instancia de la misma versión y carpeta, la trae
al frente en lugar de iniciar otra.

Cuando ``ANON_PORT`` ya viene definido (``iniciar.ps1``, verificaciones de CI,
desarrollo) el puerto lo eligió quien lanzó el proceso y se conserva el
arranque tradicional de ``app.main.run_server``.

Este módulo no importa ``app.main`` al cargarse: el puerto se decide antes de
construir la aplicación.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from app import runtime_paths

HOST = "127.0.0.1"
PORT_RANGE = range(8787, 8797)
APP_TITLE = "Anonimizador de uso personal"
LOCK_TIMEOUT_SECONDS = 65
READY_TIMEOUT_SECONDS = 60
HEALTH_TIMEOUT_SECONDS = 1.5


# ── Puerto ────────────────────────────────────────────────────────────────

def read_saved_port(path: Path) -> int | None:
    """Puerto de la última instancia, si el archivo existe y es válido."""
    try:
        port = int(path.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return None
    return port if port in PORT_RANGE else None


def write_port(path: Path, port: int) -> bool:
    """Anota el puerto en la carpeta de datos. Un fallo no impide el inicio."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{port}\n", encoding="ascii")
    except OSError:
        return False
    return True


def candidate_ports(saved: int | None) -> list[int]:
    """El puerto guardado se prueba primero; después, el rango en orden."""
    ports = list(PORT_RANGE)
    if saved in PORT_RANGE:
        ports.remove(saved)
        ports.insert(0, saved)
    return ports


def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if sys.platform == "win32":
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            probe.bind((HOST, port))
        except OSError:
            return False
    return True


# ── Instancia existente ───────────────────────────────────────────────────

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D401
        return None


def fetch_health(port: int, timeout: float = HEALTH_TIMEOUT_SECONDS) -> dict | None:
    """Consulta ``/health`` en loopback, sin proxy ni redirecciones."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)
    try:
        with opener.open(f"http://{HOST}:{port}/health", timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return None
    return payload if isinstance(payload, dict) else None


def _same_folder(left: str, right: Path) -> bool:
    try:
        return os.path.normcase(str(Path(left).resolve())) == os.path.normcase(str(right.resolve()))
    except (OSError, ValueError):
        return False


def health_matches(health: dict | None, port: int, version: str, frontend_dir: Path) -> bool:
    """La instancia es de esta versión, de esta carpeta y atiende ese puerto."""
    if not health or health.get("status") != "ok":
        return False
    try:
        same_port = int(health.get("port")) == port
    except (TypeError, ValueError):
        return False
    return (same_port and health.get("app_version") == version
            and _same_folder(str(health.get("frontend_dir", "")), frontend_dir))


@dataclass(frozen=True)
class Decision:
    action: str  # "reuse" | "start"
    port: int
    health: dict | None = None


def decide(ports: Iterable[int], *, is_free: Callable[[int], bool],
           find_instance: Callable[[int], dict | None]) -> Decision | None:
    """Reutiliza una instancia propia si existe; si no, elige el primer puerto libre.

    Un puerto ocupado por otra aplicación u otra versión se saltea sin tocarlo.
    Devuelve ``None`` cuando no hay instancia propia ni puerto libre.
    """
    free_port = None
    for port in ports:
        if is_free(port):
            if free_port is None:
                free_port = port
            continue
        health = find_instance(port)
        if health is not None:
            return Decision("reuse", port, health)
    return None if free_port is None else Decision("start", free_port)


# ── Exclusión entre arranques simultáneos ─────────────────────────────────

def lock_name(folder: Path | None = None) -> str:
    folder = runtime_paths.app_dir() if folder is None else folder
    key = hashlib.sha256(os.path.normcase(str(folder)).encode("utf-8")).hexdigest()
    return f"Local\\AnonimizadorUsoPersonal-{key}"


class InstanceLock:
    """Mutex con nombre de Windows; fuera de Windows no hace nada.

    El mutex pertenece al hilo que lo toma: entrar y salir del bloque ``with``
    debe ocurrir en el mismo hilo.
    """

    _WAIT_OBJECT_0 = 0x0
    _WAIT_ABANDONED = 0x80

    def __init__(self, name: str, timeout: float = LOCK_TIMEOUT_SECONDS):
        self.name = name
        self.timeout = timeout
        self.acquired = False
        self._handle = None
        self._kernel32 = None

    def __enter__(self) -> "InstanceLock":
        if sys.platform != "win32":
            self.acquired = True
            return self
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel32 = kernel32
        self._handle = kernel32.CreateMutexW(None, False, self.name)
        if not self._handle:
            return self
        result = kernel32.WaitForSingleObject(self._handle, int(self.timeout * 1000))
        # Un mutex abandonado por un proceso que terminó también queda tomado.
        self.acquired = result in (self._WAIT_OBJECT_0, self._WAIT_ABANDONED)
        return self

    def __exit__(self, *exc) -> None:
        if self._kernel32 is None:
            self.acquired = False
            return
        if self._handle:
            if self.acquired:
                self._kernel32.ReleaseMutex(self._handle)
            self._kernel32.CloseHandle(self._handle)
        self._handle = None
        self.acquired = False


# ── Ventana de una instancia existente ────────────────────────────────────

def focus_process_window(pid: int) -> bool:
    """Trae al frente la ventana visible del proceso indicado (solo Windows)."""
    if sys.platform != "win32" or not pid:
        return False
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    found: list[int] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]

    def visit(hwnd, _lparam):
        owner = wintypes.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if (owner.value == pid and user32.IsWindowVisible(hwnd)
                and user32.GetWindowTextLengthW(hwnd) > 0):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(callback_type(visit), 0)
    if not found:
        return False
    hwnd = found[0]
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    return True


# ── Interfaz ──────────────────────────────────────────────────────────────

def interface_mode() -> str:
    """``none`` (verificaciones), ``window`` (Store) o ``browser`` (portable)."""
    if os.environ.get("ANON_NO_BROWSER") == "1":
        return "none"
    if os.environ.get("ANON_WINDOW") == "1" or runtime_paths.is_packaged():
        return "window"
    return "browser"


def app_url(port: int, cache_bust: bool = True) -> str:
    url = f"http://{HOST}:{port}"
    return f"{url}?_{int(time.time())}" if cache_bust else url


def notify_error(message: str, mode: str) -> None:
    """Informa un error de inicio. Sin interfaz no se abre ningún diálogo."""
    print(message, file=sys.stderr, flush=True)
    if mode == "none" or sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, APP_TITLE, 0x10)  # MB_ICONERROR
    except (AttributeError, OSError):
        pass


def show_existing(decision: Decision, mode: str) -> None:
    """Muestra la instancia ya abierta: su ventana o, si no tiene, el navegador."""
    if mode == "none":
        return
    pid = (decision.health or {}).get("pid")
    if isinstance(pid, int) and focus_process_window(pid):
        return
    webbrowser.open(app_url(decision.port))


# ── Servidor ──────────────────────────────────────────────────────────────

class ServerThread:
    """Uvicorn en un hilo, para que el hilo principal maneje la interfaz."""

    def __init__(self, port: int):
        import uvicorn

        os.environ["ANON_PORT"] = str(port)
        from app import config

        config.PORT = port
        from app import main as main_module

        main_module.PORT = port
        main_module.ensure_std_streams()
        self.port = port
        self._server = uvicorn.Server(
            uvicorn.Config(main_module.app, host=HOST, port=port, log_level="info"))
        self._thread = threading.Thread(target=self._server.run, name="uvicorn", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def wait_until_ready(self, timeout: float = READY_TIMEOUT_SECONDS) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.is_alive():
                return False
            health = fetch_health(self.port)
            if health and health.get("status") == "ok":
                return True
            time.sleep(0.2)
        return False

    def stop(self, timeout: float = 10) -> None:
        self._server.should_exit = True
        self._thread.join(timeout)

    def join(self) -> None:
        while self._thread.is_alive():
            self._thread.join(0.5)


WEBVIEW_FALLBACK_MESSAGE = (
    "No se pudo abrir la ventana de la aplicación porque falta Microsoft Edge "
    "WebView2 o no responde.\n\nLa aplicación se abre en tu navegador. Sigue "
    "funcionando en este equipo, sin conexión.\n\nCerrar la pestaña no la "
    "detiene: para cerrarla del todo, finalizá «Anonimizador de uso personal» "
    "desde el Administrador de tareas."
)


def notify_info(message: str) -> None:
    print(message, file=sys.stderr, flush=True)
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, APP_TITLE, 0x40)  # MB_ICONINFORMATION
    except (AttributeError, OSError):
        pass


def run_interface(server: ServerThread, mode: str) -> None:
    """Presenta la aplicación y espera hasta que corresponda terminar.

    Con ventana propia, cerrarla detiene el servidor y termina el proceso.
    En el navegador el proceso sigue vivo, como en el portable.
    """
    if mode == "window":
        from app import window

        shown = window.run_window(app_url(server.port, cache_bust=False), APP_TITLE,
                                  runtime_paths.user_data_dir() / "webview")
        if shown:
            server.stop()
            return
        notify_info(WEBVIEW_FALLBACK_MESSAGE)
        mode = "browser"
    if mode == "browser":
        webbrowser.open(app_url(server.port))
    server.join()


# ── Punto de entrada ──────────────────────────────────────────────────────

def direct_start_enabled() -> bool:
    """El arranque directo aplica en Windows cuando nadie eligió el puerto."""
    return sys.platform == "win32" and not os.environ.get("ANON_PORT", "").strip()


def start_or_reuse() -> int:
    from app import config

    mode = interface_mode()
    port_path = runtime_paths.port_file()
    with InstanceLock(lock_name()) as lock:
        if not lock.acquired:
            notify_error("La aplicación todavía está iniciando. Esperá unos segundos "
                         "y volvé a abrirla.", mode)
            return 1

        def find_instance(port: int) -> dict | None:
            health = fetch_health(port)
            return health if health_matches(
                health, port, config.APP_VERSION, config.FRONTEND_DIR) else None

        decision = decide(candidate_ports(read_saved_port(port_path)),
                          is_free=is_port_free, find_instance=find_instance)
        if decision is None:
            notify_error("No hay un puerto libre entre 8787 y 8796. Cerrá alguna de las "
                         "aplicaciones abiertas y volvé a intentar.", mode)
            return 1
        if decision.action == "reuse":
            write_port(port_path, decision.port)
            show_existing(decision, mode)
            return 0
        server = ServerThread(decision.port)
        server.start()
        if not server.wait_until_ready():
            server.stop()
            notify_error("La aplicación no pudo iniciar. Si el problema continúa, "
                         "reinstalala.", mode)
            return 1
        write_port(port_path, decision.port)
    run_interface(server, mode)
    return 0


def main() -> int:
    if direct_start_enabled():
        return start_or_reuse()
    from app.main import run_server

    run_server(open_browser=True)
    return 0
