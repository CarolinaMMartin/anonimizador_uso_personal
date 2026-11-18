"""Arranque directo: instancia única, puerto libre y reutilización."""
import json
import os
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from app import launcher
from app.config import APP_VERSION, FRONTEND_DIR


def _health(port, **changes):
    payload = {"status": "ok", "port": port, "app_version": APP_VERSION,
               "frontend_dir": str(FRONTEND_DIR), "pid": 4321}
    payload.update(changes)
    return payload


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


# ── Archivo de puerto ─────────────────────────────────────────────────────

def test_port_file_round_trip_creates_the_data_folder(tmp_path):
    path = tmp_path / "datos" / "PUERTO_ACTUAL.txt"
    assert launcher.read_saved_port(path) is None
    assert launcher.write_port(path, 8790) is True
    assert path.read_text(encoding="ascii").strip() == "8790"
    assert launcher.read_saved_port(path) == 8790


@pytest.mark.parametrize("content", ["", "abc", "80", "8797", "8787 8788"])
def test_invalid_saved_port_is_ignored(tmp_path, content):
    path = tmp_path / "PUERTO_ACTUAL.txt"
    path.write_text(content, encoding="ascii")
    assert launcher.read_saved_port(path) is None


def test_unwritable_port_file_does_not_stop_the_start(tmp_path):
    blocker = tmp_path / "archivo"
    blocker.write_text("x", encoding="ascii")
    assert launcher.write_port(blocker / "PUERTO_ACTUAL.txt", 8787) is False


def test_saved_port_is_tried_first():
    assert launcher.candidate_ports(None) == list(range(8787, 8797))
    assert launcher.candidate_ports(8790)[:3] == [8790, 8787, 8788]
    assert sorted(launcher.candidate_ports(8790)) == list(range(8787, 8797))


# ── Reconocer una instancia propia ────────────────────────────────────────

def test_health_matches_only_this_version_folder_and_port(tmp_path):
    assert launcher.health_matches(_health(8787), 8787, APP_VERSION, FRONTEND_DIR)
    assert not launcher.health_matches(None, 8787, APP_VERSION, FRONTEND_DIR)
    assert not launcher.health_matches(_health(8787, status="error"), 8787, APP_VERSION, FRONTEND_DIR)
    assert not launcher.health_matches(_health(8787, app_version="0.0.1"), 8787, APP_VERSION, FRONTEND_DIR)
    assert not launcher.health_matches(_health(8788), 8787, APP_VERSION, FRONTEND_DIR)
    assert not launcher.health_matches(_health("x"), 8787, APP_VERSION, FRONTEND_DIR)
    assert not launcher.health_matches(
        _health(8787, frontend_dir=str(tmp_path)), 8787, APP_VERSION, FRONTEND_DIR)


@pytest.mark.skipif(sys.platform != "win32", reason="Rutas sin distinción de mayúsculas")
def test_folder_comparison_ignores_case_on_windows():
    health = _health(8787, frontend_dir=str(FRONTEND_DIR).upper())
    assert launcher.health_matches(health, 8787, APP_VERSION, FRONTEND_DIR)


def test_health_probe_reads_a_local_server_and_rejects_redirects():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.server.redirect:
                self.send_response(302)
                self.send_header("Location", "http://example.invalid/health")
                self.end_headers()
                return
            body = json.dumps({"status": "ok", "port": self.server.server_port}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.redirect = False
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_port
        assert launcher.fetch_health(port) == {"status": "ok", "port": port}
        server.redirect = True
        assert launcher.fetch_health(port) is None
    finally:
        server.shutdown()
        server.server_close()
    assert launcher.fetch_health(port, timeout=0.5) is None


def test_port_probe_detects_a_listening_socket():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen(1)
        assert launcher.is_port_free(busy.getsockname()[1]) is False
    assert launcher.is_port_free(_free_port()) is True


# ── Decisión ──────────────────────────────────────────────────────────────

def test_first_free_port_is_used_when_nothing_is_open():
    decision = launcher.decide([8787, 8788], is_free=lambda port: True,
                               find_instance=lambda port: pytest.fail("no debe consultarse"))
    assert decision == launcher.Decision("start", 8787)


def test_port_taken_by_another_application_is_skipped_untouched():
    decision = launcher.decide([8787, 8788, 8789], is_free=lambda port: port != 8787,
                               find_instance=lambda port: None)
    assert decision == launcher.Decision("start", 8788)


def test_existing_instance_is_reused_even_if_an_earlier_port_is_free():
    health = _health(8789)
    decision = launcher.decide([8787, 8788, 8789], is_free=lambda port: port != 8789,
                               find_instance=lambda port: health)
    assert decision == launcher.Decision("reuse", 8789, health)


def test_no_free_port_and_no_own_instance_reports_failure():
    assert launcher.decide([8787, 8788], is_free=lambda port: False,
                           find_instance=lambda port: None) is None


# ── Exclusión ─────────────────────────────────────────────────────────────

def test_lock_name_identifies_the_install_folder(tmp_path):
    first = launcher.lock_name(tmp_path / "a")
    assert first == launcher.lock_name(tmp_path / "a")
    assert first != launcher.lock_name(tmp_path / "b")
    assert first.startswith("Local\\AnonimizadorUsoPersonal-")


@pytest.mark.skipif(sys.platform != "win32", reason="Mutex con nombre de Windows")
def test_second_start_waits_while_the_first_one_holds_the_lock(tmp_path):
    name = launcher.lock_name(tmp_path)
    results = {}

    def contender():
        with launcher.InstanceLock(name, timeout=0.3) as lock:
            results["while_held"] = lock.acquired

    with launcher.InstanceLock(name) as lock:
        assert lock.acquired
        thread = threading.Thread(target=contender)
        thread.start()
        thread.join()
    assert results == {"while_held": False}
    with launcher.InstanceLock(name, timeout=0.3) as lock:
        assert lock.acquired


# ── Modo de interfaz y punto de entrada ───────────────────────────────────

def test_interface_mode(monkeypatch):
    monkeypatch.delenv("ANON_NO_BROWSER", raising=False)
    monkeypatch.delenv("ANON_WINDOW", raising=False)
    monkeypatch.setattr(launcher.runtime_paths, "is_packaged", lambda: False)
    assert launcher.interface_mode() == "browser"
    monkeypatch.setattr(launcher.runtime_paths, "is_packaged", lambda: True)
    assert launcher.interface_mode() == "window"
    monkeypatch.setattr(launcher.runtime_paths, "is_packaged", lambda: False)
    monkeypatch.setenv("ANON_WINDOW", "1")
    assert launcher.interface_mode() == "window"
    monkeypatch.setenv("ANON_NO_BROWSER", "1")
    assert launcher.interface_mode() == "none"


def test_port_chosen_by_the_portable_launcher_keeps_the_traditional_start(monkeypatch):
    import app.main

    calls = []
    monkeypatch.setenv("ANON_PORT", "8791")
    monkeypatch.setattr(app.main, "run_server", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(launcher, "start_or_reuse", lambda: pytest.fail("no debe elegir puerto"))
    assert launcher.direct_start_enabled() is False
    assert launcher.main() == 0
    assert calls == [{"open_browser": True}]


def test_direct_start_applies_on_windows_without_a_chosen_port(monkeypatch):
    monkeypatch.delenv("ANON_PORT", raising=False)
    monkeypatch.setattr(launcher.sys, "platform", "win32")
    assert launcher.direct_start_enabled() is True
    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    assert launcher.direct_start_enabled() is False


def test_reopening_shows_the_existing_instance(monkeypatch):
    opened, focused = [], []
    monkeypatch.setattr(launcher.webbrowser, "open", opened.append)
    decision = launcher.Decision("reuse", 8788, _health(8788))

    monkeypatch.setattr(launcher, "focus_process_window", lambda pid: focused.append(pid) or True)
    launcher.show_existing(decision, "window")
    assert focused == [4321] and opened == []

    # Sin ventana propia (instancia abierta en el navegador) se reabre la pestaña.
    monkeypatch.setattr(launcher, "focus_process_window", lambda pid: False)
    launcher.show_existing(decision, "browser")
    assert len(opened) == 1 and opened[0].startswith("http://127.0.0.1:8788")

    launcher.show_existing(decision, "none")
    assert len(opened) == 1


# ── Flujo completo con el servidor real ───────────────────────────────────

def test_start_then_second_launch_reuses_the_running_instance(monkeypatch, tmp_path):
    import app.config
    import app.main

    port = _free_port()
    monkeypatch.setenv("ANON_NO_BROWSER", "1")
    monkeypatch.setenv("ANON_PORT", os.environ.get("ANON_PORT", ""))
    monkeypatch.setattr(app.config, "PORT", app.config.PORT)
    monkeypatch.setattr(app.main, "PORT", app.main.PORT)
    monkeypatch.setattr(launcher, "PORT_RANGE", range(port, port + 1))
    monkeypatch.setattr(launcher.runtime_paths, "port_file",
                        lambda: tmp_path / "datos" / "PUERTO_ACTUAL.txt")
    monkeypatch.setattr(launcher, "lock_name", lambda: f"Local\\prueba-{port}")
    started = []
    monkeypatch.setattr(launcher, "run_interface", lambda server, mode: started.append(server))
    shown = []
    monkeypatch.setattr(launcher, "show_existing", lambda decision, mode: shown.append(decision))

    assert launcher.start_or_reuse() == 0
    assert len(started) == 1
    server = started[0]
    try:
        health = launcher.fetch_health(port)
        assert health["port"] == port and health["pid"] == os.getpid()
        assert (tmp_path / "datos" / "PUERTO_ACTUAL.txt").read_text(encoding="ascii").strip() == str(port)

        # Segundo arranque: no crea otro servidor, muestra el existente.
        assert launcher.start_or_reuse() == 0
        assert len(started) == 1
        assert [d.action for d in shown] == ["reuse"] and shown[0].port == port
    finally:
        server.stop()
    assert not server.is_alive()
    assert launcher.is_port_free(port)


def test_no_available_port_reports_an_error_without_starting(monkeypatch, tmp_path):
    messages = []
    monkeypatch.setenv("ANON_NO_BROWSER", "1")
    monkeypatch.setattr(launcher.runtime_paths, "port_file", lambda: tmp_path / "PUERTO_ACTUAL.txt")
    monkeypatch.setattr(launcher, "lock_name", lambda: f"Local\\prueba-sin-puerto-{os.getpid()}")
    monkeypatch.setattr(launcher, "is_port_free", lambda port: False)
    monkeypatch.setattr(launcher, "fetch_health", lambda port: None)
    monkeypatch.setattr(launcher, "notify_error", lambda message, mode: messages.append((message, mode)))
    monkeypatch.setattr(launcher, "ServerThread", lambda port: pytest.fail("no debe iniciar"))
    assert launcher.start_or_reuse() == 1
    assert len(messages) == 1 and "8787 y 8796" in messages[0][0] and messages[0][1] == "none"
    assert not (tmp_path / "PUERTO_ACTUAL.txt").exists()


def test_entry_script_delegates_to_the_tested_module():
    source = (Path(__file__).resolve().parent.parent / "scripts/launcher.py").read_text(encoding="utf-8")
    assert "from app.launcher import main" in source
