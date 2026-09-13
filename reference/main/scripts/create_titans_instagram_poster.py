"""Create a face-safe 1080x1350 Instagram Feed poster."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[3]
FONT_DIR = ROOT / "assets" / "fonts"
WINNER = Path(r"C:\Users\pavan\OneDrive\Desktop\winner.jpeg")
GROUP = Path(r"C:\Users\pavan\OneDrive\Desktop\whole.jpeg")
OUTPUT = ROOT / "output" / "posters" / "22yards-houston-titans-winners-instagram-4x5.png"

W, H = 1080, 1350
WHITE = "#FFFFFF"
OFF_WHITE = "#F7FAFF"
BLUE = "#0757A6"
DEEP_BLUE = "#063D7C"
SKY = "#D9EDFF"
YELLOW = "#F5C400"
CHARCOAL = "#252A31"


def face(filename: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / filename), size=size)


def fit_face(filename: str, text: str, width: int, start: int) -> ImageFont.FreeTypeFont:
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for size in range(start, 15, -1):
        candidate = face(filename, size)
        box = probe.textbbox((0, 0), text, font=candidate)
        if box[2] - box[0] <= width:
            return candidate
    return face(filename, 16)


def centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: ImageFont.FreeTypeFont,
    fill: str,
    *,
    x1: int = 0,
    x2: int = W,
) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    x = x1 + ((x2 - x1) - (box[2] - box[0])) // 2
    draw.text((x, y), text, font=font, fill=fill)


def photo_frame(
    canvas: Image.Image,
    source: Path,
    box: tuple[int, int, int, int],
    label: str,
) -> None:
    left, top, right, bottom = box
    draw = ImageDraw.Draw(canvas)

    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle(
        (left + 4, top + 7, right + 4, bottom + 9),
        radius=19,
        fill=(7, 87, 166, 45),
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(7)))

    draw.rounded_rectangle(box, radius=18, fill=WHITE, outline=BLUE, width=5)
    draw.rounded_rectangle(
        (left + 7, top + 7, right - 7, bottom - 7),
        radius=13,
        outline=YELLOW,
        width=3,
    )

    inset = 12
    target = (right - left - inset * 2, bottom - top - inset * 2)
    with Image.open(source) as original:
        photo = ImageOps.exif_transpose(original).convert("RGB")
        # Uniform exposure only. No crop, face detection, retouching or AI.
        photo = ImageEnhance.Brightness(photo).enhance(1.12)
        photo = ImageOps.contain(photo, target, method=Image.Resampling.LANCZOS)
    backing = Image.new("RGB", target, WHITE)
    backing.paste(photo, ((target[0] - photo.width) // 2, (target[1] - photo.height) // 2))
    canvas.paste(backing, (left + inset, top + inset))

    label_font = face("space-grotesk-700.woff2", 20)
    label_box = draw.textbbox((0, 0), label, font=label_font)
    pill_width = label_box[2] - label_box[0] + 34
    draw.rounded_rectangle(
        (left + 23, top - 13, left + 23 + pill_width, top + 22),
        radius=15,
        fill=BLUE,
    )
    draw.text((left + 40, top - 7), label, font=label_font, fill=WHITE)


def build() -> Path:
    for source in (WINNER, GROUP):
        if not source.is_file():
            raise FileNotFoundError(source)

    canvas = Image.new("RGBA", (W, H), OFF_WHITE)
    draw = ImageDraw.Draw(canvas)

    draw.polygon([(0, 0), (225, 0), (0, 235)], fill=SKY)
    draw.polygon([(W, 0), (890, 0), (W, 225)], fill=SKY)
    draw.polygon([(W, 5), (W, 55), (955, 195), (990, 55)], fill=BLUE)
    draw.polygon([(W, 65), (W, 100), (985, 205), (1010, 90)], fill=YELLOW)
    draw.line((50, 104, 250, 104), fill=YELLOW, width=4)
    draw.line((830, 104, 1030, 104), fill=YELLOW, width=4)

    centered(draw, "22YARDS HOUSTON", 19, face("anton-400.woff2", 51), BLUE)
    centered(
        draw,
        "SATURDAY CRICKET SERIES",
        76,
        face("space-grotesk-700.woff2", 29),
        YELLOW,
    )
    title = "22YARDS TITANS — WINNERS"
    centered(draw, title, 112, fit_face("anton-400.woff2", title, 990, 62), BLUE)
    centered(
        draw,
        "vs 22Yards Challengers",
        194,
        face("space-grotesk-500.woff2", 27),
        CHARCOAL,
    )

    photo_frame(canvas, WINNER, (32, 260, 790, 745), "22YARDS TITANS")
    photo_frame(canvas, GROUP, (32, 775, 790, 1285), "SATURDAY SERIES PLAYERS")

    # Winner score panel.
    draw.rounded_rectangle((812, 260, 1048, 745), radius=20, fill=BLUE)
    centered(draw, "WINNERS", 283, face("space-grotesk-700.woff2", 27), WHITE, x1=812, x2=1048)
    draw.line((842, 328, 1018, 328), fill=YELLOW, width=3)
    centered(draw, "TITANS", 348, face("anton-400.woff2", 43), WHITE, x1=812, x2=1048)
    centered(draw, "65/4", 394, face("anton-400.woff2", 69), YELLOW, x1=812, x2=1048)
    centered(
        draw,
        "CHALLENGERS",
        475,
        face("space-grotesk-700.woff2", 22),
        WHITE,
        x1=812,
        x2=1048,
    )
    centered(draw, "59/2", 510, face("anton-400.woff2", 54), YELLOW, x1=812, x2=1048)
    centered(draw, "10 OVERS", 579, face("space-grotesk-700.woff2", 23), WHITE, x1=812, x2=1048)
    draw.line((842, 623, 1018, 623), fill=YELLOW, width=3)
    centered(draw, "WON BY", 639, face("space-grotesk-700.woff2", 24), WHITE, x1=812, x2=1048)
    centered(draw, "6 RUNS", 672, face("anton-400.woff2", 50), YELLOW, x1=812, x2=1048)

    # Match-star panel.
    draw.rounded_rectangle((812, 775, 1048, 1285), radius=20, fill=WHITE, outline=BLUE, width=5)
    draw.rounded_rectangle((826, 793, 1034, 842), radius=14, fill=BLUE)
    centered(draw, "MATCH STARS", 801, face("space-grotesk-700.woff2", 24), WHITE, x1=812, x2=1048)
    centered(draw, "RISHAV", 872, face("anton-400.woff2", 39), BLUE, x1=812, x2=1048)
    centered(draw, "PANCHAL", 915, face("space-grotesk-700.woff2", 24), DEEP_BLUE, x1=812, x2=1048)
    centered(draw, "15 (26)", 956, face("anton-400.woff2", 48), YELLOW, x1=812, x2=1048)
    centered(draw, "BOWLING 1/2", 1012, face("space-grotesk-700.woff2", 21), CHARCOAL, x1=812, x2=1048)
    draw.line((842, 1058, 1018, 1058), fill=SKY, width=3)
    centered(draw, "VIHAAN", 1073, face("anton-400.woff2", 39), BLUE, x1=812, x2=1048)
    centered(draw, "ADHVARYU", 1117, face("space-grotesk-700.woff2", 22), DEEP_BLUE, x1=812, x2=1048)
    centered(draw, "6 (8)", 1157, face("anton-400.woff2", 48), YELLOW, x1=812, x2=1048)
    centered(draw, "BOWLING 2/5", 1213, face("space-grotesk-700.woff2", 21), CHARCOAL, x1=812, x2=1048)

    draw.line((215, 1320, 370, 1320), fill=YELLOW, width=4)
    draw.line((710, 1320, 865, 1320), fill=YELLOW, width=4)
    centered(draw, "AUGUST 15, 2026", 1298, face("space-grotesk-700.woff2", 29), BLUE)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(OUTPUT, format="PNG", optimize=True)
    return OUTPUT


if __name__ == "__main__":
    print(build())
