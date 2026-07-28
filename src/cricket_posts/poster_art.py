"""Structured art direction for Ideogram poster generation.

The existing ``ideogram.full_poster_json_prompt`` asks for "cinematic full-frame
sports photography". That is the wrong brief for the design language academies
actually publish, which is a *collage*: cut-out subjects with white keylines,
paint-stroke shapes, flat icon badges, halftone bursts and hand-drawn doodles.
A photograph prompt cannot produce that no matter how it is tuned.

Two modes are supported:

``PosterMode.FULL``
    Ideogram renders artwork *and* typography. Fast, and the only way to get
    integrated hand-lettered treatments, but text is not deterministic and every
    factual value needs proofreading.

``PosterMode.PLATE``
    Ideogram renders a designed background plate with explicitly reserved empty
    zones and no text at all. The deterministic renderer then composites exact
    copy and the real logo on top. This is how you get the collage look without
    surrendering the copy guarantee.

Bounding boxes use Ideogram's 0-1000 coordinate space on both axes.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import BrandProfile, PosterContent
from .layout import poster_copy_lines


class PosterMode(str, Enum):
    FULL = "full"
    PLATE = "plate"


class Zone(BaseModel):
    """A named rectangle in Ideogram's 0-1000 space."""

    model_config = ConfigDict(extra="forbid")

    name: str
    box: tuple[int, int, int, int]
    purpose: str = ""

    def as_list(self) -> list[int]:
        return list(self.box)


class SubjectBrief(BaseModel):
    """Who appears in the artwork.

    Kept explicit rather than buried in prose so it can be varied, stored and
    replayed with a fixed seed.
    """

    model_config = ConfigDict(extra="forbid")

    count: int = Field(default=3, ge=1, le=6)
    age_range: str = "between 5 and 10 years old"
    appearance: str = "South Asian (Indian) children"
    kit: str = "bright yellow and royal blue cricket jerseys"
    equipment: str = "cricket helmets, batting gloves and leg pads"
    action: str = "one child front and centre mid batting stroke, the others celebrating around them"
    expression: str = "genuinely joyful, laughing, full of energy"
    cutout: bool = True

    def describe(self) -> str:
        parts = [
            f"{self.count} {self.appearance} {self.age_range}",
            f"wearing {self.kit}",
            f"with {self.equipment}",
            self.action,
            f"expressions {self.expression}",
        ]
        body = ", ".join(part for part in parts if part)
        if self.cutout:
            body += (
                ". Rendered as crisp photographic cut-outs with a clean white keyline "
                "stroke around each figure, lifted off the background like sticker art"
            )
        return body


# The visual vocabulary of the reference design, stated once.
COLLAGE_STYLE = {
    "aesthetics": (
        "high-energy youth sports marketing collage, modern Indian cricket academy "
        "advertising, bold and celebratory, premium but playful"
    ),
    "medium": (
        "graphic design collage combining photographic cut-outs with vector shapes, "
        "dry-brush paint strokes, torn-paper edges, halftone dot bursts and "
        "hand-drawn marker doodles"
    ),
    "lighting": (
        "bright even daylight on the subjects with soft natural shadows, no moody "
        "cinematic darkness"
    ),
    "composition": (
        "layered poster composition on a clean near-white background, with sweeping "
        "diagonal paint strokes in the brand colours behind the subjects, small "
        "doodle accents such as stars, crowns, dotted motion arcs and a bouncing "
        "cricket ball trail"
    ),
}

NO_TEXT_RULE = (
    "Include absolutely no text, letters, numbers, words, signage, jersey lettering, "
    "sponsor marks, watermarks, captions or interface elements anywhere in the image."
)

NO_LOGO_RULE = (
    "Do not invent, draw or imitate any logo, badge, crest, emblem or brand wordmark. "
    "The real logo is composited afterwards."
)


def reference_zones() -> list[Zone]:
    """Layout skeleton matching the academy poster convention."""
    return [
        Zone(name="logo", box=(40, 30, 250, 230), purpose="brand logo lockup"),
        Zone(name="headline", box=(230, 45, 700, 330), purpose="main headline stack"),
        Zone(name="badge", box=(620, 40, 985, 210), purpose="highlighted sub-headline"),
        Zone(name="intro", box=(45, 350, 505, 570), purpose="introductory paragraph"),
        Zone(name="subject", box=(500, 200, 1000, 830), purpose="photographic subjects"),
        Zone(name="benefits", box=(40, 585, 510, 715), purpose="icon badge row"),
        Zone(name="ribbon", box=(35, 725, 520, 830), purpose="slogan ribbon"),
        Zone(name="footer", box=(40, 850, 960, 940), purpose="contact bar"),
        Zone(name="banner", box=(0, 950, 1000, 1000), purpose="closing slogan banner"),
    ]


def _palette_sentence(brand: BrandProfile) -> str:
    palette = brand.palette
    return (
        f"Strictly use this palette: deep navy {palette.ink}, off-white "
        f"{palette.surface}, golden yellow {palette.accent}, bright blue "
        f"{palette.highlight}, plus a single warm red accent. Keep the background "
        "predominantly light and clean so the colour blocks read strongly."
    )


def _text_role(line: str, content: PosterContent, brand: BrandProfile) -> str:
    organization = content.organization or brand.name
    footer_values = {
        *content.location_lines,
        *(contact.display() for contact in content.contacts),
        *brand.contact_lines,
    }
    if line == content.title:
        return (
            "The dominant headline, huge bold condensed sports lettering stacked on "
            "two or three lines, with the strongest colour contrast on the poster"
        )
    if line == content.subtitle:
        return (
            "A hand-lettered sub-headline sitting inside a golden brush-stroke shape "
            "in the upper right"
        )
    if line == content.tagline:
        return (
            "A closing slogan across the bottom banner in bold condensed caps, split "
            "across two colours"
        )
    if line == organization:
        return "The academy name set as a compact bold sports wordmark"
    if line in footer_values:
        return "Small but perfectly legible contact information inside the white footer bar"
    if line in content.cta_lines:
        return "A small bold label above its matching contact detail in the footer bar"
    return "Clear supporting copy with comfortable line spacing"


def build_art_prompt(
    content: PosterContent,
    brand: BrandProfile,
    *,
    mode: PosterMode = PosterMode.FULL,
    subject: SubjectBrief | None = None,
    zones: list[Zone] | None = None,
) -> dict[str, Any]:
    subject = subject or SubjectBrief()
    zones = zones or reference_zones()
    by_name = {zone.name: zone for zone in zones}

    subject_box = (
        by_name["subject"].as_list()
        if mode is PosterMode.FULL
        # In plate mode the subjects sit lower and further right so the copy
        # quadrants stay genuinely empty.
        else [420, 330, 1000, 880]
    )
    elements: list[dict[str, Any]] = [
        {
            "type": "obj",
            "bbox": subject_box,
            "desc": (
                f"{subject.describe()}. Fill this region with the subjects so they are "
                "the visual anchor of the poster. Include a cricket bat, stumps and a "
                f"red leather cricket ball. {NO_LOGO_RULE}"
            ),
        },
        {
            "type": "obj",
            "bbox": by_name["benefits"].as_list(),
            "desc": (
                "A horizontal row of four flat circular icon badges in green, orange, "
                "blue and purple, each containing a simple white pictogram: a batting "
                "figure, a running figure, a cricket ball and a smiling face. Clean "
                "vector style, evenly spaced, equal size."
            ),
        },
    ]

    if mode is PosterMode.FULL:
        lines = poster_copy_lines(content, brand)
        for line in lines:
            elements.append(
                {
                    "type": "text",
                    "text": line,
                    "desc": (
                        f"{_text_role(line, content, brand)}. Render this string exactly "
                        "as supplied, with no correction, translation, added or removed "
                        "punctuation, and no extra words."
                    ),
                }
            )
        text_rule = (
            "Typography is integrated into the design with a clear hierarchy. Every "
            "supplied string must appear exactly once and be fully legible."
        )
    else:
        # Reserved space is expressed as composition, never as elements with
        # boxes. Describing a zone as an object makes the model *draw* it: an
        # earlier attempt produced literal cream cards in arbitrary positions.
        text_rule = (
            f"{NO_TEXT_RULE} "
            "Compose deliberate negative space for copy that is added later: keep "
            "the upper-left quadrant and the entire lower sixth of the canvas as "
            "calm, near-flat background with no subjects, no brush strokes and no "
            "small decorative marks. Concentrate the subjects and decoration in the "
            "right half and lower-middle. Do not draw panels, cards, rounded "
            "rectangles, boxes or placeholder shapes anywhere."
        )

    return {
        "high_level_description": (
            "A premium 4:5 vertical promotional poster for a children's cricket academy "
            "in the style of modern Indian sports advertising: a layered collage of "
            "photographic cut-outs, dry-brush paint strokes and playful hand-drawn "
            f"accents on a clean light background. {_palette_sentence(brand)} {text_rule}"
        ),
        "compositional_deconstruction": {
            "background": (
                "A clean near-white background carrying broad diagonal dry-brush paint "
                "strokes in navy, golden yellow and bright blue, with subtle halftone "
                "dot bursts, small hand-drawn stars and a dotted arc tracing a cricket "
                "ball through the air. Bright, airy and uncluttered, never dark or "
                f"cinematic. {NO_LOGO_RULE}"
            ),
            "elements": elements,
        },
        "style_description": COLLAGE_STYLE,
    }
