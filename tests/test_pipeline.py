"""End-to-end: every fixture composes offline with exact copy."""

from __future__ import annotations

import json

import pytest

from cricket_posts.blocks import derive_blocks
from cricket_posts.models import BrandProfile, ColorMode, StyleIntent, parse_editable_content
from cricket_posts.pipeline import PosterComposer, sample_zone_color
from cricket_posts.plates import PlateBank
from cricket_posts.renderer import PROJECT_ROOT
from cricket_posts.theme import build_theme, theme_contrast_report

FIXTURES = sorted(path.name for path in (PROJECT_ROOT / "fixtures").glob("*.json"))


@pytest.fixture(scope="module")
def composer():
    if not PlateBank.load().entries:
        pytest.skip("plate bank is empty; run `cricket-posts bank plates`")
    instance = PosterComposer()
    yield instance
    instance.renderer.close()


def load(name: str):
    payload = json.loads((PROJECT_ROOT / "fixtures" / name).read_text(encoding="utf-8"))
    brand = (
        BrandProfile.model_validate(payload["brand"])
        if "brand" in payload
        else BrandProfile(name="Test Academy")
    )
    return parse_editable_content(payload.get("content", payload)), brand


@pytest.mark.parametrize("name", FIXTURES)
def test_every_fixture_composes_with_verbatim_copy(name, composer, tmp_path):
    content, brand = load(name)

    result = composer.compose(content, brand, tmp_path / f"{name}.png")

    assert result.poster.exists()
    assert result.missing_copy == [], f"copy lost: {result.missing_copy}"
    assert result.fit.fits, f"overlong: {result.fit.overlong_fields}"


def test_every_fixture_renders_its_contact_details_uncropped(composer, tmp_path):
    """The bar sets its values `nowrap`, so overflow crops rather than reflows."""
    content, brand = load("foundation-program-houston.json")

    result = composer.compose(content, brand, tmp_path / "clean.png")

    assert result.clipped_copy == [], f"cropped: {result.clipped_copy}"


def test_a_contact_value_too_wide_for_the_canvas_is_reported(composer, tmp_path):
    """A phone number cropped mid-string is worse than one left out entirely.

    innerText still reports it in full, so the verbatim check cannot see this;
    without a geometry check it fails silently.
    """
    content, brand = load("foundation-program-houston.json")
    content.location_lines = [
        "22 Yards Houston Cricket Facility at " + "Westpark " * 30
    ]

    result = composer.compose(content, brand, tmp_path / "wide.png")

    assert result.missing_copy == []
    assert result.clipped_copy, "an over-wide contact value went unreported"


def test_poster_matches_the_plate_dimensions(composer, tmp_path):
    from PIL import Image

    content, brand = load("information.json")
    result = composer.compose(content, brand, tmp_path / "sized.png")

    with Image.open(result.poster) as image:
        assert image.size == (result.plate.freespace.width, result.plate.freespace.height)


def test_copy_is_placed_inside_the_measured_calm_zone(composer, tmp_path):
    """The zone comes from pixels, never from the prompt's promise."""
    content, brand = load("foundation-program-houston.json")
    result = composer.compose(content, brand, tmp_path / "zoned.png")

    assert result.zone.area > 0
    assert result.zone.right <= result.plate.freespace.width
    assert result.zone.bottom <= result.plate.freespace.height


def test_short_copy_is_grown_or_centred_rather_than_left_hanging(composer, tmp_path):
    content, brand = load("information.json")
    result = composer.compose(content, brand, tmp_path / "short.png")

    # Either the ladder reached the fill band, or it gave up and centred.
    assert result.fit.fill >= 0.78 or result.fit.state.centered


def test_theme_is_solved_against_the_plate_not_an_assumed_panel(composer, tmp_path):
    content, brand = load("information.json")
    result = composer.compose(content, brand, tmp_path / "themed.png")

    report = theme_contrast_report(result.theme)
    assert report["text_on_backdrop"] >= 4.5


def test_sampled_backdrop_changes_the_resolved_text_colour():
    palette = BrandProfile(name="x").palette
    on_dark = build_theme(StyleIntent.BOLD_ATTENTION, palette, ColorMode.DARK)
    on_light = build_theme(
        StyleIntent.BOLD_ATTENTION, palette, ColorMode.DARK, backdrop="#F4EFE3"
    )

    assert on_dark.colors.text != on_light.colors.text


@pytest.mark.parametrize("intent", list(StyleIntent))
def test_each_intent_composes(intent, composer, tmp_path):
    content, brand = load("coaching-services.json")

    result = composer.compose(
        content, brand, tmp_path / f"{intent.value}.png", intent=intent
    )

    assert result.missing_copy == []
    assert result.theme.intent is intent


def test_blocks_and_render_agree_on_what_should_appear(composer, tmp_path):
    content, brand = load("summer-camp.json")
    blocks = derive_blocks(content, brand)

    result = composer.compose(content, brand, tmp_path / "agree.png")

    rendered_roles = {block.role for block in result.fit.blocks}
    assert rendered_roles.issubset({block.role for block in blocks})


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("MONTHLY PASS $125", ("MONTHLY PASS", "$125")),
        ("FROM $35 / HOUR", ("FROM", "$35 / HOUR")),
        ("$1,250.00", ("", "$1,250.00")),
        ("EARLY BIRD PRICING", None),
        ("", None),
    ],
)
def test_a_price_splits_without_being_rewritten(line, expected):
    from cricket_posts.pipeline import split_price

    assert split_price(line) == expected


@pytest.mark.parametrize(
    "line", ["MONTHLY PASS $125", "FROM $35 / HOUR", "SUMMER CAMP $499 PER CHILD"]
)
def test_the_two_halves_of_a_price_rejoin_into_the_source_line(line):
    """The card sizes the figure differently; it must not alter the words."""
    from cricket_posts.pipeline import split_price

    label, amount = split_price(line)

    assert " ".join(part for part in (label, amount) if part) == line
