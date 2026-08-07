"""Restocking the plate bank: generate, measure, then decide.

Composing a poster reads from the bank and touches no API. This is the other
half — the occasional job that puts artwork *into* the bank, and the only place
in the compose pipeline's world that spends money.

The discipline here is that the machine gate runs before a human looks. A
negative-space brief is a request, not a contract (`freespace` exists because of
that), so the question "did this plate honour the brief it was generated from"
is answered by measuring the pixels and scoring the calm rectangle against the
archetype's own expectation. A plate that measures wrong is a reject however
good it looks, because the copy has nowhere to go; a plate that measures right
still has to pass a human, because measurement cannot see stray lettering, an
invented crest, or artwork that is simply dull.

So: generate into staging, measure, print the verdict, stop early on a pass —
and accept into the bank as a separate deliberate step.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .archetypes import ARCHETYPES, Archetype, ArchetypeId
from .freespace import analyze
from .models import Palette
from .plates import PLATE_DIR, PlateBank, PlateEntry
from .poster_art import NO_LOGO_RULE, NO_TEXT_RULE

#: Candidates land here, not in the bank. `select_plate` globs the bank
#: directory, so an unreviewed plate sitting beside the accepted ones would be
#: composited onto a real poster before anyone had looked at it.
STAGING_DIR = PLATE_DIR / "_incoming"

#: 4:5, and exactly the size `dusk-floodlit-bottom-01` was generated at. It also
#: lands closest to the scale the stylesheet was tuned against: every size in
#: canvas.css is `calc(Npx * var(--s))` where `--s = width / 1728`, so a plate
#: at 1792 renders furniture at 1.04x design size where a 1080 plate renders it
#: at 0.63x.
PLATE_RESOLUTION = "1792x2240"

#: Calibrated against the plates already banked, whose best-zone IoU against
#: their own archetype runs from about 0.51 to 0.78. Below this a plate is not a
#: near miss — it is a different layout wearing the right filename.
MIN_IOU = 0.45

#: As a fraction of the canvas, not the absolute pixel count `select_plate`
#: uses. That number means 17.8% of a 1080x1350 canvas and 6.5% of a 1792x2240
#: one, which is not one threshold but two.
MIN_ZONE_FRACTION = 0.14


@dataclass
class PlateVerdict:
    """What the measurement says about one candidate."""

    accepted: bool
    iou: float
    zone_fraction: float
    reason: str

    def line(self) -> str:
        mark = "PASS" if self.accepted else "REJECT"
        return (
            f"{mark}  iou {self.iou:.2f}  zone {self.zone_fraction:.0%}"
            f"  {self.reason}"
        )


def verify(plate: Path, archetype: Archetype) -> PlateVerdict:
    """Score a candidate's measured calm rectangle against its brief.

    This answers one question only: is the calm space where this archetype
    needs it, and is there enough of it. That is the failure no amount of CSS
    recovers from, and it is the one a person is bad at eyeballing.

    It deliberately does *not* try to answer "does the artwork fill the frame".
    Ideogram will sometimes inset the picture as a rectangle and leave the rest
    flat, which is unusable — but two attempts at detecting it failed against
    the banked plates. Counting non-calm cells outside the copy region put every
    good plate at 6-36% and the inset reject at 24%, because a photograph of
    turf or sky is smooth and therefore reads as calm. Matching cells against
    the plate's modal colour put the good plates at up to 37% and the reject at
    38% — a one-point margin, which is no margin. Whether artwork bleeds off the
    frame is a judgement, and the review step below is where it belongs.
    """
    measured = analyze(plate)
    if not measured.zones:
        return PlateVerdict(False, 0.0, 0.0, "no calm rectangle anywhere")

    canvas = float(measured.width * measured.height)
    iou, zone = max(
        (
            (archetype.match_score(zone.box, measured.width, measured.height), zone)
            for zone in measured.zones
        ),
        key=lambda pair: pair[0],
    )
    fraction = zone.box.area / canvas if canvas else 0.0

    if iou < MIN_IOU:
        return PlateVerdict(
            False, iou, fraction, f"calm space is not where {archetype.id.value} needs it"
        )
    if fraction < MIN_ZONE_FRACTION:
        return PlateVerdict(False, iou, fraction, "the calm rectangle is too small for copy")
    return PlateVerdict(True, iou, fraction, "measures right — now look at it")


def _palette_sentence(palette: Palette) -> str:
    return (
        f"Strictly use this palette: deep navy {palette.ink}, off-white "
        f"{palette.surface}, golden yellow {palette.accent} and bright blue "
        f"{palette.highlight}."
    )


def build_plate_prompt(
    archetype: Archetype,
    palette: Palette,
    *,
    scene: str,
    mood: str,
) -> dict:
    """A structured prompt for one background plate.

    Reserved space is stated as composition and never as an element with a box.
    Describing a zone as an object makes the model *draw* it — an earlier
    attempt at this produced literal cream cards in arbitrary positions — so the
    elements list is deliberately empty and the brief lives in the prose.
    """
    reserved = (
        f"{archetype.negative_space_brief} Do not draw panels, cards, rounded "
        "rectangles, boxes or placeholder shapes anywhere."
    )
    return {
        "high_level_description": (
            "A 4:5 vertical background plate for a children's cricket academy "
            f"poster. {scene} {_palette_sentence(palette)} {NO_TEXT_RULE} "
            f"{NO_LOGO_RULE} {reserved}"
        ),
        "compositional_deconstruction": {
            "background": f"{scene} {reserved}",
            # Empty on purpose. Every element carries a bounding box, and a box
            # is an instruction to put something there — which is the opposite
            # of what a plate is for.
            "elements": [],
        },
        "style_description": {
            "aesthetics": mood,
            "medium": (
                "graphic design background plate combining photographic texture "
                "with flat vector colour blocks and dry-brush paint strokes"
            ),
            "composition": (
                "large simple shapes, generous uninterrupted areas of flat "
                "colour, nothing small or fiddly"
            ),
        },
    }


def sidecar(plate: Path) -> Path:
    return plate.with_suffix(".plate.json")


def generate(
    archetype_id: ArchetypeId,
    palette: Palette,
    *,
    scene: str,
    mood: str,
    intents: list[str],
    content_types: list[str],
    name: str,
    attempts: int = 3,
    rendering_speed: str = "TURBO",
    staging: Path = STAGING_DIR,
) -> tuple[Path, PlateVerdict] | None:
    """Generate until one candidate measures right, or the attempts run out.

    Stops on the first pass rather than generating the full count and choosing.
    Rejects are cheap to spot and expensive to make, so the loop is built to
    stop paying as soon as it has what it asked for.
    """
    from .ideogram import generate_json_prompt

    archetype = ARCHETYPES[archetype_id]
    prompt = build_plate_prompt(archetype, palette, scene=scene, mood=mood)
    staging.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, attempts + 1):
        candidate = staging / f"{name}-{attempt:02d}.png"
        result = generate_json_prompt(
            prompt,
            candidate,
            resolution=PLATE_RESOLUTION,
            rendering_speed=rendering_speed,
        )
        verdict = verify(candidate, archetype)
        print(f"  {candidate.name}  {verdict.line()}")
        sidecar(candidate).write_text(
            json.dumps(
                {
                    "archetype": archetype_id.value,
                    "intents": intents,
                    "content_types": content_types,
                    "seed": result.seed,
                    "resolution": result.resolution or PLATE_RESOLUTION,
                    "rendering_speed": rendering_speed,
                    "scene": scene,
                    "mood": mood,
                    "iou": round(verdict.iou, 3),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        if verdict.accepted:
            return candidate, verdict
    return None


def accept(candidate: Path, *, note: str = "", root: Path = PLATE_DIR) -> PlateEntry:
    """Move a verified candidate into the bank, carrying its provenance.

    The sidecar is what makes a plate reproducible: without the seed, a plate
    that turns out to be the good one can only be re-rolled, not re-rendered at
    a higher quality setting. `index_plates` defaults an untagged PNG to
    `left_column`, so tagging here rather than there is what stops a top-band
    plate being silently filed as a left-column one.
    """
    meta = json.loads(sidecar(candidate).read_text(encoding="utf-8"))
    destination = root / candidate.name
    destination.write_bytes(candidate.read_bytes())

    bank = PlateBank.load(root / "manifest.json")
    entries = {entry.file: entry for entry in bank.entries}
    entries[destination.name] = PlateEntry(
        file=destination.name,
        archetype=ArchetypeId(meta["archetype"]),
        intents=meta.get("intents", []),
        seed=meta.get("seed"),
        note=note or f"{meta.get('scene', '')[:150]} (iou {meta.get('iou')})",
        content_types=meta.get("content_types", []),
        has_subjects=False,
    )
    PlateBank(entries=list(entries.values())).save(root / "manifest.json")
    return entries[destination.name]
