"""La carpeta de datos del usuario no puede quedar en la instalación de Store."""
import ast
from pathlib import Path

from app import runtime_paths

ROOT = Path(__file__).resolve().parent.parent


def test_portable_and_development_keep_data_next_to_the_application(monkeypatch):
    monkeypatch.delenv("ANON_DATA_DIR", raising=False)
    monkeypatch.setattr(runtime_paths, "is_packaged", lambda: False)
    assert runtime_paths.user_data_dir() == runtime_paths.app_dir()
    assert runtime_paths.port_file() == runtime_paths.app_dir() / "PUERTO_ACTUAL.txt"


def test_store_package_writes_under_local_app_data(monkeypatch, tmp_path):
    monkeypatch.delenv("ANON_DATA_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(runtime_paths, "is_packaged", lambda: True)
    data = runtime_paths.user_data_dir()
    assert data == tmp_path / "AnonimizadorUsoPersonal"
    assert not data.is_relative_to(runtime_paths.app_dir())
    assert runtime_paths.port_file().parent == data
    assert not data.exists(), "Resolver la ruta no debe crear carpetas"


def test_store_package_without_local_app_data_uses_the_user_profile(monkeypatch, tmp_path):
    monkeypatch.delenv("ANON_DATA_DIR", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(runtime_paths, "is_packaged", lambda: True)
    monkeypatch.setattr(runtime_paths.Path, "home", classmethod(lambda cls: tmp_path))
    assert runtime_paths.user_data_dir() == tmp_path / "AppData" / "Local" / "AnonimizadorUsoPersonal"


def test_explicit_data_directory_takes_precedence(monkeypatch, tmp_path):
    monkeypatch.setenv("ANON_DATA_DIR", str(tmp_path / "datos"))
    monkeypatch.setattr(runtime_paths, "is_packaged", lambda: True)
    assert runtime_paths.user_data_dir() == (tmp_path / "datos").resolve()


def test_development_process_has_no_package_identity():
    assert runtime_paths.is_packaged() is False


def test_application_code_never_writes_relative_to_the_install_folder():
    """``app_dir()`` queda reservado a recursos de solo lectura."""
    allowed = {"frontend", "models"}
    offenders = []
    for path in sorted((ROOT / "app").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            # app_dir() / "algo": solo se admite para recursos de lectura.
            if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
                    and isinstance(node.left, ast.Call)
                    and getattr(node.left.func, "id", "") == "app_dir"):
                target = node.right.value if isinstance(node.right, ast.Constant) else None
                if target not in allowed:
                    offenders.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno}")
    assert offenders == []
