"""Ventana propia: configuración de pywebview y caída al navegador."""
import sys
import types
from pathlib import Path

import pytest

from app import launcher, window

ROOT = Path(__file__).resolve().parent.parent


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


def test_engine_temporary_data_is_removed_before_and_after_the_window(monkeypatch, tmp_path):
    storage = tmp_path / "webview"
    (storage / "EBWebView").mkdir(parents=True)
    (storage / "EBWebView" / "resto.bin").write_text("sesión anterior", encoding="utf-8")
    fake = FakeWebview()
    seen_at_start = []
    original_start = fake.start

    def start(**options):
        seen_at_start.append(storage.exists())
        (storage / "EBWebView").mkdir(parents=True)
        (storage / "EBWebView" / "cache.bin").write_text("temporal", encoding="utf-8")
        original_start(**options)

    fake.start = start
    monkeypatch.setitem(sys.modules, "webview", fake)
    monkeypatch.setattr(window, "webview2_available", lambda: True)
    assert window.run_window("http://127.0.0.1:8787", "x", storage) is True
    assert seen_at_start == [False], "Los restos anteriores se borran antes de abrir"
    assert not storage.exists(), "Al cerrar no quedan datos temporales"


def test_storage_cleanup_reports_what_it_could_not_remove(monkeypatch, tmp_path):
    storage = tmp_path / "webview"
    storage.mkdir()
    assert window.clear_storage(storage) is True
    assert window.clear_storage(storage) is True  # ya no existe
    storage.mkdir()
    import shutil

    monkeypatch.setattr(shutil, "rmtree", lambda path, ignore_errors=False: None)
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


def test_closing_the_window_stops_the_server(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(window, "run_window", lambda url, title, storage: calls.append((url, title, storage)) or True)
    monkeypatch.setattr(launcher.runtime_paths, "user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(launcher.webbrowser, "open", lambda url: pytest.fail("no debe abrir el navegador"))
    server = FakeServer()
    launcher.run_interface(server, "window")
    assert server.events == ["stop"]
    (url, title, storage), = calls
    assert url == "http://127.0.0.1:8790"
    assert title == "Anonimizador de uso personal"
    assert storage == tmp_path / "webview"


def test_window_failure_opens_the_browser_with_a_clear_message(monkeypatch, tmp_path):
    opened, messages = [], []
    monkeypatch.setattr(window, "run_window", lambda url, title, storage: False)
    monkeypatch.setattr(launcher.runtime_paths, "user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(launcher.webbrowser, "open", opened.append)
    monkeypatch.setattr(launcher, "notify_info", messages.append)
    server = FakeServer()
    launcher.run_interface(server, "window")
    assert server.events == ["join"], "El servidor sigue atendiendo al navegador"
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
