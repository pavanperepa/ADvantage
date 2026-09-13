"""Create a face-safe 4:5 Instagram academy enrollment poster.

The supplied photographs are used as ordinary raster layers. They receive only
crop/resize and global exposure adjustments; no generative editing or face
retouching is performed.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import segno
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[3]
FONT_DIR = ROOT / "assets" / "fonts"
LOGO = ROOT / "assets" / "brand" / "22yards-houston.png"
HERO = ROOT / "real-photo" / "AP7A4720.JPG"
RUNNING = ROOT / "real-photo" / "AP7A4707.JPG"
BOWLING = ROOT / "real-photo" / "AP7A4721.JPG"
OUTPUT = ROOT / "output" / "posters" / "22yards-houston-academy-instagram-4x5.png"

REGISTRATION_URL = "https://axon22yards.com/join?location=houston"
PHONE = "+1 (713) 498-2155"

W, H = 1080, 1350
WHITE = "#FFFFFF"
OFF_WHITE = "#F8FBFF"
BLUE = "#0757A6"
DEEP_BLUE = "#063D7C"
SKY = "#D9EDFF"
YELLOW = "#F5C400"
CHARCOAL = "#252A31"
MUTED = "#536274"


def font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / filename), size=size)


def fit_font(filename: str, text: str, width: int, start: int) -> ImageFont.FreeTypeFont:
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for size in range(start, 15, -1):
        candidate = font(filename, size)
        box = probe.textbbox((0, 0), text, font=candidate)
        if box[2] - box[0] <= width:
            return candidate
    return font(filename, 16)


def cover_photo(
    path: Path,
    size: tuple[int, int],
    *,
    centering: tuple[float, float] = (0.5, 0.5),
    brightness: float = 1.1,
) -> Image.Image:
    with Image.open(path) as original:
        photo = ImageOps.exif_transpose(original).convert("RGB")
        photo = ImageEnhance.Brightness(photo).enhance(brightness)
        return ImageOps.fit(
            photo,
            size,
            method=Image.Resampling.LANCZOS,
            centering=centering,
        )


def rounded_photo(
    canvas: Image.Image,
    path: Path,
    box: tuple[int, int, int, int],
    *,
    radius: int,
    centering: tuple[float, float],
    brightness: float = 1.1,
    border: int = 0,
    border_color: str = WHITE,
) -> None:
    left, top, right, bottom = box
    width, height = right - left, bottom - top

    if border:
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle(box, radius=radius, fill=border_color)
        inset_box = (left + border, top + border, right - border, bottom - border)
        rounded_photo(
            canvas,
            path,
            inset_box,
            radius=max(1, radius - border),
            centering=centering,
            brightness=brightness,
        )
        return

    photo = cover_photo(path, (width, height), centering=centering, brightness=brightness)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width, height), radius=radius, fill=255)
    canvas.paste(photo, (left, top), mask)


def qr_image(url: str, size: int) -> Image.Image:
    qr = segno.make(url, error="h")
    stream = BytesIO()
    qr.save(stream, kind="png", scale=12, border=2, dark=DEEP_BLUE, light=WHITE)
    stream.seek(0)
    with Image.open(stream) as source:
        return source.convert("RGB").resize((size, size), Image.Resampling.NEAREST)


def build() -> Path:
    for source in (LOGO, HERO, RUNNING, BOWLING):
        if not source.is_file():
            raise FileNotFoundError(source)

    canvas = Image.new("RGBA", (W, H), OFF_WHITE)
    draw = ImageDraw.Draw(canvas)

    # Bright academy palette and restrained sports accents.
    draw.polygon([(0, 0), (245, 0), (0, 225)], fill=SKY)
    draw.polygon([(W, 0), (930, 0), (W, 175)], fill=YELLOW)
    draw.polygon([(W, 0), (W, 72), (1005, 145), (1033, 0)], fill=BLUE)
    draw.rectangle((0, 130, W, 136), fill=YELLOW)

    # Brand header.
    with Image.open(LOGO) as source:
        logo = ImageOps.contain(source.convert("RGBA"), (74, 103), Image.Resampling.LANCZOS)
    canvas.alpha_composite(logo, (42, 17))
    draw.text((132, 28), "22YARDS HOUSTON", font=font("anton-400.woff2", 43), fill=BLUE)
    draw.text((134, 77), "CRICKET ACADEMY", font=font("space-grotesk-700.woff2", 24), fill=CHARCOAL)

    # Hero photo card. The source face remains unchanged.
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle((559, 171, 1067, 911), radius=28, fill=(6, 61, 124, 52))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))
    rounded_photo(
        canvas,
        HERO,
        (548, 158, 1058, 898),
        radius=26,
        centering=(0.5, 0.5),
        brightness=1.13,
        border=7,
        border_color=WHITE,
    )
    draw.rounded_rectangle((574, 180, 799, 224), radius=19, fill=YELLOW)
    draw.text((594, 187), "INDOOR COACHING", font=font("space-grotesk-700.woff2", 20), fill=DEEP_BLUE)

    # Razor-focused benefit statement.
    draw.text((44, 184), "BUILD", font=font("anton-400.woff2", 82), fill=BLUE)
    draw.text((44, 274), "FITNESS.", font=font("anton-400.woff2", 82), fill=BLUE)
    draw.rectangle((45, 371, 284, 378), fill=YELLOW)
    draw.text((44, 401), "DEVELOP", font=font("anton-400.woff2", 69), fill=DEEP_BLUE)
    draw.text((44, 480), "CRICKET", font=font("anton-400.woff2", 69), fill=DEEP_BLUE)
    draw.text((44, 559), "SKILLS.", font=font("anton-400.woff2", 69), fill=DEEP_BLUE)

    draw.rounded_rectangle((44, 660, 513, 714), radius=24, fill=SKY)
    age_line = "U5-U13  |  BEGINNERS & INTERMEDIATE"
    age_font = fit_font("space-grotesk-700.woff2", age_line, 427, 24)
    draw.text((65, 675), age_line, font=age_font, fill=BLUE)

    draw.text((46, 747), "Structured coaching for growing players.", font=font("space-grotesk-500.woff2", 23), fill=CHARCOAL)
    draw.text((46, 786), "A pathway to match experience", font=font("space-grotesk-700.woff2", 23), fill=BLUE)
    draw.text((46, 820), "as players progress.", font=font("space-grotesk-500.woff2", 23), fill=MUTED)

    draw.rounded_rectangle((44, 858, 505, 916), radius=25, fill=YELLOW)
    cta = "REGISTER NOW"
    cta_font = font("anton-400.woff2", 31)
    cta_box = draw.textbbox((0, 0), cta, font=cta_font)
    draw.text((44 + (461 - (cta_box[2] - cta_box[0])) // 2, 870), cta, font=cta_font, fill=DEEP_BLUE)

    # Two supporting action photos demonstrate fitness and skill development.
    rounded_photo(
        canvas,
        RUNNING,
        (28, 947, 526, 1125),
        radius=20,
        centering=(0.56, 0.50),
        brightness=1.13,
        border=5,
        border_color=WHITE,
    )
    rounded_photo(
        canvas,
        BOWLING,
        (554, 947, 1052, 1125),
        radius=20,
        centering=(0.5, 0.50),
        brightness=1.13,
        border=5,
        border_color=WHITE,
    )
    draw.rounded_rectangle((48, 963, 204, 1002), radius=16, fill=BLUE)
    draw.text((65, 970), "FITNESS", font=font("space-grotesk-700.woff2", 18), fill=WHITE)
    draw.rounded_rectangle((574, 963, 724, 1002), radius=16, fill=BLUE)
    draw.text((594, 970), "SKILLS", font=font("space-grotesk-700.woff2", 18), fill=WHITE)

    # Contact footer and registration QR.
    draw.rectangle((0, 1147, W, H), fill=BLUE)
    draw.rectangle((0, 1147, W, 1155), fill=YELLOW)
    draw.text((44, 1178), "CALL OR WHATSAPP", font=font("space-grotesk-700.woff2", 23), fill=YELLOW)
    draw.text((44, 1216), PHONE, font=font("anton-400.woff2", 43), fill=WHITE)
    draw.text((44, 1272), "axon22yards.com/join", font=font("space-grotesk-500.woff2", 22), fill=WHITE)
    draw.text((704, 1191), "SCAN TO", font=font("space-grotesk-700.woff2", 20), fill=WHITE)
    draw.text((704, 1221), "REGISTER", font=font("space-grotesk-700.woff2", 20), fill=YELLOW)
    qr = qr_image(REGISTRATION_URL, 154)
    canvas.paste(qr, (884, 1172))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(OUTPUT, format="PNG", optimize=True, quality=95)
    return OUTPUT


if __name__ == "__main__":
    print(build())
