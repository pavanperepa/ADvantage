"""Layout archetypes: how blocks are arranged, and what the plate must leave empty.

An archetype deliberately does *not* hardcode where the copy goes. That comes
from `freespace.analyze`, because the brief is a request and the model does not
honour it reliably. The archetype supplies two things:

* the **negative-space brief** handed to the plate generator, and
* the **arrangement** used inside whatever calm rectangle actually turns up.

Keeping the set small is intentional; each archetype needs a matching plate
brief, so this is the part of the system that should grow slowly.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from .freespace import MIN_ZONE_H, MIN_ZONE_W
from .models import Rect


class ArchetypeId(str, Enum):
    LEFT_COLUMN = "left_column"
    BOTTOM_THIRD = "bottom_third"
    CENTER_STAGE = "center_stage"


class BarPosition(str, Enum):
    BOTTOM = "bottom"
    NONE = "none"


class Archetype(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: ArchetypeId
    label: str
    negative_space_brief: str
    #: Where the calm rectangle is expected, as canvas fractions. Used to score
    #: how well a discovered zone matches, never to place copy outright.
    expected_region: tuple[float, float, float, float]
    columns: int = 1
    bar: BarPosition = BarPosition.BOTTOM
    banner: bool = True
    #: Centre the copy horizontally and set it ragged-centre. Suits announcement
    #: posters that carry no photography, where a left column looks lopsided.
    centered: bool = False
    #: Where cut-outs may stand, as canvas fractions. `None` means the archetype
    #: carries no photography — the copy owns the middle and a figure would
    #: either cover it or crowd the frame.
    subject_region: tuple[float, float, float, float] | None = None

    def region_rect(self, width: int, height: int) -> Rect:
        return self._rect(self.expected_region, width, height)

    @staticmethod
    def _rect(
        fractions: tuple[float, float, float, float],
        width: int,
        height: int,
    ) -> Rect:
        left, top, right, bottom = fractions
        return Rect(
            left=left * width,
            top=top * height,
            right=right * width,
            bottom=bottom * height,
        )

    def shape_zone(self, measured: Rect, width: int, height: int) -> Rect:
        """Trim a measured calm rectangle to the proportions this layout wants.

        Measurement answers "where may copy go", which is a safety question, and
        it answers it generously — the largest calm rectangle on the plate. That
        is not the same as "where should copy go". Handing the copy every
        available pixel makes a column wide enough to leave a hole under it and
        squeezes whatever shares the canvas, so the archetype narrows the zone
        to its own proportions and the measurement stays a hard outer bound.

        Falls back to the measured rectangle when trimming would leave too
        little to work with: a poster laid out in the wrong proportions beats a
        poster with nowhere to put the copy.
        """
        wanted = self.region_rect(width, height)
        shaped = Rect(
            left=max(measured.left, wanted.left),
            top=max(measured.top, wanted.top),
            right=min(measured.right, wanted.right),
            bottom=min(measured.bottom, wanted.bottom),
        )
        if shaped.width < MIN_ZONE_W or shaped.height < MIN_ZONE_H:
            return measured
        return shaped

    def subject_slot(self, zone: Rect, width: int, height: int) -> Rect | None:
        """Where a cut-out can stand without covering the copy.

        Clamped against the *measured* copy zone rather than the brief. The
        plate decides where the calm rectangle actually landed, so the subject
        has to take whatever is left over — pushing it clear along whichever
        axis has more room keeps a figure off the type even when the zone
        turns up somewhere the brief did not ask for.
        """
        if self.subject_region is None:
            return None
        slot = self._rect(self.subject_region, width, height)
        if (width - zone.right) >= zone.top:
            slot.left = max(slot.left, zone.right)
        else:
            slot.bottom = min(slot.bottom, zone.top)
        return slot if slot.width > 0 and slot.height > 0 else None

    def match_score(self, zone: Rect, width: int, height: int) -> float:
        """Intersection over union of a discovered zone with the expectation."""
        expected = self.region_rect(width, height)
        overlap_w = max(0.0, min(zone.right, expected.right) - max(zone.left, expected.left))
        overlap_h = max(0.0, min(zone.bottom, expected.bottom) - max(zone.top, expected.top))
        intersection = overlap_w * overlap_h
        union = zone.area + expected.area - intersection
        return intersection / union if union > 0 else 0.0


ARCHETYPES: dict[ArchetypeId, Archetype] = {
    ArchetypeId.LEFT_COLUMN: Archetype(
        id=ArchetypeId.LEFT_COLUMN,
        label="Copy left, subjects right",
        negative_space_brief=(
            "Keep the entire left third of the canvas and the lower sixth as calm, "
            "near-flat background with no subjects, no brush strokes and no small "
            "decorative marks. Concentrate all artwork and decoration in the right "
            "half."
        ),
        expected_region=(0.03, 0.03, 0.42, 0.88),
        columns=1,
        # Runs to the right edge on purpose: a figure cropped by the frame reads
        # as deliberate, whereas one floating short of it reads as a mistake.
        subject_region=(0.38, 0.06, 1.0, 0.97),
    ),
    ArchetypeId.CENTER_STAGE: Archetype(
        id=ArchetypeId.CENTER_STAGE,
        label="Centred announcement, artwork framing the edges",
        negative_space_brief=(
            "Keep a large calm rectangle through the middle of the canvas — the "
            "central two thirds horizontally and from just below the top edge to the "
            "lower fifth — as near-flat, light background with no detail, no strokes "
            "and no small marks. Concentrate every colour block, diagonal plane and "
            "decorative mark into the outer margins: the top-left and top-right "
            "corners, the left and right edges, and the bottom corners, framing the "
            "empty centre without intruding on it."
        ),
        expected_region=(0.08, 0.09, 0.92, 0.80),
        columns=1,
        centered=True,
    ),
    ArchetypeId.BOTTOM_THIRD: Archetype(
        id=ArchetypeId.BOTTOM_THIRD,
        label="Artwork above, copy below",
        negative_space_brief=(
            "Keep the entire lower two fifths of the canvas as calm, near-flat "
            "background with no subjects, no brush strokes and no small decorative "
            "marks. Concentrate all artwork and decoration in the upper half."
        ),
        expected_region=(0.04, 0.52, 0.96, 0.88),
        columns=2,
        subject_region=(0.06, 0.02, 0.94, 0.56),
    ),
}


def select_archetype(
    zones: list[Rect],
    width: int,
    height: int,
    *,
    preferred: ArchetypeId | None = None,
) -> tuple[Archetype, Rect] | None:
    """Pick the archetype whose expectation best matches an available zone.

    Returns the archetype together with the zone the copy will actually occupy,
    so callers never have to re-derive it.
    """
    if not zones:
        return None
    candidates = (
        [ARCHETYPES[preferred]] if preferred else list(ARCHETYPES.values())
    )
    best: tuple[float, Archetype, Rect] | None = None
    for archetype in candidates:
        for zone in zones:
            score = archetype.match_score(zone, width, height)
            if best is None or score > best[0]:
                best = (score, archetype, zone)
    if best is None or best[0] <= 0.0:
        # No overlap with any expectation: fall back to the biggest zone so a
        # poster is still produced rather than failing outright.
        largest = max(zones, key=lambda zone: zone.area)
        return candidates[0], largest
    return best[1], best[2]
