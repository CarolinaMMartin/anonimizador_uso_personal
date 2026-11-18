"""WebView2 sin red en segundo plano: argumentos, ajustes y tolerancia a fallos.

El efecto real (ninguna conexión saliente) no se puede comprobar en una prueba
unitaria: se midió en una máquina real y está en
``docs/VERIFICACION_RED_WEBVIEW2.md``.
"""
import sys
import types
from pathlib import Path

import pytest

from app import webview_hardening as hardening
from app import window

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def clean_status(monkeypatch):
    monkeypatch.setattr(hardening, "STATUS", dict.fromkeys(hardening.STATUS, False))
    monkeypatch.delenv(hardening.ARGUMENTS_VARIABLE, raising=False)


def test_non_local_requests_are_sent_to_a_proxy_that_does_not_exist():
    arguments = hardening.browser_arguments().split()
    assert "--proxy-server=http://127.0.0.1:9" in arguments
    # La propia máquina no pasa por el proxy: si no, la interfaz no cargaría.
    assert "--proxy-bypass-list=127.0.0.1;localhost" in arguments
    assert not [a for a in arguments if "<-loopback>" in a], "No quitar la excepción de loopback"


def test_background_features_are_disabled_at_start():
    arguments = hardening.browser_arguments().split()
    for flag in ("--disable-background-networking", "--disable-component-update",
                 "--disable-domain-reliability", "--disable-sync", "--disable-breakpad",
                 "--disable-client-side-phishing-detection", "--no-pings", "--no-first-run"):
        assert flag in arguments
    assert len(arguments) == len(set(arguments))
    # Ningún flag habilita depuración remota ni relaja la seguridad del motor.
    assert not [a for a in arguments if "remote-debugging" in a or "disable-web-security" in a
                or "allow-" in a]


def test_arguments_reach_webview2_through_its_documented_variable():
    environ = {}
    assert hardening.apply_arguments(environ) == hardening.browser_arguments()
    assert environ == {"WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS": hardening.browser_arguments()}
    assert hardening.STATUS["arguments"] is True


def test_online_security_checks_and_autofill_are_turned_off():
    settings = types.SimpleNamespace(IsReputationCheckingRequired=True,
                                     IsPasswordAutosaveEnabled=True,
                                     IsGeneralAutofillEnabled=True)
    hardening.harden_settings(settings)
    assert settings.IsReputationCheckingRequired is False
    assert settings.IsPasswordAutosaveEnabled is False
    assert settings.IsGeneralAutofillEnabled is False


class FakeEdgeChrome:
    calls = []

    def on_webview_ready(self, sender, args):
        FakeEdgeChrome.calls.append(("original", sender.CoreWebView2.Settings.IsReputationCheckingRequired))


def _sender():
    settings = types.SimpleNamespace(IsReputationCheckingRequired=True,
                                     IsPasswordAutosaveEnabled=True, IsGeneralAutofillEnabled=True)
    return types.SimpleNamespace(CoreWebView2=types.SimpleNamespace(Settings=settings))


def test_settings_are_applied_before_pywebview_starts_the_first_navigation(monkeypatch):
    FakeEdgeChrome.calls = []
    module = types.SimpleNamespace(EdgeChrome=type("EdgeChrome", (FakeEdgeChrome,), {}))
    hardening._hook_settings(module)
    hardening._hook_settings(module)  # instalar dos veces no envuelve dos veces
    module.EdgeChrome().on_webview_ready(_sender(), types.SimpleNamespace(IsSuccess=True))
    assert FakeEdgeChrome.calls == [("original", False)], \
        "Cuando pywebview navega, SmartScreen ya está apagado"


def test_failed_engine_initialization_is_left_to_pywebview():
    FakeEdgeChrome.calls = []
    module = types.SimpleNamespace(EdgeChrome=type("EdgeChrome", (FakeEdgeChrome,), {}))
    hardening._hook_settings(module)
    module.EdgeChrome().on_webview_ready(_sender(), types.SimpleNamespace(IsSuccess=False))
    assert FakeEdgeChrome.calls == [("original", True)]


def test_a_layer_that_cannot_be_applied_does_not_stop_the_window(monkeypatch):
    fake = types.ModuleType("webview.platforms.edgechromium")  # sin EdgeChrome ni WebView2
    monkeypatch.setitem(sys.modules, "webview", types.ModuleType("webview"))
    monkeypatch.setitem(sys.modules, "webview.platforms", types.ModuleType("webview.platforms"))
    monkeypatch.setitem(sys.modules, "webview.platforms.edgechromium", fake)
    sys.modules["webview.platforms"].edgechromium = fake
    status = hardening.install()
    assert status["arguments"] is True, "El proxy y los flags no dependen de pywebview"
    assert status["settings_hook"] is False and status["custom_environment"] is False


def test_missing_engine_still_applies_the_arguments(monkeypatch):
    monkeypatch.setitem(sys.modules, "webview", None)
    monkeypatch.setitem(sys.modules, "webview.platforms", None)
    assert hardening.install()["arguments"] is True


def test_window_installs_the_hardening_before_creating_the_engine(monkeypatch, tmp_path):
    order = []
    fake = types.ModuleType("webview")
    fake.settings = {}
    fake.create_window = lambda *args, **kwargs: (
        order.append("create_window"),
        types.SimpleNamespace(events=types.SimpleNamespace(shown=_Event())))[1]
    fake.start = lambda **options: order.append("start")
    monkeypatch.setitem(sys.modules, "webview", fake)
    monkeypatch.setattr(window, "webview2_available", lambda: True)
    monkeypatch.setattr(hardening, "install", lambda: order.append("hardening"))
    window.run_window("http://127.0.0.1:8787", "x", tmp_path / "webview" / "1")
    assert order == ["hardening", "create_window", "start"]


class _Event:
    def __iadd__(self, handler):
        return self


@pytest.mark.skipif(sys.platform != "win32", reason="pywebview solo se instala en Windows")
def test_pywebview_internals_this_module_relies_on_still_exist():
    """Si pywebview cambia estos nombres, las capas de API dejan de aplicarse."""
    import importlib.util

    spec = importlib.util.find_spec("webview")
    if spec is None:
        pytest.skip("pywebview no está instalado")
    text = (Path(spec.origin).parent / "platforms" / "edgechromium.py").read_text(encoding="utf-8")
    assert "class EdgeChrome" in text
    assert "def on_webview_ready(self, sender, args)" in text
    assert "self.webview = WebView2()" in text
    assert "self.webview.EnsureCoreWebView2Async(None)" in text
    assert "props.UserDataFolder = cache_dir" in text


def test_measurement_is_documented():
    report = (ROOT / "docs" / "VERIFICACION_RED_WEBVIEW2.md").read_text(encoding="utf-8")
    assert "127.0.0.1:9" in report and "IsReputationCheckingRequired" in report
