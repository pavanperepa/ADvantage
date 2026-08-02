"""The plate bank: background art indexed by archetype and intent.

Plates carry no text and no people. Keeping them background-only is what lets a
real photograph of a real student be dropped in as the subject layer, and it is
also what makes free-space discovery reliable — backgrounds are calm.

Generation is an occasional restocking job, never a per-poster call. Composing a
poster reads from this bank and touches no API.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .archetypes import ArchetypeId
from .freespace import FreeSpaceMap, load_or_analyze
from .models import ContentType, Rect, StyleIntent
from .renderer import ASSET_DIR

PLATE_DIR = ASSET_DIR / "plates"
MANIFEST = PLATE_DIR / "manifest.json"


class PlateEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str
    archetype: ArchetypeId
    intents: list[StyleIntent] = Field(default_factory=list)
    seed: int | None = None
    note: str = ""
    #: Which kinds of post this artwork suits. Empty means it suits any.
    #: Intent tags describe a *mood* and are not enough on their own: a
    #: confetti-and-balloons plate is legitimately "bright_vibrant", and
    #: matching on that alone puts an adult lane-rental offer on a children's
    #: party. Wrong artwork is a worse failure than repetitive artwork.
    content_types: list[ContentType] = Field(default_factory=list)
    #: True when the artwork already contains its own figures. Such a plate is
    #: a whole scene rather than a background: one generation settles the
    #: perspective, scale and lighting between the people and the room, which
    #: compositing cut-outs has to reconstruct by hand. The cost is that it is
    #: no longer reusable — the cast is baked in — so the pipeline must not add
    #: a subject layer on top and end up with two batters in one lane.
    has_subjects: bool = False

    def path(self, root: Path = PLATE_DIR) -> Path:
        return root / self.file


class PlateBank(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[PlateEntry] = Field(default_factory=list)

    @classmethod
    def load(cls, manifest: Path = MANIFEST) -> "PlateBank":
        if not manifest.exists():
            return cls()
        return cls.model_validate_json(manifest.read_text(encoding="utf-8"))

    def save(self, manifest: Path = MANIFEST) -> Path:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return manifest

    def candidates(
        self,
        archetype: ArchetypeId | None = None,
        intent: StyleIntent | None = None,
        content_type: ContentType | None = None,
    ) -> list[PlateEntry]:
        # Content type is applied first and separately, because it is the only
        # one of the three where a mismatch is *wrong* rather than merely
        # suboptimal. Relaxing archetype or mood gives an awkward poster;
        # relaxing this gives a lane-rental offer on a children's party plate.
        suitable = [
            entry
            for entry in self.entries
            if content_type is None
            or not entry.content_types
            or content_type in entry.content_types
        ]
        found = [
            entry
            for entry in suitable
            if (archetype is None or entry.archetype == archetype)
            and (intent is None or not entry.intents or intent in entry.intents)
        ]
        # Never leave the caller with nothing: any plate beats no poster, and the
        # free-space check downstream still gates whether it is usable. Falling
        # back within `suitable` first keeps the content-type promise intact.
        return found or suitable or list(self.entries)


class PlateChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry: PlateEntry
    path: Path
    zone: Rect
    freespace: FreeSpaceMap

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)


def select_plate(
    bank: PlateBank,
    archetype: ArchetypeId,
    intent: StyleIntent,
    *,
    root: Path = PLATE_DIR,
    min_zone_area: float = 260_000.0,
    only_file: str | None = None,
    content_type: ContentType | None = None,
) -> PlateChoice | None:
    """Pick the plate whose measured calm rectangle best suits the archetype."""
    from .archetypes import ARCHETYPES

    expectation = ARCHETYPES[archetype]
    best: tuple[float, PlateChoice] | None = None
    entries = bank.candidates(archetype, intent, content_type)
    if only_file:
        entries = [entry for entry in bank.entries if entry.file == only_file]
        if not entries:
            raise ValueError(f"No plate named {only_file!r} in the bank.")
    for entry in entries:
        plate = entry.path(root)
        if not plate.exists():
            continue
        measured = load_or_analyze(plate)
        for zone in measured.zones:
            if zone.area < min_zone_area:
                continue
            score = expectation.match_score(zone.box, measured.width, measured.height)
            choice = PlateChoice(
                entry=entry, path=plate, zone=zone.box, freespace=measured
            )
            if best is None or score > best[0]:
                best = (score, choice)
    return best[1] if best else None


def index_plates(root: Path = PLATE_DIR) -> PlateBank:
    """Rebuild the manifest from whatever PNGs are present, preserving tags."""
    existing = {entry.file: entry for entry in PlateBank.load(root / "manifest.json").entries}
    entries: list[PlateEntry] = []
    for plate in sorted(root.glob("*.png")):
        entries.append(
            existing.get(
                plate.name,
                PlateEntry(file=plate.name, archetype=ArchetypeId.LEFT_COLUMN),
            )
        )
        load_or_analyze(plate)
    bank = PlateBank(entries=entries)
    bank.save(root / "manifest.json")
    return bank
