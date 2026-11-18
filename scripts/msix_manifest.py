"""Manifiesto MSIX: versión de cuatro partes, plantilla y validación.

La identidad es la del producto reservado en Partner Center. Tiene que
coincidir exactamente con el manifiesto o la Store rechaza el paquete.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "packaging" / "msix" / "AppxManifest.xml"
ASSETS_DIR = ROOT / "packaging" / "msix" / "Assets"
EXECUTABLE = "AnonimizadorJudicial-NLP.exe"

IDENTITY_NAME = "CarolinaMartin.Anonimizadordeusopersonal"
IDENTITY_PUBLISHER = "CN=54101CBA-F9F0-4A60-A1F4-FA1225FEC231"
PUBLISHER_DISPLAY_NAME = "Carolina Martin"
DISPLAY_NAME = "Anonimizador de uso personal"
ARCHITECTURE = "x64"
DEVICE_FAMILY = "Windows.Desktop"
ENTRY_POINT = "Windows.FullTrustApplication"
LANGUAGE_PREFIX = "es"

NS = {
    "f": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
    "uap": "http://schemas.microsoft.com/appx/manifest/uap/windows10",
    "rescap": "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities",
}


def store_version(app_version: str) -> str:
    """``3.4.5`` -> ``3.4.5.0``. La Store reserva la cuarta parte y exige ``0``."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", app_version):
        raise ValueError(
            f"APP_VERSION debe tener tres partes numéricas para el paquete de Store: {app_version!r}")
    parts = [int(part) for part in app_version.split(".")]
    if parts[0] == 0:
        raise ValueError("La Store no admite versiones cuya primera parte sea 0.")
    if any(part > 65535 for part in parts):
        raise ValueError(f"Cada parte de la versión debe ser menor o igual a 65535: {app_version}")
    return ".".join(str(part) for part in parts) + ".0"


def render_manifest(app_version: str, template: Path = TEMPLATE) -> str:
    """Devuelve el manifiesto con la versión inyectada."""
    text = template.read_text(encoding="utf-8")
    if text.count("{{VERSION}}") != 2:  # una en el comentario, una en Identity
        raise ValueError("La plantilla debe usar {{VERSION}} solo en Identity/@Version.")
    # El comentario explicativo de la plantilla no viaja en el paquete.
    text = re.sub(r"<!--.*?-->\s*", "", text, count=1, flags=re.S)
    rendered = text.replace("{{VERSION}}", store_version(app_version))
    if "{{" in rendered:
        raise ValueError("Quedaron marcadores sin reemplazar en el manifiesto.")
    return rendered


def logo_paths(manifest_xml: str) -> list[str]:
    """Rutas de imagen que el manifiesto referencia, con ``/`` como separador."""
    root = ET.fromstring(manifest_xml)
    paths = [root.findtext("f:Properties/f:Logo", default="", namespaces=NS)]
    visual = root.find("f:Applications/f:Application/uap:VisualElements", NS)
    if visual is not None:
        paths += [visual.get("Square150x150Logo", ""), visual.get("Square44x44Logo", "")]
    return [path.replace("\\", "/") for path in paths if path]


def validate_manifest(manifest_xml: str, app_version: str) -> list[str]:
    """Errores del manifiesto respecto de Partner Center y de esta versión."""
    try:
        root = ET.fromstring(manifest_xml)
    except ET.ParseError as exc:
        return [f"El manifiesto no es XML válido: {exc}"]
    errors: list[str] = []

    def expect(label: str, found, expected) -> None:
        if found != expected:
            errors.append(f"{label}: se esperaba {expected!r} y el manifiesto tiene {found!r}")

    identity = root.find("f:Identity", NS)
    if identity is None:
        return ["Falta el elemento Identity."]
    expect("Identity/@Name", identity.get("Name"), IDENTITY_NAME)
    expect("Identity/@Publisher", identity.get("Publisher"), IDENTITY_PUBLISHER)
    expect("Identity/@Version", identity.get("Version"), store_version(app_version))
    expect("Identity/@ProcessorArchitecture", identity.get("ProcessorArchitecture"), ARCHITECTURE)
    expect("Properties/DisplayName",
           root.findtext("f:Properties/f:DisplayName", namespaces=NS), DISPLAY_NAME)
    expect("Properties/PublisherDisplayName",
           root.findtext("f:Properties/f:PublisherDisplayName", namespaces=NS),
           PUBLISHER_DISPLAY_NAME)

    languages = [item.get("Language", "") for item in root.findall("f:Resources/f:Resource", NS)]
    if not languages or not languages[0].lower().split("-")[0] == LANGUAGE_PREFIX:
        errors.append(f"El idioma principal del recurso debe ser español: {languages}")

    families = [item.get("Name") for item in root.findall("f:Dependencies/f:TargetDeviceFamily", NS)]
    expect("TargetDeviceFamily/@Name", families, [DEVICE_FAMILY])

    capabilities = [item.get("Name") for item in root.findall("f:Capabilities/rescap:Capability", NS)]
    if "runFullTrust" not in capabilities:
        errors.append("Falta la capacidad restringida runFullTrust.")

    applications = root.findall("f:Applications/f:Application", NS)
    if len(applications) != 1:
        errors.append(f"Debe haber exactamente una aplicación: {len(applications)}")
    else:
        application = applications[0]
        expect("Application/@Executable", application.get("Executable"), EXECUTABLE)
        expect("Application/@EntryPoint", application.get("EntryPoint"), ENTRY_POINT)
        visual = application.find("uap:VisualElements", NS)
        if visual is None:
            errors.append("Falta uap:VisualElements.")
        else:
            expect("VisualElements/@DisplayName", visual.get("DisplayName"), DISPLAY_NAME)
            for attribute in ("Description", "BackgroundColor", "Square150x150Logo", "Square44x44Logo"):
                if not visual.get(attribute):
                    errors.append(f"Falta VisualElements/@{attribute}.")
    return errors
