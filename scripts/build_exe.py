"""Construir ejecutable Windows con PyInstaller."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Instalando PyInstaller…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    frontend = ROOT / "frontend"
    data = ROOT / "data"

    sep = ";" if sys.platform == "win32" else ":"
    add_data = [
        f"{frontend}{sep}frontend",
        f"{data}{sep}data",
    ]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        "AnonimizadorJudicial",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--distpath={ROOT / 'dist'}",
        f"--workpath={ROOT / 'build'}",
        f"--specpath={ROOT}",
    ]
    for item in add_data:
        cmd.extend(["--add-data", item])

    cmd.append(str(ROOT / "scripts" / "launcher.py"))
    print("Ejecutando:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)
    print(f"\nListo: {ROOT / 'dist' / 'AnonimizadorJudicial.exe'}")


if __name__ == "__main__":
    main()
