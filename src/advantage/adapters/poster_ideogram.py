"""Turn a CampaignRequest into a poster via Ideogram artwork + deterministic stamping.

Companion to `poster.py`'s free `compose()` path, not a replacement for it: this
is the paid path, used when `IDEOGRAM_API_KEY` is configured (see `poster.py`'s
`produce_poster` routing/fallback). Per AGENTS.md, Ideogram is asked to render
the *scene only* -- text-free, no logos, no watermarks -- and every piece of
exact business copy (name, offer, audience, brief, contact phone, destination
URL) is stamped on top afterward with PIL, verbatim from the request, the same
"never invent copy" discipline `poster.py`'s `build_poster_content()` already
documents. The compositing approach (scrim over a photo band, a white info
band, a dark footer band with a QR) follows
`scripts/campaigns/22yards/create_strength_training_ideogram_poster.py`, the
proven working example this module generalizes away from one hardcoded
business.

Two small JSON sidecar files ride alongside the rendered PNG so
`application/verification.py` can check this path without threading extra
return values through `poster.py`'s fixed `(CampaignArtifact, ComposeResult |
None)` return shape (which `orchestrator.py` -- out of scope for this change
-- already calls positionally):

* `<poster>.stamp.json` -- written by `_stamp()` below: the exact strings that
  were stamped, and any that had to be truncated to fit their safe box.
* `<poster>.fallback.json` -- written by `poster.py` when it had to fall back
  to `compose()` (missing key or a failed Ideogram call): the human-readable
  reason, surfaced as a non-blocking verification finding.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

import segno
from PIL import Image, ImageDraw, ImageFont, ImageOps

from cricket_posts.ideogram import generate_from_prompt

from ..domain.models import (
    CampaignArtifact,
    CampaignRequest,
    CreativeDecision,
    CreativeFormat,
    CreativePlan,
    PosterStyle,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FONT_DIR = REPO_ROOT / "assets" / "fonts"

#: Poster canvas -- matches poster.py / AGENTS.md's 1080x1350 (Instagram Feed 4:5).
W, H = 1080, 1350
PHOTO_H = 760
INFO_TOP = PHOTO_H
INFO_H = 270
FOOTER_TOP = INFO_TOP + INFO_H

#: No per-request brand palette field exists on CampaignRequest (same gap
#: poster.py's build_brand_profile() docstring notes for BrandProfile.palette),
#: so a fixed, deterministic default is used rather than inventing one.
WHITE = "#FFFFFF"
OFF_WHITE = "#F7F9FC"
INK = "#12161C"
DEEP = "#0B3B66"
ACCENT = "#F4B400"

#: Minimum distance stamped text must keep from every canvas edge.
SAFE_MARGIN = 48


class PosterAdapterError(RuntimeError):
    """Raised when an Ideogram poster cannot be generated, downloaded, or stamped."""


@dataclass(frozen=True)
class StampedPoster:
    """`produce_ideogram_poster()`'s full result: the artifact plus what was stamped."""

    artifact: CampaignArtifact
    stamped_copy: list[str] = field(default_factory=list)
    #: Any stamped strings that had to be truncated to stay inside SAFE_MARGIN.
    overflow: list[str] = field(default_factory=list)


#: One art-direction preset per PosterStyle. Pure scene/mood language --
#: nothing here ever asks Ideogram to render text (see build_art_prompt()).
_PRESETS: dict[PosterStyle, str] = {
    PosterStyle.PHOTOREAL: (
        "authentic documentary-style sports photography: real people, natural "
        "directional lighting, true-to-life color grading, a candid athletic "
        "moment captured as it actually happened"
    ),
    PosterStyle.BOLD_GRAPHIC: (
        "high-contrast, bold sports photography: dramatic rim lighting, punchy "
        "saturated color, a dynamic low-angle action moment with poster-grade "
        "energy and strong graphic shapes in the light and shadow"
    ),
    PosterStyle.WARM_LIFESTYLE: (
        "warm, golden-hour lifestyle photography: soft natural light, a gentle "
        "candid family-and-community mood, inviting and approachable rather "
        "than intense"
    ),
    PosterStyle.PREMIUM_MINIMAL: (
        "premium minimal editorial photography: clean uncluttered composition, "
        "soft studio-quality light, a refined muted palette, and a single clear "
        "focal subject with generous breathing room around it"
    ),
}


def _resolve_style(poster_style: PosterStyle | None) -> PosterStyle:
    """Default to PHOTOREAL -- the safest generic choice for an unknown small business."""
    return poster_style or PosterStyle.PHOTOREAL


def build_art_prompt(request: CampaignRequest) -> str:
    """Deterministic Ideogram prompt: scene/mood only, never business copy as text.

    Always ends with an explicit no-text/no-logo/no-watermark constraint and a
    4:5 vertical framing instruction with lower-third negative space for the
    copy block `_stamp()` adds afterward -- true for every PosterStyle.
    """
    style = _resolve_style(request.poster_style)
    scene = _PRESETS[style]

    parts = [
        f"Create a premium, text-free 4:5 vertical photograph of a real scene for "
        f"{request.business_name.strip()}, a real local business.",
        f"Art direction: {scene}.",
    ]
    if request.audience and request.audience.strip():
        parts.append(f"The scene should feel relevant to this audience: {request.audience.strip()}.")
    if request.location and request.location.strip():
        parts.append(f"Setting/location context: {request.location.strip()}.")
    if request.art_direction_notes and request.art_direction_notes.strip():
        parts.append(
            "Additional scene notes from the business owner (about the subject/scene "
            f"only, not any wording to render): {request.art_direction_notes.strip()}"
        )
    parts.append(
        "Composition: strict 4:5 vertical portrait framing (matching a 1080x1350 "
        "canvas). Keep the lower third of the frame calm and visually uncluttered -- "
        "it is reserved as negative space for a text/copy block that will be added "
        "afterward. Do not crowd the lower third with subjects, props, or clutter."
    )
    parts.append(
        "Absolutely no text, no words, no letters, no numbers, no captions, no "
        "signage, no logos, no watermarks, no invented brand marks, no UI or "
        "interface elements -- nothing resembling writing anywhere in the image."
    )
    parts.append(
        "Photorealistic, natural anatomy, realistic hands and faces, no distorted "
        "limbs, no duplicated people, no visual artifacts."
    )
    return "\n\n".join(parts)


def describe_plan(request: CampaignRequest) -> CreativePlan:
    """Pure, no-API-call explanation of the Ideogram poster path's decisions."""
    style = _resolve_style(request.poster_style)
    decisions: list[CreativeDecision] = []

    if request.poster_style is not None:
        decisions.append(
            CreativeDecision(
                choice=f"Art-direction preset: {style.value}",
                reason="The owner selected this poster_style for the artwork's mood and lighting.",
            )
        )
    else:
        decisions.append(
            CreativeDecision(
                choice=f"Art-direction preset: {style.value} (default)",
                reason="No poster_style was supplied; photoreal is the safest generic choice for an unknown small business.",
            )
        )
    decisions.append(
        CreativeDecision(
            choice="Ideogram generates text-free scene artwork only",
            reason=(
                "AGENTS.md requires Ideogram artwork to stay text-free; exact business "
                "copy (name, offer, audience, contact, URL) is stamped deterministically "
                "afterward so dates, phone numbers, and links are always correct -- never "
                "left to the image model to render."
            ),
        )
    )
    if request.destination_url and request.destination_url.strip():
        decisions.append(
            CreativeDecision(
                choice="Include a scannable QR code",
                reason=f"destination_url is set ({request.destination_url}); a QR gets a phone straight there.",
            )
        )
    else:
        decisions.append(
            CreativeDecision(choice="No QR code", reason="No destination_url was supplied on the request.")
        )
    if request.logo_asset and request.logo_asset.local_ref:
        decisions.append(
            CreativeDecision(
                choice="Include the supplied logo",
                reason="request.logo_asset.local_ref is present.",
            )
        )
    else:
        decisions.append(
            CreativeDecision(choice="No logo", reason="No logo asset was supplied on the request.")
        )
    return CreativePlan(format=CreativeFormat.POSTER, feel=style.value, decisions=decisions)


# --- sidecar manifests ------------------------------------------------------
# See module docstring: these let verification.py check the Ideogram path
# without changing poster.py's fixed (CampaignArtifact, ComposeResult | None)
# return shape that orchestrator.py already calls positionally.


def stamp_manifest_path(poster_path: Path | str) -> Path:
    return Path(poster_path).with_suffix(".stamp.json")


def read_stamp_manifest(poster_path: Path | str) -> dict[str, list[str]] | None:
    path = stamp_manifest_path(poster_path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return {
        "stamped_copy": [str(value) for value in (data.get("stamped_copy") or [])],
        "overflow": [str(value) for value in (data.get("overflow") or [])],
    }


def _write_stamp_manifest(poster_path: Path, stamped_copy: list[str], overflow: list[str]) -> None:
    manifest = {"stamped_copy": stamped_copy, "overflow": overflow}
    stamp_manifest_path(poster_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def fallback_marker_path(poster_path: Path | str) -> Path:
    return Path(poster_path).with_suffix(".fallback.json")


def write_fallback_marker(poster_path: Path | str, reason: str) -> None:
    fallback_marker_path(poster_path).write_text(
        json.dumps({"fallback": True, "reason": reason}), encoding="utf-8"
    )


def read_fallback_reason(poster_path: Path | str) -> str | None:
    path = fallback_marker_path(poster_path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "Poster generation fell back to the offline compose() pipeline (reason unavailable)."
    reason = data.get("reason")
    return str(reason) if reason else "Poster generation fell back to the offline compose() pipeline."


# --- drawing helpers ---------------------------------------------------------


def _clip(value: str, limit: int) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[:limit].rstrip()


def _font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / filename), size=size)


def _fit_font(filename: str, text: str, width: int, start: int, floor: int = 16) -> ImageFont.FreeTypeFont:
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for size in range(start, floor - 1, -1):
        candidate = _font(filename, size)
        box = probe.textbbox((0, 0), text, font=candidate)
        if box[2] - box[0] <= width:
            return candidate
    return _font(filename, floor)


def _wrap_lines(
    draw: ImageDraw.ImageDraw, text: str, font_file: str, size: int, max_width: int, max_lines: int
) -> tuple[list[str], ImageFont.FreeTypeFont, bool]:
    """Greedy word-wrap. Returns (lines, font, truncated) -- truncated is True
    only if real content had to be cut to make it fit within max_lines."""
    typeface = _font(font_file, size)
    words = text.split()
    if not words:
        return [], typeface, False

    def width_of(candidate: str) -> int:
        box = draw.textbbox((0, 0), candidate, font=typeface)
        return box[2] - box[0]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if width_of(candidate) <= max_width:
            current = candidate
            continue
        lines.append(current)
        current = word
        if len(lines) == max_lines:
            break
    else:
        lines.append(current)
        return lines, typeface, False

    # The loop broke early: more words remained than max_lines allows. Mark
    # the last committed line with an ellipsis, shrinking word-by-word until
    # it (plus the ellipsis) fits.
    last = lines[-1] if lines else current
    while width_of(last + "…") > max_width and " " in last:
        last = last.rsplit(" ", 1)[0]
    if lines:
        lines[-1] = last.rstrip() + "…"
    else:
        lines = [last.rstrip() + "…"]
    return lines, typeface, True


def _check_fit(
    draw: ImageDraw.ImageDraw,
    text: str,
    typeface: ImageFont.FreeTypeFont,
    x1: int,
    x2_allowed: int,
    overflow: list[str],
) -> None:
    """Measure the drawn text box and record it as overflow if it breaches the
    safe margin -- the valuable check verification.py reads back."""
    box = draw.textbbox((x1, 0), text, font=typeface)
    if (box[2] > x2_allowed + 1 or box[0] < 0) and text not in overflow:
        overflow.append(text)


def _qr_image(url: str, size: int) -> Image.Image:
    qr = segno.make(url, error="h")
    stream = BytesIO()
    qr.save(stream, kind="png", scale=10, border=2, dark=DEEP, light=WHITE)
    stream.seek(0)
    with Image.open(stream) as source:
        return source.convert("RGB").resize((size, size), Image.Resampling.NEAREST)


def _add_gradient_scrim(canvas: Image.Image) -> None:
    band = 420
    top = PHOTO_H - band
    overlay = Image.new("RGBA", (W, band), (0, 0, 0, 0))
    pixels = overlay.load()
    for y in range(band):
        alpha = int(min(235, max(0, (y / band) ** 1.4 * 235)))
        for x in range(W):
            pixels[x, y] = (8, 20, 36, alpha)
    canvas.alpha_composite(overlay, (0, top))


def _stamp(request: CampaignRequest, artwork_path: Path, destination: Path) -> StampedPoster:
    """Composite text-free Ideogram artwork + deterministic stamped copy -> poster.png."""
    if not artwork_path.is_file():
        raise PosterAdapterError(f"Ideogram artwork not found at {artwork_path}.")

    business_name = _clip(request.business_name, 60)
    headline = _clip(request.offer_text or request.business_name, 90)
    subtitle = _clip(request.audience, 90) if request.audience and request.audience.strip() else ""
    body = _clip(request.brief_text, 260)
    contact = _clip(request.contact_phone, 60) if request.contact_phone and request.contact_phone.strip() else ""
    url = (
        _clip(request.destination_url, 90)
        if request.destination_url and request.destination_url.strip()
        else ""
    )

    stamped_copy = [value for value in (business_name, headline, subtitle, body, contact, url) if value]
    overflow: list[str] = []

    try:
        with Image.open(artwork_path) as source:
            art = ImageOps.fit(
                source.convert("RGB"),
                (W, PHOTO_H),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.45),
            )
    except Exception as exc:
        raise PosterAdapterError(f"Ideogram artwork at {artwork_path} is not a readable image: {exc}") from exc

    canvas = Image.new("RGBA", (W, H), OFF_WHITE)
    canvas.paste(art, (0, 0))
    _add_gradient_scrim(canvas)
    draw = ImageDraw.Draw(canvas)

    # --- brand lockup (logo + business name) over the photo, top-left -------
    text_left = SAFE_MARGIN
    if request.logo_asset and request.logo_asset.local_ref and Path(request.logo_asset.local_ref).is_file():
        with Image.open(request.logo_asset.local_ref) as logo_source:
            logo = ImageOps.contain(logo_source.convert("RGBA"), (64, 88), Image.Resampling.LANCZOS)
        canvas.alpha_composite(logo, (SAFE_MARGIN, 30))
        text_left = SAFE_MARGIN + logo.width + 16

    name_font = _fit_font("anton-400.woff2", business_name, W - text_left - SAFE_MARGIN, 40)
    draw.text((text_left, 44), business_name, font=name_font, fill=WHITE)
    _check_fit(draw, business_name, name_font, text_left, W - SAFE_MARGIN, overflow)

    # --- headline + subtitle over the scrim, bottom of the photo band -------
    headline_lines, headline_font, headline_truncated = _wrap_lines(
        draw, headline, "anton-400.woff2", 58, W - 2 * SAFE_MARGIN, max_lines=2
    )
    if headline_truncated:
        overflow.append(headline)
    y = PHOTO_H - 60 - 66 * max(1, len(headline_lines)) - (40 if subtitle else 0)
    for line in headline_lines:
        draw.text((SAFE_MARGIN, y), line, font=headline_font, fill=WHITE)
        _check_fit(draw, line, headline_font, SAFE_MARGIN, W - SAFE_MARGIN, overflow)
        y += 66

    if subtitle:
        subtitle_upper = subtitle.upper()
        subtitle_font = _fit_font("space-grotesk-700.woff2", subtitle_upper, W - 2 * SAFE_MARGIN, 26)
        draw.text((SAFE_MARGIN, y + 6), subtitle_upper, font=subtitle_font, fill=ACCENT)
        _check_fit(draw, subtitle_upper, subtitle_font, SAFE_MARGIN, W - SAFE_MARGIN, overflow)

    # --- info band: the raw brief, verbatim -----------------------------
    draw.rectangle((0, INFO_TOP, W, INFO_TOP + INFO_H), fill=WHITE)
    draw.rectangle((0, INFO_TOP, W, INFO_TOP + 8), fill=ACCENT)
    body_lines, body_font, body_truncated = _wrap_lines(
        draw, body, "space-grotesk-500.woff2", 26, W - 2 * SAFE_MARGIN, max_lines=5
    )
    if body_truncated:
        overflow.append(body)
    by = INFO_TOP + 40
    for line in body_lines:
        draw.text((SAFE_MARGIN, by), line, font=body_font, fill=INK)
        _check_fit(draw, line, body_font, SAFE_MARGIN, W - SAFE_MARGIN, overflow)
        by += 36

    # --- footer band: contact + destination + QR ----------------------------
    draw.rectangle((0, FOOTER_TOP, W, H), fill=DEEP)
    draw.rectangle((0, FOOTER_TOP, W, FOOTER_TOP + 8), fill=ACCENT)
    fy = FOOTER_TOP + 40
    footer_right = W - SAFE_MARGIN
    if url:
        footer_right = W - SAFE_MARGIN - 190  # reserve room for the QR block

    if contact:
        contact_font = _fit_font("space-grotesk-700.woff2", contact, footer_right - SAFE_MARGIN, 30)
        draw.text((SAFE_MARGIN, fy), contact, font=contact_font, fill=WHITE)
        _check_fit(draw, contact, contact_font, SAFE_MARGIN, footer_right, overflow)
        fy += 46

    if url:
        url_font = _fit_font("space-grotesk-500.woff2", url, footer_right - SAFE_MARGIN, 24)
        draw.text((SAFE_MARGIN, fy), url, font=url_font, fill=WHITE)
        _check_fit(draw, url, url_font, SAFE_MARGIN, footer_right, overflow)

        qr = _qr_image(request.destination_url, 160)
        qr_x = W - SAFE_MARGIN - 160
        qr_y = H - SAFE_MARGIN - 160
        draw.rounded_rectangle((qr_x - 10, qr_y - 10, qr_x + 170, qr_y + 170), radius=14, fill=WHITE)
        canvas.paste(qr, (qr_x, qr_y))

    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(destination, format="PNG", optimize=True)

    artifact = CampaignArtifact(
        format=CreativeFormat.POSTER, file_path=str(destination), width=W, height=H
    )
    _write_stamp_manifest(destination, stamped_copy, overflow)
    return StampedPoster(artifact=artifact, stamped_copy=stamped_copy, overflow=overflow)


def produce_ideogram_poster(request: CampaignRequest, *, workdir: Path) -> StampedPoster:
    """Generate text-free Ideogram artwork, then stamp exact copy on top.

    Raises PosterAdapterError on any failure (missing key, a failed/blocked
    generation call, a corrupt download, or a stamping failure) -- `poster.py`
    catches this (and any other exception) to fall back to compose().
    """
    if request.format != CreativeFormat.POSTER:
        raise PosterAdapterError(
            "produce_ideogram_poster requires CampaignRequest.format == CreativeFormat.POSTER, "
            f"got {request.format.value!r}."
        )

    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    artwork_path = workdir / "artwork.png"
    destination = workdir / "poster.png"

    try:
        generate_from_prompt(
            build_art_prompt(request),
            artwork_path,
            resolution="1792x2240",
            rendering_speed="QUALITY",
        )
    except Exception as exc:
        raise PosterAdapterError(f"Ideogram artwork generation failed: {exc}") from exc

    try:
        return _stamp(request, artwork_path, destination)
    except PosterAdapterError:
        raise
    except Exception as exc:
        raise PosterAdapterError(f"Stamping the Ideogram poster failed: {exc}") from exc
