"""Arranca WebView2 con sus funciones de red en segundo plano desactivadas.

La ventana solo muestra ``http://127.0.0.1``. Aun así, el motor de WebView2
abre por su cuenta conexiones a servidores de Microsoft (medido: ver
``docs/VERIFICACION_RED_WEBVIEW2.md``). Este módulo las corta en tres capas.

1. API documentadas por Microsoft ("Data and privacy in WebView2"):
   - ``CoreWebView2Settings.IsReputationCheckingRequired = False`` apaga
     SmartScreen, la comprobación de seguridad en línea.
   - ``CoreWebView2EnvironmentOptions.IsCustomCrashReportingEnabled = True``
     evita que los volcados de fallos se envíen a Microsoft.
   - Autocompletado y guardado de contraseñas, apagados.
2. ``--proxy-server`` (flag documentado en "WebView2 browser flags"): todo
   pedido HTTP/HTTPS que no sea a la propia máquina se deriva a un proxy
   inexistente y falla. Las direcciones de loopback no pasan por el proxy.
   Cubre todo lo que sale por la pila de red de Chromium, sirva o no el resto.
3. Flags de Chromium que evitan que esos pedidos siquiera se intenten
   (actualización de componentes, red en segundo plano, informes). Microsoft
   no los documenta y advierte que los flags pueden cambiar entre versiones;
   por eso son un complemento y no la garantía.

Lo que queda, medido: en aproximadamente la mitad de las corridas el proceso
principal de WebView2 abre una única conexión HTTPS a los servicios de
identidad de Microsoft 365 (certificado ``outlook.com`` / ``*.office.com``).
No pasa por la pila de red de Chromium, así que ni el proxy ni los flags la
alcanzan; ``--allow-browser-signin=false`` se probó y no la evita.

Lo que la aplicación NO puede controlar, según la documentación: los datos de
diagnóstico obligatorios de Windows (siguen la configuración del sistema) y
la actualización del runtime de WebView2, que hace el servicio Microsoft Edge
Update por fuera de este proceso.

Depende de detalles internos de pywebview 6.2.1 (clase ``EdgeChrome``). Si
alguno cambia, ``install`` lo registra y la ventana abre igual; las capas 2 y
3 no dependen de esos detalles.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Puerto "discard": no hay nada escuchando. Un pedido derivado ahí falla al
# instante sin salir del equipo.
BLACKHOLE_PROXY = "127.0.0.1:9"
ARGUMENTS_VARIABLE = "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"

DOCUMENTED_ARGUMENTS = (
    f"--proxy-server=http://{BLACKHOLE_PROXY}",
    "--proxy-bypass-list=127.0.0.1;localhost",
    "--no-first-run",
)
# Chromium; no documentados por Microsoft para WebView2.
CHROMIUM_ARGUMENTS = (
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-domain-reliability",
    "--disable-sync",
    "--disable-client-side-phishing-detection",
    "--disable-breakpad",
    "--no-pings",
)

# Qué capas quedaron aplicadas en este proceso (para diagnóstico y pruebas).
STATUS = {"arguments": False, "settings_hook": False, "custom_environment": False,
          "reputation_checking_off": False}


def browser_arguments() -> str:
    return " ".join(DOCUMENTED_ARGUMENTS + CHROMIUM_ARGUMENTS)


def apply_arguments(environ=os.environ) -> str:
    """Capas 2 y 3: WebView2 agrega esta variable a los argumentos del motor."""
    arguments = browser_arguments()
    environ[ARGUMENTS_VARIABLE] = arguments
    STATUS["arguments"] = True
    return arguments


def harden_settings(settings) -> None:
    """Capa 1, sobre ``CoreWebView2.Settings``, antes de la primera navegación."""
    settings.IsReputationCheckingRequired = False
    settings.IsPasswordAutosaveEnabled = False
    settings.IsGeneralAutofillEnabled = False
    STATUS["reputation_checking_off"] = True


def _hook_settings(edgechromium) -> None:
    original = edgechromium.EdgeChrome.on_webview_ready
    if getattr(original, "_anon_hardened", False):
        return

    def on_webview_ready(self, sender, args):
        try:
            if args.IsSuccess:
                harden_settings(sender.CoreWebView2.Settings)
        except Exception:  # noqa: BLE001 - la ventana debe abrir igual.
            logger.exception("No se pudieron aplicar los ajustes de privacidad de WebView2.")
        return original(self, sender, args)

    on_webview_ready._anon_hardened = True
    edgechromium.EdgeChrome.on_webview_ready = on_webview_ready
    STATUS["settings_hook"] = True


def _hook_environment(edgechromium) -> None:
    """Crea el entorno de WebView2 con el envío de volcados desactivado.

    pywebview crea el control con ``CoreWebView2CreationProperties``, que no
    expone esa opción. Se reemplaza el control por una subclase cuya
    inicialización arma el entorno con ``CoreWebView2EnvironmentOptions``.
    """
    base = edgechromium.WebView2
    if getattr(base, "_anon_hardened", False):
        return
    from Microsoft.Web.WebView2.Core import (
        CoreWebView2Environment,
        CoreWebView2EnvironmentOptions,
    )
    from System import Action
    from System.Threading.Tasks import Task, TaskScheduler
    from webview import _state

    class HardenedWebView2(base):
        __namespace__ = "AnonimizadorUsoPersonal"
        _anon_hardened = True

        def EnsureCoreWebView2Async(self, environment=None):  # noqa: N802 - nombre de .NET
            control = self
            try:
                properties = control.CreationProperties
                options = CoreWebView2EnvironmentOptions()
                options.AdditionalBrowserArguments = properties.AdditionalBrowserArguments
                options.IsCustomCrashReportingEnabled = True

                def ready(task):
                    try:
                        created = task.Result
                        controller = created.CreateCoreWebView2ControllerOptions()
                        controller.IsInPrivateModeEnabled = bool(_state["private_mode"])
                        base.EnsureCoreWebView2Async(control, created, controller)
                        STATUS["custom_environment"] = True
                    except Exception:  # noqa: BLE001
                        logger.exception("Entorno propio de WebView2 no disponible; se usa el estándar.")
                        base.EnsureCoreWebView2Async(control, None)

                CoreWebView2Environment.CreateAsync(
                    properties.BrowserExecutableFolder, properties.UserDataFolder, options,
                ).ContinueWith(Action[Task[CoreWebView2Environment]](ready),
                               TaskScheduler.FromCurrentSynchronizationContext())
            except Exception:  # noqa: BLE001
                logger.exception("Entorno propio de WebView2 no disponible; se usa el estándar.")
                base.EnsureCoreWebView2Async(control, None)

    edgechromium.WebView2 = HardenedWebView2


def install() -> dict:
    """Aplica las tres capas. Llamar antes de crear la ventana.

    Nunca lanza: si una capa no se puede aplicar, queda registrada en el log y
    en ``STATUS`` y la ventana abre con las demás.
    """
    apply_arguments()
    try:
        from webview.platforms import edgechromium
    except Exception:  # noqa: BLE001 - sin pywebview/.NET no hay ventana que ajustar.
        logger.exception("No se pudo cargar el motor de la ventana.")
        return dict(STATUS)
    for hook in (_hook_settings, _hook_environment):
        try:
            hook(edgechromium)
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo aplicar %s.", hook.__name__)
    return dict(STATUS)
