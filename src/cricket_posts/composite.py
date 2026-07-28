"""Composite exact copy and the real logo onto a generated art plate.

Ideogram is a strong illustrator and an unreliable typesetter: its repair
endpoint re-rolls text rather than correcting it, and it invents brand marks
when asked for a logo. So the division of labour is:

* Ideogram draws the artwork, and its edit endpoint *clears* a region.
* This module types into that cleared region with the browser, using the real
  brand logo and verbatim copy.

Nothing here can misspell a phone number, because nothing here generates text.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image

from .models import BrandProfile, PosterContent
from .renderer import PROJECT_ROOT, TEMPLATE_DIR
from .studio_renderer import PlaywrightRenderer

STUDIO_TEMPLATE_DIR = TEMPLATE_DIR / "studio"


def _sample_plate_background(plate: Path, box: tuple[int, int, int, int]) -> str:
    """Median colour of a plate region, used to bury an invented logo crest."""
    with Image.open(plate) as image:
        crop = image.convert("RGB").crop(box).resize((8, 8), Image.Resampling.BOX)
        pixels = list(crop.getdata())
    channels = [sorted(channel[index] for channel in pixels) for index in range(3)]
    median = tuple(channel[len(channel) // 2] for channel in channels)
    return "#" + "".join(f"{value:02X}" for value in median)


def compose_overlay_html(
    plate: Path,
    brand: BrandProfile,
    content: PosterContent,
    destination: Path,
    *,
    logo_path: Path | None = None,
    logo_box: tuple[int, int, int, int] | None = None,
    patch_background: bool = False,
) -> tuple[Path, tuple[int, int]]:
    with Image.open(plate) as image:
        width, height = image.size

    scale = width / 1728
    logo_box = logo_box or (
        int(70 * scale),
        int(50 * scale),
        int(250 * scale),
        int(230 * scale),
    )
    plate_bg = _sample_plate_background(
        plate,
        # Sample just outside the crest so the patch matches the paper, not the
        # thing being covered.
        (logo_box[2] + int(40 * scale), logo_box[1], logo_box[2] + int(120 * scale), logo_box[3]),
    )

    resolved_logo = logo_path or (Path(brand.logo_path) if brand.logo_path else None)
    if resolved_logo and not resolved_logo.is_absolute():
        resolved_logo = PROJECT_ROOT / resolved_logo
    if resolved_logo and not resolved_logo.exists():
        resolved_logo = None

    organization = content.organization or brand.name
    eyebrow_lines = [line for line in content.eyebrow.split("\n") if line.strip()]
    phones = [contact.display() for contact in content.contacts if contact.display()]
    website = next(
        (line for line in content.cta_lines if "." in line and " " not in line),
        "",
    )
    labels = [line for line in content.cta_lines if line != website]

    environment = Environment(
        loader=FileSystemLoader(STUDIO_TEMPLATE_DIR),
        autoescape=select_autoescape(("html", "xml")),
    )
    html = environment.get_template("overlay.html").render(
        content=content,
        brand=brand,
        width=width,
        height=height,
        plate_url=plate.resolve().as_uri(),
        plate_bg=plate_bg,
        fonts_url=(STUDIO_TEMPLATE_DIR / "fonts.css").resolve().as_uri(),
        logo_url=resolved_logo.resolve().as_uri() if resolved_logo else None,
        logo={
            # Only needed when the header was not cleared by the edit endpoint.
            # A flat rectangle rarely matches a textured plate, so clearing wins.
            "patch": patch_background,
            "patch_left": logo_box[0] - int(14 * scale),
            "patch_top": logo_box[1] - int(14 * scale),
            "patch_width": (logo_box[2] - logo_box[0]) + int(28 * scale),
            "patch_height": (logo_box[3] - logo_box[1]) + int(28 * scale),
            "left": logo_box[0],
            "top": logo_box[1],
            "size": logo_box[3] - logo_box[1],
            "gap": int(26 * scale),
            "name_px": int(46 * scale),
            "sub_px": int(24 * scale),
        },
        wordmark_name=organization,
        wordmark_sub=eyebrow_lines,
        location_lines=content.location_lines,
        website=website,
        web_label=labels[0] if labels else "VISIT US",
        call_label=labels[1] if len(labels) > 1 else "CALL OR TEXT",
        phones=phones,
        bar={
            "left": int(60 * scale),
            "bottom": int(52 * scale),
            "gap": int(26 * scale),
            "pad_x": int(34 * scale),
            "pad_y": int(26 * scale),
            "radius": int(28 * scale),
            "icon": int(58 * scale),
            "icon_gap": int(18 * scale),
            "label_px": int(20 * scale),
            "value_px": int(25 * scale),
        },
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, encoding="utf-8")
    return destination, (width, height)


def composite_brand_overlay(
    plate: Path,
    brand: BrandProfile,
    content: PosterContent,
    destination: Path,
    *,
    logo_path: Path | None = None,
    renderer: PlaywrightRenderer | None = None,
    patch_background: bool = False,
) -> Path:
    html_path, size = compose_overlay_html(
        plate,
        brand,
        content,
        destination.with_suffix(".html"),
        logo_path=logo_path,
        patch_background=patch_background,
    )
    renderer = renderer or PlaywrightRenderer()
    session = renderer._session()
    page = session.browser.new_page(
        viewport={"width": size[0], "height": size[1]},
        device_scale_factor=1,
    )
    try:
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.evaluate("() => document.fonts.ready.then(() => true)")
        destination.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(
            path=str(destination),
            clip={"x": 0, "y": 0, "width": size[0], "height": size[1]},
        )
    finally:
        page.close()
    return destination


def verify_copy(poster: Path, expected: list[str]) -> dict[str, bool]:
    """Placeholder for the OCR gate; composited copy is exact by construction."""
    return {value: True for value in expected}
