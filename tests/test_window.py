"""Ventana propia: configuración de pywebview y caída al navegador."""
import sys
import types
from pathlib import Path

import pytest

from app import launcher, window

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def terminated(monkeypatch):
    """Ninguna prueba debe terminar de verdad el proceso de pytest."""
    codes = []
    monkeypatch.setattr(launcher, "terminate_process", lambda code=0: codes.append(code))
    return codes


class FakeWebview(types.ModuleType):
    """Registra cómo se configura pywebview sin abrir ninguna ventana."""

    def __init__(self, fail_before_shown=False):
        super().__init__("webview")
        self.settings = {"ALLOW_DOWNLOADS": False, "ALLOW_FILE_URLS": True,
                         "OPEN_EXTERNAL_LINKS_IN_BROWSER": False}
        self.created = []
        self.started = []
        self.fail_before_shown = fail_before_shown
        self._shown_handlers = []

    def create_window(self, title, url, **options):
        self.created.append((title, url, options))
        handlers = self._shown_handlers

        class Event:
            def __iadd__(self, handler):
                handlers.append(handler)
                return self

        return types.SimpleNamespace(events=types.SimpleNamespace(shown=Event()))

    def start(self, **options):
        self.started.append(options)
        if self.fail_before_shown:
            raise RuntimeError("motor no disponible")
        for handler in self._shown_handlers:
            handler()


def test_webview2_detection_requires_a_recent_runtime():
    assert window.webview2_available(["157.0.4341.60"]) is True
    assert window.webview2_available(["86.0.622.0"]) is True
    assert window.webview2_available(["85.0.564.40", "0.0.0.0"]) is False
    assert window.webview2_available(["", "no-es-version"]) is False
    assert window.webview2_available([]) is False


def test_window_enables_downloads_text_selection_and_private_storage(monkeypatch, tmp_path):
    fake = FakeWebview()
    monkeypatch.setitem(sys.modules, "webview", fake)
    monkeypatch.setattr(window, "webview2_available", lambda: True)

    assert window.run_window("http://127.0.0.1:8787", "Anonimizador de uso personal",
                             tmp_path / "webview") is True

    assert fake.settings["ALLOW_DOWNLOADS"] is True, "Sin esto no funcionan las exportaciones"
    assert fake.settings["ALLOW_FILE_URLS"] is False
    (title, url, options), = fake.created
    assert title == "Anonimizador de uso personal"
    assert url.startswith("http://127.0.0.1:")
    assert options["text_select"] is True
    assert options["confirm_close"] is True
    start, = fake.started
    assert start["gui"] == "edgechromium"
    assert start["private_mode"] is True
    assert Path(start["storage_path"]) == tmp_path / "webview"


def test_each_process_uses_its_own_temporary_folder(tmp_path):
    import os

    storage = window.process_storage_dir(tmp_path / "webview")
    assert storage == tmp_path / "webview" / str(os.getpid())


def test_leftovers_from_previous_processes_are_removed_before_opening(monkeypatch, tmp_path):
    root = tmp_path / "webview"
    storage = root / "4242"
    (root / "1111" / "EBWebView").mkdir(parents=True)
    (root / "1111" / "EBWebView" / "resto.bin").write_text("sesión anterior", encoding="utf-8")
    (root / "suelto.tmp").write_text("x", encoding="utf-8")
    fake = FakeWebview()
    seen_at_start = []
    original_start = fake.start

    def start(**options):
        seen_at_start.append(sorted(path.name for path in root.iterdir()))
        (storage / "EBWebView").mkdir(parents=True)
        (storage / "EBWebView" / "cache.bin").write_text("temporal", encoding="utf-8")
        original_start(**options)

    fake.start = start
    monkeypatch.setitem(sys.modules, "webview", fake)
    monkeypatch.setattr(window, "webview2_available", lambda: True)
    assert window.run_window("http://127.0.0.1:8787", "x", storage) is True
    assert seen_at_start == [[]], "Los restos anteriores se borran antes de abrir"
    assert (storage / "EBWebView" / "cache.bin").is_file(), "El borrado propio lo decide quien llama"

    assert window.clear_storage(storage, delay=0) is True
    assert not root.exists(), "Al cerrar no queda nada, tampoco la carpeta vacía"


def test_cleanup_keeps_the_folder_of_another_running_instance(tmp_path):
    root = tmp_path / "webview"
    mine, other = root / "1", root / "2"
    mine.mkdir(parents=True)
    (other / "EBWebView").mkdir(parents=True)
    assert window.clear_storage(mine, delay=0) is True
    assert (other / "EBWebView").is_dir()

    window.clear_stale_storage(tmp_path / "no-existe", tmp_path / "no-existe" / "1")  # no falla


def test_storage_cleanup_reports_what_it_could_not_remove(monkeypatch, tmp_path):
    storage = tmp_path / "webview" / "1"
    storage.mkdir(parents=True)
    monkeypatch.setattr(window.shutil, "rmtree", lambda path, ignore_errors=False: None)
    assert window.clear_storage(storage, attempts=2, delay=0) is False


def test_missing_webview2_falls_back_without_loading_the_engine(monkeypatch, tmp_path):
    fake = FakeWebview()
    monkeypatch.setitem(sys.modules, "webview", fake)
    monkeypatch.setattr(window, "webview2_available", lambda: False)
    assert window.run_window("http://127.0.0.1:8787", "x", tmp_path) is False
    assert fake.created == [] and fake.started == []


def test_engine_failure_before_showing_the_window_falls_back(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "webview", FakeWebview(fail_before_shown=True))
    monkeypatch.setattr(window, "webview2_available", lambda: True)
    assert window.run_window("http://127.0.0.1:8787", "x", tmp_path) is False


def test_missing_pywebview_falls_back(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "webview", None)  # import webview -> ImportError
    monkeypatch.setattr(window, "webview2_available", lambda: True)
    assert window.run_window("http://127.0.0.1:8787", "x", tmp_path) is False


class FakeServer:
    port = 8790

    def __init__(self):
        self.events = []

    def stop(self):
        self.events.append("stop")

    def join(self):
        self.events.append("join")


def test_closing_the_window_stops_the_server(monkeypatch, tmp_path, terminated):
    calls = []
    monkeypatch.setattr(window, "run_window", lambda url, title, storage: calls.append((url, title, storage)) or True)
    monkeypatch.setattr(launcher.runtime_paths, "user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(launcher.webbrowser, "open", lambda url: pytest.fail("no debe abrir el navegador"))
    server = FakeServer()
    monkeypatch.setattr(window, "clear_storage",
                        lambda storage, **options: server.events.append(("clear", storage)) or True)
    launcher.run_interface(server, "window")
    (url, title, storage), = calls
    assert url == "http://127.0.0.1:8790"
    assert title == "Anonimizador de uso personal"
    assert storage == window.process_storage_dir(tmp_path / "webview")
    assert server.events == ["stop", ("clear", storage)], \
        "Primero se libera el puerto; después se borran los temporales"
    assert terminated == [0], "El proceso termina sin esperar a los hilos del motor"


def test_process_termination_does_not_wait_for_engine_threads(monkeypatch):
    import app.launcher as real

    exits = []
    monkeypatch.undo()  # se prueba la función real, con os._exit simulado
    monkeypatch.setattr(real.os, "_exit", exits.append)
    monkeypatch.setattr(real.sys, "stdout", None)  # ejecutable sin consola
    real.terminate_process(0)
    assert exits == [0]


def test_window_failure_opens_the_browser_with_a_clear_message(monkeypatch, tmp_path, terminated):
    opened, messages = [], []
    monkeypatch.setattr(window, "run_window", lambda url, title, storage: False)
    monkeypatch.setattr(launcher.runtime_paths, "user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(launcher.webbrowser, "open", opened.append)
    monkeypatch.setattr(launcher, "notify_info", messages.append)
    server = FakeServer()
    launcher.run_interface(server, "window")
    assert server.events == ["join"], "El servidor sigue atendiendo al navegador"
    assert terminated == [], "En el navegador el proceso sigue vivo"
    assert len(opened) == 1 and opened[0].startswith("http://127.0.0.1:8790")
    assert len(messages) == 1 and "WebView2" in messages[0] and "navegador" in messages[0]


def test_headless_and_browser_modes_never_load_the_window(monkeypatch):
    monkeypatch.setattr(window, "run_window", lambda *args: pytest.fail("no debe abrir ventana"))
    opened = []
    monkeypatch.setattr(launcher.webbrowser, "open", opened.append)
    for mode, expected in (("none", 0), ("browser", 1)):
        opened.clear()
        server = FakeServer()
        launcher.run_interface(server, mode)
        assert server.events == ["join"] and len(opened) == expected


def test_interface_uses_the_store_product_name():
    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    assert "<title>Anonimizador de uso personal</title>" in html
    assert "<h1>Anonimizador de uso personal</h1>" in html
    assert launcher.APP_TITLE == "Anonimizador de uso personal"


def test_pywebview_is_pinned_for_windows_only():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    line = next(line for line in requirements.splitlines() if line.startswith("pywebview"))
    assert "==" in line and 'sys_platform == "win32"' in line
