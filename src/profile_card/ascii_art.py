from pathlib import Path

from PIL import Image, ImageOps

RAMP = " .:-=+*#%@"
CELL_ASPECT = 0.5
ASCII_COLUMNS = 70


def image_to_ascii(image: Image.Image, columns: int, invert: bool) -> list[str]:
    rows = max(1, round(columns * image.height / image.width * CELL_ASPECT))
    gray = ImageOps.autocontrast(
        image.convert("L").resize((columns, rows), Image.Resampling.LANCZOS)
    )
    last = len(RAMP) - 1
    lines = []
    for y in range(rows):
        line = []
        for x in range(columns):
            level = gray.getpixel((x, y)) / 255
            if invert:
                level = 1 - level
            line.append(RAMP[round(level * last)])
        lines.append("".join(line))
    return lines


def write_portraits(image_path: Path, data_dir: Path) -> None:
    with Image.open(image_path) as image:
        for name, invert in (("ascii_dark.txt", False), ("ascii_light.txt", True)):
            lines = image_to_ascii(image, ASCII_COLUMNS, invert)
            (data_dir / name).write_text("\n".join(lines) + "\n")
