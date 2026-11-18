"""Genera los íconos del paquete MSIX a partir del logo de la aplicación.

Uso:
  python scripts/make_msix_icons.py
  python scripts/make_msix_icons.py --source ruta/a/otro_logo.ico

Salida: packaging/msix/Assets/ (se reemplaza completa).

El logo es ``packaging/app.ico``, el mismo que lleva el ejecutable. Para
cambiar la imagen del paquete alcanza con reemplazar ese archivo (o pasar otro
ICO o PNG de fondo transparente con ``--source``) y volver a correr el script.

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
SOURCE = ROOT / "packaging" / "app.ico"
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


def load_marks(source: Path) -> list:
    """Versiones del logo, de menor a mayor, recortadas a su contenido.

    Un ``.ico`` trae varias, dibujadas para cada tamaño; un PNG, una sola.
    """
    from PIL import Image

    image = Image.open(source)
    sizes = sorted(image.info.get("sizes", [])) if image.format == "ICO" else []
    frames = []
    if sizes:
        for size in sizes:
            frame = Image.open(source)
            frame.size = size
            frame.load()
            frames.append(frame.convert("RGBA"))
    else:
        frames.append(image.convert("RGBA"))
    marks = []
    for frame in frames:
        if frame.getchannel("A").getextrema()[0] != 0:
            raise SystemExit(f"El logo debe tener fondo transparente: {source}")
        marks.append(frame.crop(frame.getbbox()))
    return marks


def is_single_colour(mark) -> bool:
    """True si el logo es una silueta de un solo color (como un isotipo)."""
    opaque = [colour[:3] for _count, colour in mark.getcolors(maxcolors=mark.width * mark.height)
              if colour[3] > 200]
    if not opaque:
        return True
    return all(max(c[i] for c in opaque) - min(c[i] for c in opaque) < 48 for i in range(3))


def render(marks, side: int, fill: float, *, white: bool = False):
    """Logo centrado sobre un lienzo cuadrado transparente.

    Usa la versión más chica que alcanza para no agrandar, y así aprovecha
    las que el ``.ico`` trae dibujadas para tamaños pequeños.
    """
    from PIL import Image

    if not isinstance(marks, (list, tuple)):
        marks = [marks]
    box = max(1, round(side * fill))
    mark = next((m for m in marks if max(m.size) >= box), marks[-1])
    ratio = min(box / mark.width, box / mark.height)
    size = (max(1, round(mark.width * ratio)), max(1, round(mark.height * ratio)))
    scaled = mark if size == mark.size else mark.resize(size, Image.LANCZOS)
    if white:
        tinted = Image.new("RGBA", size, (255, 255, 255, 0))
        tinted.putalpha(scaled.getchannel("A"))
        scaled = tinted
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(scaled, ((side - size[0]) // 2, (side - size[1]) // 2))
    return canvas


def build(source: Path = SOURCE, output: Path = ASSETS) -> list[Path]:
    marks = load_marks(source)
    # Una silueta de un solo color se pasa a blanco para que se distinga sin
    # placa sobre fondo oscuro. Un logo de varios colores se deja como está.
    tint_for_dark = is_single_colour(marks[-1])
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    written = []
    for filename, side in expected_assets().items():
        white = tint_for_dark and filename.endswith("_altform-unplated.png")
        path = output / filename
        render(marks, side, _fill_for(filename), white=white).save(path, optimize=True)
        written.append(path)
    return written


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Íconos del paquete MSIX")
    parser.add_argument("--source", type=Path, default=SOURCE,
                        help="ICO o PNG con fondo transparente (por defecto, packaging/app.ico)")
    args = parser.parse_args()
    files = build(args.source)
    print(f"{len(files)} íconos en {ASSETS}")
