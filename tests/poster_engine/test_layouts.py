"""Harvesting a layout template, and the gate that keeps stray text out.

The API is never called here: `harvest` takes its layerizer as an argument
precisely so the loop and the gate can be tested without spending a request.
"""

from __future__ import annotations

import pytest

from cricket_posts.blocks import BlockRole
from cricket_posts.layerize import HarvestResult, LayerizePass, TextBlock, harvest
from cricket_posts.layouts import (
    DEFAULT_FONT,
    FONT_MAP,
    ROLE_MAP,
    SHIPPED_FONTS,
    LayoutBank,
    map_font,
    template_from_blocks,
)


def block(text: str, *, role: str = "body", x: float = 0, y: float = 0, **kwargs) -> TextBlock:
    return TextBlock(text=text, role=role, x=x, y=y, width=100, height=20, **kwargs)


class FakeLayerizer:
    """Returns one batch of blocks per call, then nothing."""

    def __init__(self, batches: list[list[TextBlock]]):
        self.batches = batches
        self.calls = 0

    def __call__(self, image: bytes, **kwargs) -> LayerizePass:
        found = self.batches[self.calls] if self.calls < len(self.batches) else []
        self.calls += 1
        return LayerizePass(blocks=found, base_image=f"erased-{self.calls}".encode())


def test_harvest_keeps_erasing_until_a_pass_finds_nothing():
    """One pass missed the word BRIGHT on a real poster; a second caught it."""
    layerizer = FakeLayerizer([[block("HEADLINE")], [block("BRIGHT")], []])

    result = harvest(b"poster", layerizer=layerizer)

    assert result.clean
    assert [b.text for b in result.blocks] == ["HEADLINE", "BRIGHT"]
    # The third pass found nothing, so the plate from the second is the result:
    # a pass that erased nothing has nothing to contribute.
    assert result.base_image == b"erased-2"
    assert layerizer.calls == 3


def test_a_single_clean_pass_returns_the_source_untouched():
    layerizer = FakeLayerizer([[]])

    result = harvest(b"poster", layerizer=layerizer)

    assert result.clean and result.blocks == [] and result.passes == 1


def test_text_that_survives_the_pass_budget_is_reported_not_swallowed():
    """A string we did not write, baked into the plate, is disqualifying."""
    layerizer = FakeLayerizer([[block("STUBBORN")]] * 8)

    result = harvest(b"poster", layerizer=layerizer, max_passes=3)

    assert not result.clean
    assert result.residue == ["STUBBORN"]


def test_slots_follow_reading_order_not_detection_order():
    """Detection order is arbitrary; mapping content onto it would scramble."""
    blocks = [
        block("foot", role="caption", x=50, y=900),
        block("title", role="heading", x=50, y=100),
        block("badge", role="subheading", x=400, y=300),
    ]

    template = template_from_blocks(
        blocks, name="t", plate_file="t.png", width=1080, height=1350
    )

    assert [slot.role for slot in template.slots] == [
        BlockRole.HEADLINE,
        BlockRole.BADGE,
        BlockRole.INFO_BAR,
    ]


def test_repeated_slots_of_one_role_merge_into_a_band():
    """Four one-line body slots are a bullet list, not four components."""
    blocks = [block(f"item {i}", role="body", x=50, y=500 + i * 35) for i in range(4)]

    template = template_from_blocks(
        blocks, name="t", plate_file="t.png", width=1080, height=1350
    )
    bands = template.bands()

    assert len(bands) == 1
    role, box = bands[0]
    assert role is BlockRole.PARAGRAPH
    assert box.top == 500 and box.bottom == 625


def test_an_unknown_role_still_produces_a_slot():
    template = template_from_blocks(
        [block("odd", role="watermark")], name="t", plate_file="t.png", width=10, height=10
    )

    assert template.slots[0].role is BlockRole.PARAGRAPH
    assert template.slots[0].source_role == "watermark"


@pytest.mark.parametrize(
    ("reported", "expected"),
    [
        ("Montserrat-Bold.ttf", "Outfit"),
        ("Oswald-Bold.ttf", "Archivo Narrow"),
        ("OpenSans-Regular.ttf", "Inter"),
        ("PlayfairDisplay-Black.ttf", "Playfair Display"),
        ("SomethingNobodyShips.otf", DEFAULT_FONT),
    ],
)
def test_harvested_fonts_map_to_something_we_can_embed(reported, expected):
    assert map_font(reported) == expected


def test_every_font_mapping_targets_a_family_we_actually_ship():
    """A mapping to a font with no woff2 falls back to a system face silently."""
    assert set(FONT_MAP.values()) <= set(SHIPPED_FONTS)
    assert DEFAULT_FONT in SHIPPED_FONTS


def test_every_mapped_role_is_a_real_block_role():
    assert all(isinstance(role, BlockRole) for role in ROLE_MAP.values())


def test_banking_a_template_replaces_the_one_it_supersedes(tmp_path):
    template = template_from_blocks(
        [block("a", role="heading")], name="dup", plate_file="d.png", width=10, height=10
    )
    other = template_from_blocks(
        [block("b", role="heading"), block("c", role="body")],
        name="dup",
        plate_file="d.png",
        width=10,
        height=10,
    )

    bank = LayoutBank().add(template).add(other)
    manifest = bank.save(tmp_path / "manifest.json")

    assert len(bank.templates) == 1
    assert len(LayoutBank.load(manifest).get("dup").slots) == 2


def test_a_missing_bank_is_empty_rather_than_an_error(tmp_path):
    assert LayoutBank.load(tmp_path / "absent.json").templates == []


def test_a_slot_found_late_is_flagged_for_review():
    """The word BRIGHT arrived on pass 2 and became a phantom heading slot."""
    layerizer = FakeLayerizer([[block("REAL", role="heading")], [block("BRIGHT", role="heading")], []])

    result = harvest(b"poster", layerizer=layerizer)
    template = template_from_blocks(
        result.blocks, name="t", plate_file="t.png", width=100, height=100
    )

    assert [b.found_on_pass for b in result.blocks] == [1, 2]
    assert [slot.found_on_pass for slot in template.suspect_slots()] == [2]


def test_a_clean_harvest_flags_nothing_for_review():
    layerizer = FakeLayerizer([[block("REAL", role="heading")], []])

    template = template_from_blocks(
        harvest(b"poster", layerizer=layerizer).blocks,
        name="t",
        plate_file="t.png",
        width=100,
        height=100,
    )

    assert template.suspect_slots() == []
