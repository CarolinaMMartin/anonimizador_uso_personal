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


def _opaque_colours(path):
    from PIL import Image

    image = Image.open(path)
    assert image.mode == "RGBA"
    assert image.getpixel((0, 0))[3] == 0, "Sin placa: el fondo es transparente"
    return {colour[:3] for _count, colour in image.getcolors(maxcolors=image.width * image.height)
            if colour[3] == 255}


def test_committed_icons_come_from_the_application_logo(tmp_path):
    assert make_msix_icons.SOURCE == ROOT / "packaging" / "app.ico"
    written = make_msix_icons.build(output=tmp_path / "Assets")
    assert {path.name for path in written} == set(make_msix_icons.expected_assets())
    from PIL import Image, ImageChops

    for path in written:
        # Se comparan píxeles, no bytes: la compresión PNG varía entre plataformas.
        committed = Image.open(msix_manifest.ASSETS_DIR / path.name).convert("RGBA")
        generated = Image.open(path).convert("RGBA")
        assert committed.size == generated.size
        difference = max(high for _low, high in ImageChops.difference(committed, generated).getextrema())
        assert difference <= 3, \
            f"{path.name} no coincide con packaging/app.ico: regenerá con scripts/make_msix_icons.py"


def test_multicolour_logo_keeps_its_colours_on_dark_and_light_backgrounds(tmp_path):
    make_msix_icons.build(output=tmp_path / "Assets")
    dark = _opaque_colours(tmp_path / "Assets" / "Square44x44Logo.targetsize-48_altform-unplated.png")
    light = _opaque_colours(tmp_path / "Assets" / "Square44x44Logo.targetsize-48_altform-lightunplated.png")
    assert dark == light and len(dark) > 1, "No se aplana a un solo color"


def test_single_colour_logo_turns_white_for_dark_backgrounds(tmp_path):
    from PIL import Image, ImageDraw

    source = tmp_path / "silueta.png"
    image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse((16, 16, 112, 112), fill=(2, 50, 87, 255))
    image.save(source)
    make_msix_icons.build(source=source, output=tmp_path / "Assets")
    dark = _opaque_colours(tmp_path / "Assets" / "Square44x44Logo.targetsize-48_altform-unplated.png")
    light = _opaque_colours(tmp_path / "Assets" / "Square44x44Logo.targetsize-48_altform-lightunplated.png")
    assert dark == {(255, 255, 255)}, "Sobre fondo oscuro la silueta va en blanco"
    assert (2, 50, 87) in light and all(r < 60 and b > r and r + g + b < 300 for r, g, b in light), \
        "Sobre fondo claro conserva su color"


def test_small_icons_use_the_versions_drawn_for_small_sizes():
    marks = make_msix_icons.load_marks(make_msix_icons.SOURCE)
    assert len(marks) >= 5 and [m.size for m in marks] == sorted(m.size for m in marks)
    assert max(max(m.size) for m in marks) >= 200, "Alcanza para 256 px sin agrandar de más"


def test_logo_without_transparent_background_is_rejected(tmp_path):
    from PIL import Image

    source = tmp_path / "opaco.png"
    Image.new("RGBA", (64, 64), (255, 255, 255, 255)).save(source)
    with pytest.raises(SystemExit):
        make_msix_icons.build(source=source, output=tmp_path / "Assets")
