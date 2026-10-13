from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

RAMP = " .:-=+*#%@"
CELL_ASPECT = 0.5
ASCII_COLUMNS = 80
PORTRAIT_CROP = (0.2, 0.12, 0.8, 0.74)


def image_to_ascii(image: Image.Image, columns: int) -> list[str]:
    rows = max(1, round(columns * image.height / image.width * CELL_ASPECT))
    gray = image.convert("L").resize((columns, rows), Image.Resampling.LANCZOS)
    sharpened = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=220, threshold=2))
    toned = ImageOps.autocontrast(sharpened, cutoff=1)
    last = len(RAMP) - 1
    return [
        "".join(RAMP[round(toned.getpixel((x, y)) / 255 * last)] for x in range(columns))
        for y in range(rows)
    ]


def write_portrait(image_path: Path, data_dir: Path) -> None:
    with Image.open(image_path) as image:
        width, height = image.size
        left, top, right, bottom = PORTRAIT_CROP
        box = (int(left * width), int(top * height), int(right * width), int(bottom * height))
        lines = image_to_ascii(image.crop(box), ASCII_COLUMNS)
    (data_dir / "ascii.txt").write_text("\n".join(lines) + "\n")
