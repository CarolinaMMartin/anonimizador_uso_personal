"""Estructura del paquete MSIX para Microsoft Store.

Igual que ``test_package_structure.py``, las pruebas sobre el paquete real se
omiten si todavía no se construyó (``scripts/build_msix.py``). Con
``ANON_REQUIRE_MSIX=1`` (CI) la ausencia del paquete es una falla.

Para apuntar a otra ubicación:
    ANON_MSIX_DIR=/ruta/a/la/carpeta   ANON_MSIX=/ruta/al/archivo.msix
"""
import os
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_msix  # noqa: E402
import msix_manifest  # noqa: E402

from app.config import APP_VERSION  # noqa: E402

EXE = "AnonimizadorJudicial-NLP.exe"


def _write(root: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


@pytest.fixture
def portable(tmp_path):
    """Portable mínimo con lo que entrega build_portable_full.py."""
    root = tmp_path / "portable"
    _write(root, {
        EXE: "binary",
        "_internal/base_library.zip": "runtime",
        "_internal/data/dictionaries/nombres.json": "[]",
        "_internal/docx/templates/default.docx": "wheel-template",
        "_internal/docx/templates/default-docx-template/[Content_Types].xml": "opc",
        "_internal/docx/templates/default-docx-template/_rels/.rels": "relationships",
        "frontend/index.html": "<html></html>",
        "frontend/app.js": "",
        "models/es_core_news_md/config.cfg": "[nlp]",
        "models/es_core_news_md/LICENSE": "GNU GENERAL PUBLIC LICENSE",
        "LICENSES/MIT.txt": "MIT",
        "LICENSES/third_party/pkg/LICENSE": "license",
        "LICENSE": "license", "NOTICE": "notice", "THIRD_PARTY_NOTICES.txt": "notices",
        "COMPLIANCE.md": "compliance", "MANUAL_USUARIO.md": "manual", "CHANGELOG.md": "changes",
        "BUILD_PROVENANCE.json": "{}", "DEPENDENCIAS_BUILD.txt": "deps",
        # Lo que NO debe viajar en el paquete de Store:
        "INICIAR.bat": "start", "VERIFICAR.bat": "verify", "iniciar.ps1": "launcher",
        "VERSION_APP.txt": APP_VERSION, "PUERTO_ACTUAL.txt": "8787",
        "LEEME_INSTALACION.txt": "Ejecutar INICIAR.bat", "MANUAL_INSTALACION.md": "zip",
        "_internal/tools/activate.ps1": "script", "_internal/tools/run.cmd": "script",
        "Manuales/Resumen_ejecutivo.pdf": "archivo ajeno al repositorio",
        "Manuales/privado.pdf": "archivo personal",
        "frontend/export.docx": "documento del usuario",
        "_internal/docx/templates/privado.docx": "documento del usuario",
        "frontend/equivalencias.csv": "datos personales",
        "data/sessions.db": "sessions", "_internal/debug.log": "log",
        "_internal/__pycache__/x.pyc": "cache", "exports/salida.pdf": "export",
    })
    return root


@pytest.fixture
def layout(portable, tmp_path):
    target = tmp_path / "layout"
    trusted = {"_internal/docx/templates/default.docx":
               portable / "_internal/docx/templates/default.docx"}
    skipped = build_msix.stage_layout(portable, target, version=APP_VERSION,
                                      trusted_resources=trusted)
    return target, skipped


def _files(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def test_layout_contains_the_application_and_leaves_portable_scripts_out(layout):
    target, skipped = layout
    files = _files(target)
    for required in (EXE, "AppxManifest.xml", "_internal/base_library.zip",
                     "_internal/data/dictionaries/nombres.json", "frontend/index.html",
                     "models/es_core_news_md/config.cfg", "models/es_core_news_md/LICENSE",
                     "LICENSES/MIT.txt", "LICENSES/third_party/pkg/LICENSE", "LICENSE", "NOTICE",
                     "THIRD_PARTY_NOTICES.txt", "Assets/StoreLogo.png",
                     "Assets/Square44x44Logo.targetsize-24_altform-unplated.png",
                     "_internal/docx/templates/default.docx"):
        assert required in files, f"Falta {required}"
    assert not [name for name in files if name.lower().endswith((".bat", ".ps1", ".cmd"))]
    for excluded in ("VERSION_APP.txt", "PUERTO_ACTUAL.txt", "LEEME_INSTALACION.txt",
                     "MANUAL_INSTALACION.md", "frontend/export.docx", "frontend/equivalencias.csv",
                     "_internal/docx/templates/privado.docx", "data/sessions.db",
                     "_internal/debug.log", "_internal/__pycache__/x.pyc", "exports/salida.pdf"):
        assert excluded not in files, f"No debe empaquetarse {excluded}"
    assert {"_internal/tools/activate.ps1", "_internal/tools/run.cmd", "frontend/export.docx",
            "_internal/docx/templates/privado.docx"} <= set(skipped)
    assert not (target / "_internal/docx/templates/default-docx-template").exists()
    assert not (target / "Manuales/privado.pdf").exists()
    for name in build_msix.PDF_MANUALS:
        assert (target / "Manuales" / name).read_bytes() == (ROOT / "docs/manuales" / name).read_bytes()
    assert build_msix.verify_layout(target, APP_VERSION) == []


def test_layout_manifest_is_valid_and_matches_the_application_version(layout):
    target, _ = layout
    manifest = (target / "AppxManifest.xml").read_text(encoding="utf-8")
    assert msix_manifest.validate_manifest(manifest, APP_VERSION) == []
    assert f'Version="{APP_VERSION}.0"' in manifest
    assert 'Name="CarolinaMartin.Anonimizadordeusopersonal"' in manifest
    assert 'Publisher="CN=54101CBA-F9F0-4A60-A1F4-FA1225FEC231"' in manifest
    for logo in msix_manifest.logo_paths(manifest):
        assert (target / logo).is_file()


def test_portable_folder_is_left_untouched(portable, layout):
    assert (portable / "INICIAR.bat").is_file() and (portable / "iniciar.ps1").is_file()
    assert (portable / "VERSION_APP.txt").read_text(encoding="utf-8") == APP_VERSION
    assert not (portable / "AppxManifest.xml").exists()


def test_layout_verification_reports_scripts_missing_files_and_stale_versions(layout):
    target, _ = layout
    (target / "INICIAR.bat").write_text("start", encoding="utf-8")
    (target / "_internal" / "hook.ps1").write_text("x", encoding="utf-8")
    (target / "Assets" / "StoreLogo.png").unlink()
    (target / "models" / "es_core_news_md" / "LICENSE").unlink()
    errors = build_msix.verify_layout(target, APP_VERSION)
    assert "Archivo que no debe empaquetarse: INICIAR.bat" in errors
    assert "Archivo que no debe empaquetarse: _internal/hook.ps1" in errors
    assert "El manifiesto referencia un ícono inexistente: Assets/StoreLogo.png" in errors
    assert "Falta models/es_core_news_md/LICENSE" in errors
    stale = build_msix.verify_layout(target, "9.9.9")
    assert any("Identity/@Version" in error for error in stale)


def test_missing_executable_stops_before_creating_a_package(tmp_path):
    with pytest.raises(SystemExit):
        build_msix.stage_layout(tmp_path / "vacio", tmp_path / "layout", version=APP_VERSION,
                                trusted_resources={})
    assert not (tmp_path / "layout").exists()


def test_existing_layout_is_only_replaced_inside_the_build_folder(portable, tmp_path):
    outside = tmp_path / "otra-carpeta"
    outside.mkdir()
    (outside / "importante.txt").write_text("no borrar", encoding="utf-8")
    with pytest.raises(ValueError):
        build_msix.stage_layout(portable, outside, version=APP_VERSION, trusted_resources={})
    assert (outside / "importante.txt").is_file()


def _fake_msix(path: Path, layout_dir: Path, extra: dict[str, str] | None = None,
               skip: tuple[str, ...] = ()) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for file in sorted(layout_dir.rglob("*")):
            name = file.relative_to(layout_dir).as_posix()
            if file.is_file() and name not in skip:
                archive.write(file, name)
        for name, content in {"AppxBlockMap.xml": "<BlockMap/>", "[Content_Types].xml": "<Types/>",
                              "resources.pri": "pri", **(extra or {})}.items():
            if name not in skip:
                archive.writestr(name, content)
    return path


def test_packed_file_verification(layout, tmp_path):
    target, _ = layout
    good = _fake_msix(tmp_path / "ok.msix", target)
    assert build_msix.verify_msix(good, APP_VERSION) == []

    with_script = _fake_msix(tmp_path / "script.msix", target, extra={"iniciar.ps1": "x"})
    assert build_msix.verify_msix(with_script, APP_VERSION) == [
        "Archivo que no debe empaquetarse: iniciar.ps1"]

    without_pri = _fake_msix(tmp_path / "sinpri.msix", target, skip=("resources.pri",))
    assert build_msix.verify_msix(without_pri, APP_VERSION) == ["El paquete no contiene resources.pri"]

    without_manifest = _fake_msix(tmp_path / "sinmanifiesto.msix", target, skip=("AppxManifest.xml",))
    assert build_msix.verify_msix(without_manifest, APP_VERSION) == [
        "El paquete no contiene AppxManifest.xml"]

    assert any("Identity/@Version" in error for error in build_msix.verify_msix(good, "9.9.9"))
    broken = tmp_path / "roto.msix"
    broken.write_bytes(b"no es un zip")
    assert build_msix.verify_msix(broken, APP_VERSION)[0].startswith("No se pudo leer")


def test_package_filename_carries_version_and_architecture():
    assert build_msix.msix_filename("3.4.5") == "AnonimizadorUsoPersonal-3.4.5-x64.msix"


def test_sdk_tools_can_be_pointed_to_explicitly(monkeypatch, tmp_path):
    (tmp_path / "makeappx.exe").write_text("tool", encoding="utf-8")
    monkeypatch.setenv("ANON_WINDOWS_SDK_BIN", str(tmp_path))
    assert build_msix.find_sdk_tool("makeappx.exe") == tmp_path / "makeappx.exe"
    with pytest.raises(SystemExit):
        build_msix.find_sdk_tool("makepri.exe")


def test_release_workflow_builds_and_uploads_the_msix_without_publishing_it():
    import yaml

    workflow = yaml.load((ROOT / ".github/workflows/release-windows.yml").read_text(encoding="utf-8"),
                         Loader=yaml.BaseLoader)
    steps = workflow["jobs"]["build"]["steps"]
    commands = [step.get("run", "") for step in steps]
    portable_build = next(i for i, run in enumerate(commands) if "build_portable_full.py" in run)
    msix_build = next(i for i, run in enumerate(commands) if "build_msix.py" in run)
    assert msix_build > portable_build, "El MSIX se arma después del portable"
    assert "test_msix_package.py" in commands[msix_build]
    assert steps[msix_build].get("env", {}).get("ANON_REQUIRE_MSIX") == "1"
    uploads = [step["with"]["path"] for step in steps if "upload-artifact" in step.get("uses", "")]
    assert any(".msix" in path for path in uploads), "El .msix se sube como artefacto"
    # El portable sigue subiéndose y la Release publica solo el ZIP verificado.
    assert any("asset_name" in path for path in uploads)
    publish = " ".join(step.get("run", "") for step in workflow["jobs"]["publish"]["steps"])
    assert ".msix" not in publish


# ── Paquete real, si ya se construyó ──────────────────────────────────────

def _real_layout() -> Path | None:
    env = os.environ.get("ANON_MSIX_DIR", "").strip()
    candidate = Path(env).expanduser().resolve() if env else build_msix.LAYOUT_DIR
    return candidate if (candidate / "AppxManifest.xml").is_file() else None


def _real_msix() -> Path | None:
    env = os.environ.get("ANON_MSIX", "").strip()
    candidate = (Path(env).expanduser().resolve() if env
                 else ROOT / "dist" / build_msix.msix_filename(APP_VERSION))
    return candidate if candidate.is_file() else None


def _require(found, what: str):
    if found is None:
        message = f"No hay {what}. Generalo con scripts/build_msix.py."
        if os.environ.get("ANON_REQUIRE_MSIX") == "1":
            pytest.fail(message)
        pytest.skip(message)
    return found


def test_built_layout_structure():
    layout_dir = _require(_real_layout(), "carpeta de paquete MSIX construida")
    assert build_msix.verify_layout(layout_dir, APP_VERSION) == []
    assert (layout_dir / EXE).stat().st_size > 1024 * 1024, "El ejecutable parece incompleto"
    assert (layout_dir / "_internal" / "data" / "dictionaries").is_dir(), "Faltan los diccionarios"
    assert not [path for path in layout_dir.rglob("*")
                if path.suffix.lower() in {".bat", ".ps1", ".cmd"}]


def test_built_msix_file():
    msix = _require(_real_msix(), "archivo .msix construido")
    assert build_msix.verify_msix(msix, APP_VERSION) == []
    with zipfile.ZipFile(msix) as archive:
        assert archive.testzip() is None
        from io import BytesIO
        from docx import Document

        template = Document(BytesIO(archive.read("_internal/docx/templates/default.docx")))
        template.add_paragraph("Exportación de prueba")
        exported = BytesIO()
        template.save(exported)
        assert Document(exported).paragraphs[-1].text == "Exportación de prueba"
        names = set(archive.namelist())
    assert "Assets/StoreLogo.png" in names
    assert any(name.startswith("models/es_core_news_md/") for name in names)
    assert not [name for name in names if name.lower().endswith((".bat", ".ps1", ".cmd"))]
