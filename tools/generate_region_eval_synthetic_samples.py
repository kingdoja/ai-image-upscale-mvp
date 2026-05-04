from __future__ import annotations

from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont


SAMPLE_DIR = Path(__file__).resolve().parents[1] / "datasets" / "region-eval" / "samples"


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _save(image: Image.Image, filename: str) -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    image.save(SAMPLE_DIR / filename)


def _label(draw: ImageDraw.ImageDraw, xy: Tuple[int, int], text: str, size: int, *, fill=(25, 35, 45)) -> None:
    draw.text(xy, text, font=_font(size, bold=True), fill=fill)


def make_text_only_poster() -> None:
    image = Image.new("RGB", (800, 520), color=(246, 241, 232))
    draw = ImageDraw.Draw(image)
    draw.rectangle((54, 58, 746, 290), fill=(255, 255, 252), outline=(198, 188, 174), width=3)
    _label(draw, (86, 88), "SPRING SALE", 64)
    _label(draw, (90, 170), "LIMITED OFFER", 42, fill=(92, 72, 52))
    _label(draw, (92, 232), "TEXT ONLY NOTICE", 30, fill=(65, 75, 85))
    draw.rectangle((54, 338, 746, 392), fill=(232, 224, 212))
    _label(draw, (92, 346), "NO BRAND MARK IN THIS SAMPLE", 25, fill=(80, 76, 68))
    _save(image, "synthetic-text-only-poster.png")


def make_packaging_text_only() -> None:
    image = Image.new("RGB", (900, 600), color=(238, 239, 232))
    draw = ImageDraw.Draw(image)
    for offset in (0, 160, 320):
        x = 120 + offset
        draw.rounded_rectangle((x, 90, x + 130, 500), radius=6, fill=(218, 228, 214), outline=(172, 182, 164), width=2)
        draw.rectangle((x + 20, 185, x + 110, 360), fill=(252, 252, 248), outline=(180, 176, 164), width=2)
    _label(draw, (302, 210), "MODEL A12", 31)
    _label(draw, (310, 262), "CAUTION", 34, fill=(132, 44, 38))
    _label(draw, (310, 318), "CARTRIDGE", 24, fill=(45, 60, 58))
    _label(draw, (462, 212), "MODEL B24", 30)
    _label(draw, (470, 266), "CAUTION", 31, fill=(132, 44, 38))
    _label(draw, (470, 320), "REFILL UNIT", 23, fill=(45, 60, 58))
    _save(image, "synthetic-packaging-text-only.png")


def make_plain_product_negative() -> None:
    image = Image.new("RGB", (800, 600), color=(242, 242, 238))
    draw = ImageDraw.Draw(image)
    draw.ellipse((210, 120, 590, 460), fill=(192, 206, 208), outline=(138, 156, 160), width=5)
    draw.ellipse((300, 205, 500, 385), fill=(216, 224, 225), outline=(160, 174, 178), width=3)
    draw.rectangle((0, 480, 800, 600), fill=(224, 225, 220))
    _save(image, "synthetic-plain-product-negative.png")


def make_packaging_logo_text() -> None:
    image = Image.new("RGB", (900, 600), color=(238, 240, 236))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((90, 70, 520, 530), radius=8, fill=(230, 238, 226), outline=(155, 170, 148), width=3)
    draw.rectangle((110, 92, 224, 196), fill=(18, 28, 40))
    draw.ellipse((138, 116, 196, 174), fill=(240, 245, 230))
    draw.rectangle((260, 132, 466, 390), fill=(255, 255, 250), outline=(176, 172, 160), width=2)
    _label(draw, (282, 160), "GREEN PACK", 34)
    _label(draw, (284, 226), "MODEL G9", 30)
    _label(draw, (286, 284), "CAUTION", 31, fill=(136, 44, 38))
    _label(draw, (286, 342), "HANDLE DRY", 23, fill=(45, 58, 55))
    draw.rounded_rectangle((585, 92, 810, 508), radius=8, fill=(220, 226, 216), outline=(172, 178, 164), width=2)
    _save(image, "synthetic-packaging-logo-text.png")


def main() -> None:
    make_text_only_poster()
    make_packaging_text_only()
    make_plain_product_negative()
    make_packaging_logo_text()
    print(f"Synthetic region-eval samples written to {SAMPLE_DIR}")


if __name__ == "__main__":
    main()
