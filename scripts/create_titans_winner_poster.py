"""Build the Titans winner poster without generatively editing any photograph."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "assets" / "fonts"
DEFAULT_WINNER = Path(r"C:\Users\pavan\OneDrive\Desktop\winner.jpeg")
DEFAULT_GROUP = Path(r"C:\Users\pavan\OneDrive\Desktop\whole.jpeg")
DEFAULT_OUTPUT = ROOT / "output" / "posters" / "22yards-houston-titans-winners-face-safe.png"

WIDTH, HEIGHT = 1080, 1920
WHITE = "#FFFFFF"
OFF_WHITE = "#F7FAFF"
ROYAL_BLUE = "#0757A6"
DEEP_BLUE = "#063D7C"
SKY_BLUE = "#D9EDFF"
YELLOW = "#F5C400"
CHARCOAL = "#252A31"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size=size)


def centered_text(
    draw: ImageDraw.ImageDraw,
    y: int,
    text: str,
    face: ImageFont.FreeTypeFont,
    fill: str,
    *,
    stroke_width: int = 0,
    stroke_fill: str | None = None,
) -> tuple[int, int, int, int]:
    box = draw.textbbox((0, 0), text, font=face, stroke_width=stroke_width)
    x = (WIDTH - (box[2] - box[0])) // 2
    draw.text(
        (x, y),
        text,
        font=face,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )
    return draw.textbbox((x, y), text, font=face, stroke_width=stroke_width)


def fit_font(name: str, text: str, max_width: int, start: int, minimum: int = 18) -> ImageFont.FreeTypeFont:
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    size = start
    while size > minimum:
        face = font(name, size)
        box = probe.textbbox((0, 0), text, font=face)
        if box[2] - box[0] <= max_width:
            return face
        size -= 1
    return font(name, minimum)


def add_background(canvas: Image.Image) -> None:
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.polygon([(0, 0), (240, 0), (0, 300)], fill="#D9EDFF")
    draw.polygon([(WIDTH, 0), (870, 0), (WIDTH, 260)], fill="#D9EDFF")
    draw.polygon([(WIDTH, 15), (WIDTH, 70), (930, 245), (965, 90)], fill=ROYAL_BLUE)
    draw.polygon([(WIDTH, 95), (WIDTH, 130), (970, 255), (995, 135)], fill=YELLOW)
    draw.polygon([(0, 1010), (28, 950), (28, 1450), (0, 1510)], fill=SKY_BLUE)
    draw.polygon([(WIDTH, 1060), (1052, 1000), (1052, 1490), (WIDTH, 1550)], fill=SKY_BLUE)
    for offset in range(0, 5):
        draw.line(
            [(36 + offset * 13, 250), (150 + offset * 8, 115)],
            fill=ROYAL_BLUE if offset % 2 == 0 else YELLOW,
            width=4,
        )
    canvas.alpha_composite(overlay)


def place_photo(
    canvas: Image.Image,
    source: Path,
    box: tuple[int, int, int, int],
    *,
    label: str,
) -> None:
    left, top, right, bottom = box
    frame_w, frame_h = right - left, bottom - top
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle(
        (left + 5, top + 10, right + 5, bottom + 12),
        radius=24,
        fill=(7, 87, 166, 50),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    canvas.alpha_composite(shadow)

    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(box, radius=22, fill=WHITE, outline=ROYAL_BLUE, width=7)
    draw.rounded_rectangle(
        (left + 8, top + 8, right - 8, bottom - 8),
        radius=16,
        outline=YELLOW,
        width=3,
    )

    inset = 15
    target_size = (frame_w - inset * 2, frame_h - inset * 2)
    with Image.open(source) as original:
        photo = ImageOps.exif_transpose(original).convert("RGB")
        # A uniform exposure adjustment across the complete photo. This does
        # not detect, reconstruct, smooth, or otherwise selectively edit faces.
        photo = ImageEnhance.Brightness(photo).enhance(1.12)
        # `contain` is deliberate: no crop, generative fill, retouching, or
        # colour adjustment. Every source pixel remains represented.
        photo = ImageOps.contain(photo, target_size, method=Image.Resampling.LANCZOS)
    photo_layer = Image.new("RGB", target_size, WHITE)
    px = (target_size[0] - photo.width) // 2
    py = (target_size[1] - photo.height) // 2
    photo_layer.paste(photo, (px, py))
    canvas.paste(photo_layer, (left + inset, top + inset))

    label_face = font("space-grotesk-700.woff2", 25)
    label_box = draw.textbbox((0, 0), label, font=label_face)
    pill_w = label_box[2] - label_box[0] + 42
    draw.rounded_rectangle(
        (left + 28, top - 18, left + 28 + pill_w, top + 25),
        radius=18,
        fill=ROYAL_BLUE,
    )
    draw.text((left + 49, top - 10), label, font=label_face, fill=WHITE)


def build_poster(winner: Path, group: Path, output: Path) -> Path:
    for source in (winner, group):
        if not source.is_file():
            raise FileNotFoundError(source)

    canvas = Image.new("RGBA", (WIDTH, HEIGHT), OFF_WHITE)
    add_background(canvas)
    draw = ImageDraw.Draw(canvas)

    centered_text(draw, 30, "22YARDS HOUSTON", font("anton-400.woff2", 62), ROYAL_BLUE)
    draw.line((80, 134, 270, 134), fill=YELLOW, width=5)
    draw.line((810, 134, 1000, 134), fill=YELLOW, width=5)
    centered_text(
        draw,
        108,
        "SATURDAY CRICKET SERIES",
        font("space-grotesk-700.woff2", 38),
        YELLOW,
    )
    winner_title = "22YARDS TITANS — WINNERS"
    centered_text(
        draw,
        158,
        winner_title,
        fit_font("anton-400.woff2", winner_title, 990, 72),
        ROYAL_BLUE,
    )
    centered_text(
        draw,
        245,
        "vs 22Yards Challengers",
        font("space-grotesk-700.woff2", 32),
        CHARCOAL,
    )

    place_photo(canvas, winner, (45, 320, 1035, 945), label="22YARDS TITANS")
    place_photo(canvas, group, (45, 985, 1035, 1645), label="SATURDAY SERIES PLAYERS")

    panel = (45, 1680, 1035, 1872)
    draw.rounded_rectangle(panel, radius=26, fill=WHITE, outline=ROYAL_BLUE, width=6)
    draw.line((472, 1692, 472, 1860), fill=ROYAL_BLUE, width=3)

    left_title = font("anton-400.woff2", 44)
    left_body = font("space-grotesk-700.woff2", 30)
    draw.text((75, 1700), "TITANS", font=left_title, fill=ROYAL_BLUE)
    draw.text((265, 1700), "65/4", font=left_title, fill=YELLOW)
    draw.text((75, 1750), "CHALLENGERS", font=left_body, fill=ROYAL_BLUE)
    draw.text((310, 1750), "59/2", font=left_body, fill=YELLOW)
    result_face = font("space-grotesk-700.woff2", 22)
    draw.text((75, 1802), "10 OVERS", font=result_face, fill=CHARCOAL)
    draw.text((185, 1802), "•", font=result_face, fill=YELLOW)
    draw.text((210, 1802), "WON BY 6 RUNS", font=result_face, fill=ROYAL_BLUE)

    draw.rounded_rectangle((510, 1698, 990, 1748), radius=16, fill=ROYAL_BLUE)
    centered = "MATCH STARS"
    star_face = font("space-grotesk-700.woff2", 31)
    sb = draw.textbbox((0, 0), centered, font=star_face)
    sx = 750 - (sb[2] - sb[0]) // 2
    draw.text((sx, 1705), centered, font=star_face, fill=WHITE)
    stat_face = fit_font(
        "space-grotesk-700.woff2",
        "RISHAV PANCHAL • 15 (26) • 1/2",
        480,
        27,
    )
    draw.text((500, 1764), "RISHAV PANCHAL • 15 (26) • 1/2", font=stat_face, fill=DEEP_BLUE)
    draw.text((500, 1810), "VIHAAN ADHVARYU • 6 (8) • 2/5", font=stat_face, fill=DEEP_BLUE)

    draw.line((215, 1893, 380, 1893), fill=YELLOW, width=4)
    draw.line((700, 1893, 865, 1893), fill=YELLOW, width=4)
    centered_text(
        draw,
        1878,
        "AUGUST 15, 2026",
        font("space-grotesk-700.woff2", 31),
        ROYAL_BLUE,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, format="PNG", optimize=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--winner-photo", type=Path, default=DEFAULT_WINNER)
    parser.add_argument("--group-photo", type=Path, default=DEFAULT_GROUP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(build_poster(args.winner_photo, args.group_photo, args.output))


if __name__ == "__main__":
    main()
