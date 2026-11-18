"""Manifiesto MSIX: identidad de Partner Center, versión e íconos."""
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import make_msix_icons  # noqa: E402
import msix_manifest  # noqa: E402

from app.config import APP_VERSION  # noqa: E402

NS = msix_manifest.NS


def _png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"No es PNG: {path.name}"
    return struct.unpack(">II", header[16:24])


def test_store_version_has_four_parts_ending_in_zero():
    assert msix_manifest.store_version("3.4.4") == "3.4.4.0"
    assert msix_manifest.store_version("3.4.5") == "3.4.5.0"
    assert msix_manifest.store_version("10.0.12") == "10.0.12.0"


@pytest.mark.parametrize("version", ["3.4", "3.4.5.1", "3.4.5-rc1", "v3.4.5", "", "0.9.1", "3.70000.1"])
def test_versions_the_store_would_reject_stop_the_build(version):
    with pytest.raises(ValueError):
        msix_manifest.store_version(version)


def test_rendered_manifest_matches_partner_center_and_the_application_version():
    manifest = msix_manifest.render_manifest(APP_VERSION)
    assert msix_manifest.validate_manifest(manifest, APP_VERSION) == []
    root = ET.fromstring(manifest)
    identity = root.find("f:Identity", NS)
    assert identity.attrib == {
        "Name": "CarolinaMartin.Anonimizadordeusopersonal",
        "Publisher": "CN=54101CBA-F9F0-4A60-A1F4-FA1225FEC231",
        "Version": APP_VERSION + ".0",
        "ProcessorArchitecture": "x64",
    }
    assert root.findtext("f:Properties/f:PublisherDisplayName", namespaces=NS) == "Carolina Martin"
    assert root.findtext("f:Properties/f:DisplayName", namespaces=NS) == "Anonimizador de uso personal"
    family = root.find("f:Dependencies/f:TargetDeviceFamily", NS)
    assert family.get("Name") == "Windows.Desktop"
    application = root.find("f:Applications/f:Application", NS)
    assert application.get("EntryPoint") == "Windows.FullTrustApplication"
    assert application.get("Executable") == "AnonimizadorJudicial-NLP.exe"
    assert [item.get("Name") for item in root.findall("f:Capabilities/rescap:Capability", NS)] == ["runFullTrust"]
    assert root.find("f:Resources/f:Resource", NS).get("Language").startswith("es")
    assert "{{" not in manifest and "<!--" not in manifest


def test_template_keeps_the_version_as_a_placeholder():
    template = msix_manifest.TEMPLATE.read_text(encoding="utf-8")
    assert 'Version="{{VERSION}}"' in template
    assert APP_VERSION + ".0" not in template, "La versión se inyecta; no se escribe a mano"


@pytest.mark.parametrize("old, new, expected", [
    ("CarolinaMartin.Anonimizadordeusopersonal", "Otro.Nombre", "Identity/@Name"),
    ("CN=54101CBA-F9F0-4A60-A1F4-FA1225FEC231", "CN=Otro", "Identity/@Publisher"),
    ("<PublisherDisplayName>Carolina Martin<", "<PublisherDisplayName>Otra Persona<", "PublisherDisplayName"),
    ('ProcessorArchitecture="x64"', 'ProcessorArchitecture="x86"', "ProcessorArchitecture"),
    ('Name="Windows.Desktop"', 'Name="Windows.Universal"', "TargetDeviceFamily"),
    ("Windows.FullTrustApplication", "App.Main", "EntryPoint"),
    ('<rescap:Capability Name="runFullTrust" />', "", "runFullTrust"),
    ('Language="es-AR"', 'Language="en-US"', "español"),
])
def test_validation_reports_each_mismatch_with_partner_center(old, new, expected):
    manifest = msix_manifest.render_manifest(APP_VERSION)
    assert old in manifest
    errors = msix_manifest.validate_manifest(manifest.replace(old, new), APP_VERSION)
    assert any(expected in error for error in errors), errors


def test_validation_reports_a_stale_version_and_broken_xml():
    manifest = msix_manifest.render_manifest("3.4.4")
    errors = msix_manifest.validate_manifest(manifest, "3.4.5")
    assert len(errors) == 1 and "Identity/@Version" in errors[0]
    assert "XML válido" in msix_manifest.validate_manifest("<Package>", APP_VERSION)[0]


def test_every_logo_in_the_manifest_exists_with_the_documented_size():
    manifest = msix_manifest.render_manifest(APP_VERSION)
    expected = {"Assets/StoreLogo.png": 50, "Assets/Square150x150Logo.png": 150,
                "Assets/Square44x44Logo.png": 44}
    assert sorted(msix_manifest.logo_paths(manifest)) == sorted(expected)
    for relative, side in expected.items():
        path = msix_manifest.ASSETS_DIR.parent / relative
        assert path.is_file(), f"Falta {relative}"
        assert _png_size(path) == (side, side)


def test_icon_folder_holds_exactly_the_generated_set():
    expected = make_msix_icons.expected_assets()
    found = {path.name for path in msix_manifest.ASSETS_DIR.iterdir()}
    assert found == set(expected), "Regenerá con scripts/make_msix_icons.py"
    for name, side in expected.items():
        assert _png_size(msix_manifest.ASSETS_DIR / name) == (side, side), name
    # Variantes sin placa para la barra de tareas, en fondo oscuro y claro.
    for size in (16, 24, 32, 48, 256):
        assert f"Square44x44Logo.targetsize-{size}_altform-unplated.png" in expected
        assert f"Square44x44Logo.targetsize-{size}_altform-lightunplated.png" in expected


def test_icons_can_be_regenerated_from_the_brand_isotype(tmp_path):
    written = make_msix_icons.build(output=tmp_path / "Assets")
    assert {path.name for path in written} == set(make_msix_icons.expected_assets())
    from PIL import Image

    dark = Image.open(tmp_path / "Assets" / "Square44x44Logo.targetsize-48_altform-unplated.png")
    light = Image.open(tmp_path / "Assets" / "Square44x44Logo.targetsize-48_altform-lightunplated.png")
    assert dark.mode == light.mode == "RGBA"
    assert dark.getpixel((0, 0))[3] == 0, "Sin placa: el fondo es transparente"
    opaque_dark = max((color for _count, color in dark.getcolors(maxcolors=48 * 48)),
                      key=lambda pixel: pixel[3])
    opaque_light = max((color for _count, color in light.getcolors(maxcolors=48 * 48)),
                       key=lambda pixel: pixel[3])
    assert opaque_dark[:3] == (255, 255, 255), "Sobre fondo oscuro el isotipo va en blanco"
    assert sum(opaque_light[:3]) < 300, "Sobre fondo claro conserva el azul de la marca"
