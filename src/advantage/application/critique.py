"""An independent review of the finished creative, before the owner sees it.

Deliberately separate from ``verification.py``. That module answers "is this
file structurally correct" -- right dimensions, no missing or clipped copy.
This module answers "is this any good, and what went wrong", which is a
different question that structural checks cannot reach: a poster can be
exactly 1080x1350 with every string present and still be two-thirds empty
white space, which is precisely the failure this module exists to catch.

Two layers, in this order:

1. **Deterministic pixel measurements** (Pillow only, no network). These are
   the reliability backbone: they run with no API key, produce a *number*
   rather than an opinion, and are what actually caught the reported
   "poster looks empty" case.
2. **An optional vision pass.** When a model is reachable it looks at the
   rendered PNG alongside those measurements and the planner's own decisions,
   and writes the owner-facing "what I did / why / where I struggled" text.

The merge rule matters: a measured defect is always reported, even when the
model does not mention it. The model can add nuance to a finding but it can
never talk the system out of one, because the number came from the pixels and
the model's opinion did not. ``model_reviewed`` is True only when a real
vision response came back and validated, so the UI never implies the artwork
was looked at when it was not.

Never raises. It sits in the middle of a successful generate path; a failure
to *describe* a creative must not discard the creative.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..domain.models import (
    CampaignArtifact,
    CampaignRequest,
    CreativeCritique,
    CreativeFormat,
    CreativePlan,
    VerificationResult,
)

# --- deterministic thresholds ----------------------------------------------------
#
# Every number below is a judgement call, so each one is named and explained
# rather than buried as a literal. They are deliberately forgiving: this pass
# should flag the poster a human would immediately call empty, not nitpick a
# deliberately minimal design.

#: A poster is sampled on a grid rather than pixel-by-pixel -- 1080x1350 is
#: ~1.5M pixels and we only need the broad distribution of colour.
SAMPLE_GRID = 48

#: Colours are bucketed this coarsely before counting, so imperceptible
#: gradient/JPEG noise doesn't read as "varied".
COLOUR_BUCKET = 24

#: A *single* colour covering more than this is an obviously blank render.
#: Kept high because the interesting case is rarely one colour: the reported
#: poster was white body + coloured footer, neither of which dominated alone.
FLAT_CANVAS_LIMIT = 0.45

#: Any colour bucket covering at least this much canvas counts as a "large
#: uniform block" (a band, a panel, an empty margin) rather than detail.
UNIFORM_BLOCK_MIN = 0.08

#: When large uniform blocks *together* cover this much of the poster, it
#: reads as empty even though no single colour dominates. This is the check
#: that actually catches the reported failure: a flat white body band plus a
#: flat coloured footer summed to roughly half the canvas.
UNIFORM_TOTAL_LIMIT = 0.35

#: The same idea applied to the bottom third alone, which the whole-canvas
#: number can miss when the photo above it is busy. The reported poster's
#: footer was a large coloured band holding one short phone number.
FLAT_BAND_LIMIT = 0.70

#: Fewer distinct bucketed colours than this across the whole canvas means the
#: image is essentially flat colour -- usually a failed or blank render.
MIN_DISTINCT_COLOURS = 6


class ImageMeasurements(BaseModel):
    """What the deterministic pass actually measured. Numbers, not opinions."""

    model_config = ConfigDict(extra="forbid")

    readable: bool
    flat_share: float = 0.0
    uniform_share: float = 0.0
    bottom_band_flat_share: float = 0.0
    distinct_colours: int = 0
    dominant_hex: str = ""


def measure_poster(path: Path) -> ImageMeasurements:
    """Measure flatness/emptiness of a rendered poster.

    Returns ``readable=False`` rather than raising when the file is missing or
    not a decodable image -- the caller still owes the owner a critique.
    """
    try:
        from PIL import Image

        with Image.open(path) as source:
            image = source.convert("RGB").resize((SAMPLE_GRID, SAMPLE_GRID))
            pixels = list(image.getdata())
    except Exception:
        return ImageMeasurements(readable=False)

    if not pixels:
        return ImageMeasurements(readable=False)

    def bucket(pixel: tuple[int, int, int]) -> tuple[int, int, int]:
        return tuple(channel // COLOUR_BUCKET for channel in pixel)  # type: ignore[return-value]

    counts: dict[tuple[int, int, int], int] = {}
    for pixel in pixels:
        key = bucket(pixel)
        counts[key] = counts.get(key, 0) + 1

    dominant_key, dominant_count = max(counts.items(), key=lambda item: item[1])
    dominant_rgb = tuple(channel * COLOUR_BUCKET for channel in dominant_key)

    # The bottom third, measured separately: a big empty footer band is a
    # distinct failure mode from an empty poster overall.
    band_start = (SAMPLE_GRID * 2 // 3) * SAMPLE_GRID
    band = pixels[band_start:]
    band_counts: dict[tuple[int, int, int], int] = {}
    for pixel in band:
        key = bucket(pixel)
        band_counts[key] = band_counts.get(key, 0) + 1
    band_flat = (max(band_counts.values()) / len(band)) if band else 0.0

    # Large uniform blocks summed together: the empty-poster signal that a
    # single-colour measurement misses (white body band + coloured footer).
    uniform = sum(
        count for count in counts.values() if count / len(pixels) >= UNIFORM_BLOCK_MIN
    )

    return ImageMeasurements(
        readable=True,
        flat_share=round(dominant_count / len(pixels), 3),
        uniform_share=round(uniform / len(pixels), 3),
        bottom_band_flat_share=round(band_flat, 3),
        distinct_colours=len(counts),
        dominant_hex="#%02X%02X%02X" % dominant_rgb,
    )


def deterministic_findings(
    artifact: CampaignArtifact, measurements: ImageMeasurements
) -> list[str]:
    """Owner-readable findings derived only from measured numbers.

    Each finding quotes the number it is based on: "the lower third is 91% one
    flat colour" is actionable, "looks empty" is not.
    """
    findings: list[str] = []

    if artifact.format != CreativeFormat.POSTER:
        return findings

    if not measurements.readable:
        findings.append(
            "I could not open the rendered poster to inspect it, so I have not "
            "checked how it actually looks."
        )
        return findings

    if measurements.flat_share >= FLAT_CANVAS_LIMIT:
        findings.append(
            f"{measurements.flat_share:.0%} of the poster is a single flat colour "
            f"({measurements.dominant_hex}). It will read as empty -- worth "
            "regenerating with more artwork or larger copy."
        )
    elif measurements.uniform_share >= UNIFORM_TOTAL_LIMIT:
        findings.append(
            f"{measurements.uniform_share:.0%} of the poster is large flat blocks of "
            "colour rather than artwork or copy. It will read as empty -- try "
            "regenerating with more of the scene showing, or larger text."
        )
    if measurements.bottom_band_flat_share >= FLAT_BAND_LIMIT:
        findings.append(
            f"The lower third is {measurements.bottom_band_flat_share:.0%} one flat "
            "colour -- the footer band is mostly empty space around a short line of text."
        )
    if measurements.distinct_colours < MIN_DISTINCT_COLOURS:
        findings.append(
            f"Only {measurements.distinct_colours} distinct colour regions across the "
            "whole poster, which usually means the artwork did not render as intended."
        )
    return findings


# --- optional vision pass --------------------------------------------------------

REVIEW_INSTRUCTIONS = """\
You are reviewing an advertising poster your own system just produced, before
the small-business owner sees it. Be useful and blunt, not reassuring.

You are given the poster image, automated measurements of it, and the design
decisions the system made.

Return three lists:
* "did" -- what the system actually did to build this creative.
* "why" -- the reasoning behind those choices, in the owner's terms.
* "struggled" -- what is weak, awkward, or went wrong. This is the most
  important list. An owner reading a visibly poor poster alongside an empty
  "struggled" list will stop trusting everything else you say. If the
  measurements report large flat areas, say so plainly.

Rules: describe only what is actually visible in the image. Never claim text,
logos, or elements you cannot see. Never invent business facts -- no prices,
dates, phone numbers, statistics, or testimonials. Keep each entry to one
short sentence.
"""


class _VisionReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(default="", max_length=400)
    did: list[str] = Field(default_factory=list)
    why: list[str] = Field(default_factory=list)
    struggled: list[str] = Field(default_factory=list)


def _encode_image(path: Path) -> str | None:
    try:
        return base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return None


def _vision_review(
    artifact: CampaignArtifact,
    request: CampaignRequest,
    plan: CreativePlan | None,
    measurements: ImageMeasurements,
    *,
    client: Any | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> _VisionReview | None:
    """Ask a vision model to describe and criticise the poster.

    Returns ``None`` on any failure at all -- the caller then reports the
    deterministic findings alone with ``model_reviewed=False``.
    """
    if artifact.format != CreativeFormat.POSTER or not measurements.readable:
        return None

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key and client is None:
        return None

    encoded = _encode_image(Path(artifact.file_path))
    if encoded is None:
        return None

    decisions = (
        "\n".join(f"- {d.choice}: {d.reason}" for d in plan.decisions) if plan else "(none recorded)"
    )
    context = (
        f"Business: {request.business_name}\n"
        f"Format: {artifact.format.value} at {artifact.width}x{artifact.height}\n"
        f"Automated measurements: {measurements.flat_share:.0%} of the canvas is one flat "
        f"colour; the lower third is {measurements.bottom_band_flat_share:.0%} flat; "
        f"{measurements.distinct_colours} distinct colour regions.\n"
        f"Design decisions the system made:\n{decisions}"
    )

    try:
        openai_client = client
        if openai_client is None:
            from openai import OpenAI

            openai_client = OpenAI(api_key=key)

        response = openai_client.responses.parse(
            model=model or os.getenv("OPENAI_MODEL", "gpt-5.4"),
            instructions=REVIEW_INSTRUCTIONS,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": context},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{encoded}",
                        },
                    ],
                }
            ],
            text_format=_VisionReview,
            reasoning={"effort": "low"},
        )
        parsed = response.output_parsed
        if parsed is None or not isinstance(parsed, _VisionReview):
            return None
        return parsed
    except Exception:
        return None


# --- public entry point ----------------------------------------------------------


def review_creative(
    artifact: CampaignArtifact,
    request: CampaignRequest,
    plan: CreativePlan | None = None,
    verification: VerificationResult | None = None,
    *,
    client: Any | None = None,
) -> CreativeCritique:
    """Review a finished creative and report what was done, why, and what is weak.

    Never raises. With no model available the result is still useful: the
    deterministic measurements carry the ``struggled`` list and the plan
    carries ``did``/``why``.
    """
    try:
        measurements = (
            measure_poster(Path(artifact.file_path))
            if artifact.format == CreativeFormat.POSTER
            else ImageMeasurements(readable=False)
        )
    except Exception:
        measurements = ImageMeasurements(readable=False)

    measured = deterministic_findings(artifact, measurements)

    vision = None
    try:
        vision = _vision_review(artifact, request, plan, measurements, client=client)
    except Exception:
        vision = None

    # What of the owner's own information actually reached the artwork. Read
    # from the renderer's stamped-copy record rather than re-derived from the
    # request, so this answers "did it use what I gave it" honestly -- a field
    # the renderer silently dropped will not appear here.
    information: list[str] = []
    if artifact.format == CreativeFormat.POSTER:
        try:
            from ..adapters.poster_ideogram import read_stamp_manifest

            manifest = read_stamp_manifest(artifact.file_path)
            if manifest:
                information = list(manifest.get("stamped_copy") or [])
        except Exception:
            information = []

    # `did`/`why` fall back to the planner's own record so the critique agrees
    # with the plan panel instead of contradicting it.
    plan_did = [d.choice for d in plan.decisions] if plan else []
    plan_why = [d.reason for d in plan.decisions] if plan else []

    did = (vision.did if vision and vision.did else plan_did)[:6]
    why = (vision.why if vision and vision.why else plan_why)[:6]

    # The merge that matters: measured defects are appended unconditionally,
    # so a model that returns an empty `struggled` for a measurably empty
    # poster cannot suppress the finding.
    struggled: list[str] = []
    if vision and vision.struggled:
        struggled.extend(vision.struggled[:6])
    for finding in measured:
        if finding not in struggled:
            struggled.append(finding)

    if verification is not None and not verification.passed:
        for finding in verification.findings:
            note = f"Structural check flagged: {finding}"
            if note not in struggled:
                struggled.append(note)

    if artifact.format == CreativeFormat.REEL:
        struggled.append(
            "I reviewed this reel from its edit plan and file checks only -- I did not "
            "watch the rendered frames, so visual problems inside the video could be missed."
        )

    summary = (vision.summary.strip() if vision and vision.summary.strip() else "") or (
        "Reviewed against automated measurements only."
        if artifact.format == CreativeFormat.POSTER
        else "Reviewed against the edit plan and file checks."
    )

    return CreativeCritique(
        summary=summary,
        did=did,
        why=why,
        information=information,
        struggled=struggled,
        model_reviewed=vision is not None,
    )
