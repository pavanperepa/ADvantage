"""Layout templates harvested from generated posters.

A harvested template is the model's *arrangement*, kept and reused: an ordered
set of slots, each with a rectangle, a role, a size, a colour and an alignment,
paired with the plate its text was lifted off.

This is a strictly richer starting point than the free-space route. `freespace`
answers "where is there room at all" and returns a bare rectangle; a template
arrives already knowing there is a heading here, a badge there, and a row of
captions along the foot.

It stays a **proposal**. Our copy is fixed and must render verbatim, so when a
harvested heading slot is too small for the real headline the fit engine grows
the type or the slot — it never trims the words. Nothing here relaxes that.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .blocks import BlockRole
from .layerize import TextBlock
from .models import Rect
from .renderer import ASSET_DIR

LAYOUT_DIR = ASSET_DIR / "layouts"
MANIFEST = LAYOUT_DIR / "manifest.json"

#: Vendor role -> our block role. The vendor vocabulary is small and generic,
#: so this is a deliberate, testable table rather than inference from position.
ROLE_MAP: dict[str, BlockRole] = {
    "heading": BlockRole.HEADLINE,
    "title": BlockRole.HEADLINE,
    "subheading": BlockRole.BADGE,
    "subtitle": BlockRole.BADGE,
    "body": BlockRole.PARAGRAPH,
    "paragraph": BlockRole.PARAGRAPH,
    "list": BlockRole.BULLETS,
    "caption": BlockRole.INFO_BAR,
    "footer": BlockRole.INFO_BAR,
    "label": BlockRole.STAT_CHIPS,
}

#: Families we actually ship as woff2 in assets/fonts. A harvested font name is
#: whatever the model felt like; substituting the nearest thing we can embed
#: keeps the render self-contained and avoids a silent fallback to a system
#: face that is not on the machine.
SHIPPED_FONTS = (
    "Anton",
    "Archivo",
    "Archivo Black",
    "Archivo Narrow",
    "Bebas Neue",
    "Fraunces",
    "Inter",
    "Outfit",
    "Playfair Display",
    "Poppins",
    "Space Grotesk",
)

#: Matched on the family stem of the reported font, by character rather than by
#: name: condensed grotesques to our condensed, geometric to geometric, and so on.
FONT_MAP: dict[str, str] = {
    "oswald": "Archivo Narrow",
    "bebasneue": "Bebas Neue",
    "anton": "Anton",
    "impact": "Anton",
    "montserrat": "Outfit",
    "raleway": "Outfit",
    "futura": "Outfit",
    "poppins": "Poppins",
    "nunito": "Poppins",
    "quicksand": "Poppins",
    "opensans": "Inter",
    "roboto": "Inter",
    "lato": "Inter",
    "sourcesanspro": "Inter",
    "helvetica": "Inter",
    "arial": "Inter",
    "inter": "Inter",
    "spacegrotesk": "Space Grotesk",
    "archivo": "Archivo",
    "archivoblack": "Archivo Black",
    "archivonarrow": "Archivo Narrow",
    "playfairdisplay": "Playfair Display",
    "merriweather": "Playfair Display",
    "georgia": "Playfair Display",
    "times": "Playfair Display",
    "fraunces": "Fraunces",
}

DEFAULT_FONT = "Inter"


def map_font(font_name: str) -> str:
    """Nearest family we can actually embed, for a font name we were handed."""
    stem = Path(font_name).stem.lower()
    # "Montserrat-Bold" -> "montserrat"; weights and styles are theming, not identity.
    family = "".join(ch for ch in stem.split("-")[0] if ch.isalnum())
    if family in FONT_MAP:
        return FONT_MAP[family]
    for known, shipped in FONT_MAP.items():
        if family.startswith(known) or known.startswith(family):
            return shipped
    return DEFAULT_FONT


class LayoutSlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: BlockRole
    #: What the model called it, kept so a mapping change stays reviewable.
    source_role: str = ""
    box: Rect
    font_family: str = DEFAULT_FONT
    font_size: float = 0.0
    line_height: float = 0.0
    color: str = ""
    alignment: str = "left"
    order: int = 0
    #: Erase pass that found this slot. Above 1 flags a likely fragment.
    found_on_pass: int = 1

    @property
    def area(self) -> float:
        return self.box.area


class LayoutTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    plate_file: str
    width: int
    height: int
    slots: list[LayoutSlot] = Field(default_factory=list)
    note: str = ""

    def by_role(self, role: BlockRole) -> list[LayoutSlot]:
        return [slot for slot in self.slots if slot.role is role]

    def suspect_slots(self) -> list[LayoutSlot]:
        """Slots the detector missed on its first look.

        These are usually fragments of garbled type rather than components the
        designer intended, so they want a human eye before the template is used.
        """
        return [slot for slot in self.slots if slot.found_on_pass > 1]

    def bands(self) -> list[tuple[BlockRole, Rect]]:
        """Consecutive slots of one role merged into the region they span.

        A row of captions along the foot is one contact bar, and four one-line
        body slots are one bullet list. Grouping them keeps the arrangement
        without pretending each line is its own component.
        """
        bands: list[tuple[BlockRole, Rect]] = []
        for slot in sorted(self.slots, key=lambda item: item.order):
            if bands and bands[-1][0] is slot.role:
                role, box = bands[-1]
                bands[-1] = (
                    role,
                    Rect(
                        left=min(box.left, slot.box.left),
                        top=min(box.top, slot.box.top),
                        right=max(box.right, slot.box.right),
                        bottom=max(box.bottom, slot.box.bottom),
                    ),
                )
            else:
                bands.append((slot.role, slot.box))
        return bands


def template_from_blocks(
    blocks: list[TextBlock],
    *,
    name: str,
    plate_file: str,
    width: int,
    height: int,
    note: str = "",
) -> LayoutTemplate:
    """Turn harvested text blocks into a reusable template.

    Reading order, not detection order: the blocks come back in whatever order
    they were found, and a template whose slots are out of sequence would map
    our content onto the page scrambled.
    """
    ordered = sorted(blocks, key=lambda block: (round(block.y), round(block.x)))
    slots = [
        LayoutSlot(
            role=ROLE_MAP.get(block.role.lower().strip(), BlockRole.PARAGRAPH),
            source_role=block.role,
            box=block.box(),
            font_family=map_font(block.font_name),
            font_size=block.font_size,
            line_height=block.line_height,
            color=block.color,
            alignment=block.alignment or "left",
            order=index,
            found_on_pass=block.found_on_pass,
        )
        for index, block in enumerate(ordered)
    ]
    return LayoutTemplate(
        name=name,
        plate_file=plate_file,
        width=width,
        height=height,
        slots=slots,
        note=note,
    )


class LayoutBank(BaseModel):
    model_config = ConfigDict(extra="forbid")

    templates: list[LayoutTemplate] = Field(default_factory=list)

    @classmethod
    def load(cls, manifest: Path = MANIFEST) -> "LayoutBank":
        if not manifest.exists():
            return cls()
        return cls.model_validate_json(manifest.read_text(encoding="utf-8"))

    def save(self, manifest: Path = MANIFEST) -> Path:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return manifest

    def add(self, template: LayoutTemplate) -> "LayoutBank":
        kept = [item for item in self.templates if item.name != template.name]
        return LayoutBank(templates=[*kept, template])

    def get(self, name: str) -> LayoutTemplate | None:
        return next((item for item in self.templates if item.name == name), None)
