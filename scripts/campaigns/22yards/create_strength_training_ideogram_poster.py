"""Generate Ideogram strength-training artwork and compose an exact-text poster."""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

import segno
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from cricket_posts.ideogram import generate_from_prompt


ROOT = Path(__file__).resolve().parents[3]
FONT_DIR = ROOT / "assets" / "fonts"
LOGO = ROOT / "assets" / "brand" / "22yards-houston.png"
ARTWORK = ROOT / "output" / "posters" / "strength-training-ideogram-artwork.png"
OUTPUT = ROOT / "output" / "posters" / "22yards-houston-strength-training-free-trial-sept15-ideogram.png"

REGISTRATION_URL = "https://axon22yards.com/join?location=houston"
PHONE = "+1 (713) 498-2155"

W, H = 1080, 1350
WHITE = "#FFFFFF"
OFF_WHITE = "#F8FBFF"
BLUE = "#0757A6"
DEEP_BLUE = "#063D7C"
YELLOW = "#F5C400"
SKY = "#D9EDFF"
CHARCOAL = "#252A31"


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


def ideogram_prompt() -> str:
    return """
Create a premium, text-free 4:5 vertical documentary sports photograph for a
children's cricket academy strength and conditioning campaign.

Scene: a real modern indoor cricket training facility with green turf, practice
nets and bright directional sports lighting. Show a supervised youth strength
training circuit with exactly three South Asian children representing roughly
ages 5, 9 and 13. They wear plain royal-blue and sunshine-yellow athletic cricket
training kits with no words, badges or logos. The youngest child performs a safe
bodyweight squat to a low box; the middle child uses a light resistance band for
controlled rotational core work; the oldest holds a light medicine ball in an
athletic stance. One encouraging professional coach supervises their technique.
Include a cricket bat, three stumps and one red leather cricket ball subtly in the
scene to connect athletic strength with cricket skill.

Composition: concentrate the people in the right half and middle of the frame.
Keep the upper-left quadrant and lower fifth calm and uncluttered for copy that
will be added later. Use natural side and three-quarter angles rather than an
extreme close-up. Authentic, energetic, aspirational youth sports photography;
natural skin texture; realistic hands and anatomy; crisp professional detail.

Absolutely no text, letters, numbers, captions, signage, watermarks, sponsor
marks, invented logos, badges, interface elements, duplicated people, distorted
faces, malformed hands, heavy barbells, dangerous lifting or bodybuilding poses.
""".strip()


def generate_artwork() -> Path:
    load_dotenv(ROOT / ".env")
    result_path = generate_from_prompt(
        ideogram_prompt(),
        ARTWORK,
        resolution="1792x2240",
        rendering_speed="QUALITY",
    )
    return Path(result_path)


def qr_image(url: str, size: int) -> Image.Image:
    qr = segno.make(url, error="h")
    stream = BytesIO()
    qr.save(stream, kind="png", scale=12, border=2, dark=DEEP_BLUE, light=WHITE)
    stream.seek(0)
    with Image.open(stream) as source:
        return source.convert("RGB").resize((size, size), Image.Resampling.NEAREST)


def add_gradient_overlay(canvas: Image.Image) -> None:
    overlay = Image.new("RGBA", (W, 780), (0, 0, 0, 0))
    pixels = overlay.load()
    for y in range(780):
        bottom_alpha = int(max(0, (y - 550) / 230) * 210)
        for x in range(W):
            left_alpha = int(max(0, 1 - x / 690) * 225)
            alpha = min(245, max(left_alpha, bottom_alpha))
            pixels[x, y] = (6, 61, 124, alpha)
    canvas.alpha_composite(overlay, (0, 0))


def centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    typeface: ImageFont.FreeTypeFont,
    fill: str,
    *,
    x1: int,
    x2: int,
) -> None:
    box = draw.textbbox((0, 0), text, font=typeface)
    x = x1 + ((x2 - x1) - (box[2] - box[0])) // 2
    draw.text((x, y), text, font=typeface, fill=fill)


def compose() -> Path:
    if not ARTWORK.is_file():
        raise FileNotFoundError(f"Generate the Ideogram artwork first: {ARTWORK}")
    if not LOGO.is_file():
        raise FileNotFoundError(LOGO)

    with Image.open(ARTWORK) as source:
        art = ImageOps.fit(
            ImageEnhance.Brightness(source.convert("RGB")).enhance(1.06),
            (W, 780),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.47),
        )
    canvas = Image.new("RGBA", (W, H), OFF_WHITE)
    canvas.paste(art, (0, 0))
    add_gradient_overlay(canvas)
    draw = ImageDraw.Draw(canvas)

    # Brand lockup.
    with Image.open(LOGO) as source:
        logo = ImageOps.contain(source.convert("RGBA"), (70, 98), Image.Resampling.LANCZOS)
    canvas.alpha_composite(logo, (42, 27))
    draw.text((126, 37), "22YARDS HOUSTON", font=font("anton-400.woff2", 40), fill=WHITE)
    draw.text((128, 82), "CRICKET ACADEMY", font=font("space-grotesk-700.woff2", 21), fill=YELLOW)

    # Main promise, intentionally short and mobile-readable.
    draw.text((43, 170), "BETTER", font=font("anton-400.woff2", 76), fill=WHITE)
    draw.text((43, 247), "CRICKETER.", font=font("anton-400.woff2", 76), fill=WHITE)
    draw.text((43, 334), "STRONGER", font=font("anton-400.woff2", 76), fill=YELLOW)
    draw.text((43, 411), "ATHLETE.", font=font("anton-400.woff2", 76), fill=YELLOW)

    draw.rounded_rectangle((43, 520, 515, 574), radius=23, fill=BLUE)
    centered_text(
        draw,
        "U5-U13  •  EVERY AGE  •  EVERY PROGRAM",
        535,
        fit_font("space-grotesk-700.woff2", "U5-U13  •  EVERY AGE  •  EVERY PROGRAM", 430, 22),
        WHITE,
        x1=43,
        x2=515,
    )
    draw.text((44, 610), "NOT JUST CRICKET SKILLS.", font=font("space-grotesk-700.woff2", 28), fill=WHITE)
    draw.text((44, 650), "WE TRAIN THE WHOLE ATHLETE.", font=font("space-grotesk-700.woff2", 28), fill=YELLOW)

    # Clear explanation and benefit row.
    draw.rectangle((0, 780, W, 1055), fill=WHITE)
    draw.rectangle((0, 780, W, 789), fill=YELLOW)
    draw.text((43, 818), "STRENGTH TRAINING IS BUILT IN.", font=font("anton-400.woff2", 42), fill=DEEP_BLUE)
    draw.text(
        (43, 873),
        "Age-appropriate training that supports cricket development.",
        font=font("space-grotesk-500.woff2", 24),
        fill=CHARCOAL,
    )

    benefits = [
        (43, "STRENGTH\n& CORE"),
        (365, "BALANCE &\nMOVEMENT"),
        (718, "SPEED &\nCOORDINATION"),
    ]
    for x, label in benefits:
        draw.rounded_rectangle((x, 934, x + 295, 1028), radius=18, fill=SKY)
        draw.ellipse((x + 15, 958, x + 51, 994), fill=YELLOW)
        draw.line((x + 24, 976, x + 42, 976), fill=DEEP_BLUE, width=5)
        draw.text((x + 67, 949), label, font=font("space-grotesk-700.woff2", 22), fill=DEEP_BLUE, spacing=2)

    # Deadline-first CTA. September 15 is the strongest element in the footer.
    draw.rectangle((0, 1055, W, H), fill=DEEP_BLUE)
    draw.rectangle((0, 1055, W, 1064), fill=YELLOW)
    draw.text((43, 1091), "FREE TRIAL", font=font("anton-400.woff2", 48), fill=WHITE)
    draw.text((43, 1144), "CLAIM YOUR SPOT BY", font=font("space-grotesk-700.woff2", 25), fill=WHITE)
    draw.text((43, 1179), "SEPTEMBER 15", font=font("anton-400.woff2", 61), fill=YELLOW)
    draw.text((43, 1252), f"CALL OR WHATSAPP  {PHONE}", font=font("space-grotesk-700.woff2", 23), fill=WHITE)
    draw.text((43, 1288), "axon22yards.com/join", font=font("space-grotesk-500.woff2", 21), fill=WHITE)

    qr = qr_image(REGISTRATION_URL, 178)
    draw.rounded_rectangle((855, 1124, 1047, 1316), radius=16, fill=WHITE)
    canvas.paste(qr, (862, 1131))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(OUTPUT, format="PNG", optimize=True, quality=95)
    return OUTPUT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="Call Ideogram before composing")
    args = parser.parse_args()
    if args.generate:
        generate_artwork()
    print(compose())


if __name__ == "__main__":
    main()
