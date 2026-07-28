from __future__ import annotations

import json

import pytest

from cricket_posts.blocks import (
    BlockPriority,
    BlockRole,
    block_values,
    by_priority,
    derive_blocks,
    duplicated_in_blocks,
    missing_from_blocks,
)
from cricket_posts.layout import poster_copy_lines
from cricket_posts.models import BrandProfile, parse_editable_content
from cricket_posts.renderer import PROJECT_ROOT

FIXTURES = sorted(path.name for path in (PROJECT_ROOT / "fixtures").glob("*.json"))


def load(name: str):
    payload = json.loads((PROJECT_ROOT / "fixtures" / name).read_text(encoding="utf-8"))
    brand = (
        BrandProfile.model_validate(payload["brand"])
        if isinstance(payload, dict) and "brand" in payload
        else BrandProfile(name="Test Academy")
    )
    content = parse_editable_content(
        payload.get("content", payload) if isinstance(payload, dict) else payload
    )
    return content, brand


@pytest.mark.parametrize("name", FIXTURES)
def test_every_source_string_is_owned_by_exactly_one_block(name):
    content, brand = load(name)
    blocks = derive_blocks(content, brand)

    assert missing_from_blocks(blocks, poster_copy_lines(content, brand)) == []
    assert duplicated_in_blocks(blocks) == []


@pytest.mark.parametrize("name", FIXTURES)
def test_blocks_never_invent_copy(name):
    content, brand = load(name)
    source = set(poster_copy_lines(content, brand))

    for value in block_values(derive_blocks(content, brand)):
        assert value in source, f"block produced a string not present in the source: {value!r}"


@pytest.mark.parametrize("name", FIXTURES)
def test_identity_and_contact_are_always_required(name):
    content, brand = load(name)
    roles = {
        block.role
        for block in by_priority(derive_blocks(content, brand), BlockPriority.REQUIRED)
    }

    assert BlockRole.HEADLINE in roles
    assert BlockRole.LOCKUP in roles
    assert BlockRole.INFO_BAR in roles


def test_optional_blocks_exist_to_fill_space():
    """Without optional blocks the fit engine has no way to close a gap."""
    content, brand = load("foundation-program-houston.json")
    optional = by_priority(derive_blocks(content, brand), BlockPriority.OPTIONAL)

    assert optional, "expected at least one promotable block"
    assert {block.role for block in optional} & {
        BlockRole.RIBBON,
        BlockRole.BANNER,
        BlockRole.STAT_CHIPS,
    }


def test_contact_details_land_in_the_info_bar():
    content, brand = load("foundation-program-houston.json")
    blocks = derive_blocks(content, brand)
    bar = next(block for block in blocks if block.role is BlockRole.INFO_BAR)

    for value in ("+1 (713) 498-2155", "+1 (737) 323-0270", "Houston, TX 77082"):
        assert value in bar.values


def test_bullet_sections_keep_their_heading_and_items_together():
    content, brand = load("summer-camp.json")
    bullets = [
        block
        for block in derive_blocks(content, brand)
        if block.role is BlockRole.BULLETS
    ]

    assert bullets
    assert all(block.splittable for block in bullets)
    assert any(len(block.values) > 2 for block in bullets)


def test_tournament_categories_become_their_own_blocks():
    content, brand = load("svats-cup.json")
    categories = [
        block
        for block in derive_blocks(content, brand)
        if block.role is BlockRole.CATEGORY
    ]

    assert len(categories) >= 1
    assert all(block.heading for block in categories)
