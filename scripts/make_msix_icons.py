"""Genera los íconos del paquete MSIX a partir del isotipo de la marca.

Uso:
  python scripts/make_msix_icons.py
  python scripts/make_msix_icons.py --source ruta/a/otro_isotipo.png

Salida: packaging/msix/Assets/ (se reemplaza completa).

Para cambiar la imagen del paquete alcanza con volver a correr este script con
otro PNG de fondo transparente, o con reemplazar a mano los archivos de esa
carpeta conservando nombres y tamaños.

Tamaños según "Construct your Windows app's icon" (Microsoft Learn):
- StoreLogo: 50 px a escala 100 %.
- Square44x44Logo: 44 px a escala 100 %, más variantes ``targetsize`` para la
  barra de tareas y el menú Inicio. ``altform-unplated`` se usa sobre fondo
  oscuro y ``altform-lightunplated`` sobre fondo claro, ambas sin placa.
- Square150x150Logo: 150 px a escala 100 %.
Los nombres con calificador (``scale-200``, ``targetsize-24_altform-unplated``)
solo se resuelven si el paquete incluye ``resources.pri``; lo genera
``scripts/build_msix.py`` con ``makepri.exe``.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "marca" / "logos" / "isotype_azul.png"
ASSETS = ROOT / "packaging" / "msix" / "Assets"

SCALES = (100, 200, 400)
TARGET_SIZES = (16, 24, 32, 48, 256)
# nombre base -> (lado en px a escala 100 %, fracción del lado que ocupa el isotipo)
TILES = {
    "StoreLogo": (50, 0.80),
    "Square44x44Logo": (44, 0.75),
    "Square150x150Logo": (150, 0.55),
}
TARGET_FILL = 0.92


def expected_assets() -> dict[str, int]:
    """Nombre de archivo -> lado en píxeles de cada ícono generado."""
    assets: dict[str, int] = {}
    for name, (base, _fill) in TILES.items():
        for scale in SCALES:
            suffix = "" if scale == 100 else f".scale-{scale}"
            assets[f"{name}{suffix}.png"] = round(base * scale / 100)
    for size in TARGET_SIZES:
        assets[f"Square44x44Logo.targetsize-{size}.png"] = size
        assets[f"Square44x44Logo.targetsize-{size}_altform-unplated.png"] = size
        assets[f"Square44x44Logo.targetsize-{size}_altform-lightunplated.png"] = size
    return assets


def _fill_for(filename: str) -> float:
    if ".targetsize-" in filename:
        return TARGET_FILL
    return TILES[filename.split(".")[0]][1]


def render(mark, side: int, fill: float, *, white: bool = False):
    """Isotipo centrado sobre un lienzo cuadrado transparente."""
    from PIL import Image

    box = max(1, round(side * fill))
    ratio = min(box / mark.width, box / mark.height)
    size = (max(1, round(mark.width * ratio)), max(1, round(mark.height * ratio)))
    scaled = mark.resize(size, Image.LANCZOS)
    if white:
        tinted = Image.new("RGBA", size, (255, 255, 255, 0))
        tinted.putalpha(scaled.getchannel("A"))
        scaled = tinted
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(scaled, ((side - size[0]) // 2, (side - size[1]) // 2))
    return canvas


def build(source: Path = SOURCE, output: Path = ASSETS) -> list[Path]:
    from PIL import Image

    mark = Image.open(source).convert("RGBA")
    mark = mark.crop(mark.getbbox())
    if mark.getchannel("A").getextrema()[0] != 0:
        raise SystemExit(f"El isotipo debe tener fondo transparente: {source}")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    written = []
    for filename, side in expected_assets().items():
        # Sin placa sobre fondo oscuro: isotipo en blanco para que se distinga.
        white = filename.endswith("_altform-unplated.png")
        path = output / filename
        render(mark, side, _fill_for(filename), white=white).save(path, optimize=True)
        written.append(path)
    return written


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Íconos del paquete MSIX")
    parser.add_argument("--source", type=Path, default=SOURCE,
                        help="PNG con fondo transparente (por defecto, el isotipo azul)")
    args = parser.parse_args()
    files = build(args.source)
    print(f"{len(files)} íconos en {ASSETS}")
