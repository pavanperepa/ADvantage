"""End-to-end: every fixture composes offline with exact copy."""

from __future__ import annotations

import json

import pytest

from cricket_posts.archetypes import ArchetypeId
from cricket_posts.blocks import derive_blocks
from cricket_posts.models import BrandProfile, ColorMode, StyleIntent, parse_editable_content
from cricket_posts.pipeline import PosterComposer, sample_zone_color
from cricket_posts.plates import PlateBank
from cricket_posts.renderer import PROJECT_ROOT
from cricket_posts.theme import build_theme, theme_contrast_report

def poster_fixture_names() -> list[str]:
    names: list[str] = []
    for path in sorted((PROJECT_ROOT / "fixtures").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        content = payload.get("content", payload) if isinstance(payload, dict) else payload
        if isinstance(content, dict) and "content_type" in content:
            names.append(path.name)
    return names


FIXTURES = poster_fixture_names()


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


@pytest.mark.parametrize("variant", ["dots", "feature", "rules"])
def test_every_bullet_variant_renders_the_same_points(variant, composer, tmp_path):
    """Variants change structure, never content — that is the whole point."""
    content, brand = load("lane-rental-houston.json")

    result = composer.compose(
        content, brand, tmp_path / f"{variant}.png", bullets_variant=variant
    )

    assert result.missing_copy == [], f"copy lost: {result.missing_copy}"
    assert result.clipped_copy == [], f"cropped: {result.clipped_copy}"


def test_variant_specs_spread_across_plates_rather_than_clustering():
    """Six posters that share a plate are the sameness this exists to avoid."""
    from cricket_posts.pipeline import variant_specs

    specs = variant_specs(PlateBank.load(), count=6)

    assert len(specs) == 6
    assert len({spec.plate_file for spec in specs}) == 6


def test_variant_specs_are_deterministic():
    """Same content and bank must always offer the same set to choose from."""
    from cricket_posts.pipeline import variant_specs

    assert variant_specs(PlateBank.load(), count=5) == variant_specs(
        PlateBank.load(), count=5
    )


def test_variant_specs_survive_a_bank_smaller_than_the_request():
    from cricket_posts.plates import PlateBank as Bank
    from cricket_posts.pipeline import variant_specs

    assert variant_specs(Bank(), count=6) == []


def test_a_narrow_canvas_wraps_the_contact_bar_instead_of_cropping_it(
    composer, tmp_path
):
    """The 1080 plates could not fit the bar on one row and cropped the phones.

    Values are `nowrap` so a number never breaks mid-digit, which means an
    over-wide row loses its last digits while still reporting the full string
    in the DOM. Wrapping keeps every cell whole at any canvas width.
    """
    content, brand = load("lane-rental-houston.json")

    result = composer.compose(
        content, brand, tmp_path / "narrow.png", plate_file="austin-geometric-left-01.png"
    )

    assert result.plate.freespace.width == 1080
    assert result.clipped_copy == [], f"cropped: {result.clipped_copy}"


def test_a_lane_rental_never_lands_on_a_childrens_plate():
    """Wrong artwork is a worse failure than repetitive artwork.

    Intent tags are not enough on their own: a confetti-and-balloons plate is
    legitimately "bright_vibrant", and matching on mood alone put an adult
    offer on a children's party.
    """
    from cricket_posts.models import ContentType
    from cricket_posts.pipeline import variant_specs

    bank = PlateBank.load()
    kids = {
        entry.file
        for entry in bank.entries
        if entry.content_types and ContentType.LANE_RENTAL not in entry.content_types
    }
    assert kids, "expected some plates to be restricted away from lane rentals"

    specs = variant_specs(bank, count=6, content_type=ContentType.LANE_RENTAL)

    assert {spec.plate_file for spec in specs}.isdisjoint(kids)


def test_content_type_filtering_outranks_mood():
    """Relaxing archetype or intent is fine; relaxing content type is not."""
    from cricket_posts.models import ContentType

    for entry in PlateBank.load().candidates(content_type=ContentType.LANE_RENTAL):
        assert not entry.content_types or ContentType.LANE_RENTAL in entry.content_types


def test_a_poster_gets_the_brand_logo_without_being_asked(composer, tmp_path):
    """Correct branding must not depend on remembering a flag."""
    content, brand = load("lane-rental-houston.json")
    assert brand.logo_path, "the Houston fixture should carry its own mark"

    result = composer.compose(content, brand, tmp_path / "logo.png")

    html = result.html.read_text(encoding="utf-8")
    assert "22yards-houston.png" in html


def test_a_logo_path_that_no_longer_resolves_is_dropped_not_fatal():
    """A missing file must not break the render, and must not draw a stranger."""
    from cricket_posts.pipeline import brand_logo

    assert brand_logo(BrandProfile(name="x", logo_path="assets/brand/gone.png")) is None
    assert brand_logo(BrandProfile(name="x")) is None


def test_the_printed_link_and_the_scanned_link_differ_on_purpose(composer, tmp_path):
    """Short enough to type; tagged enough to attribute. Both, not one."""
    content, brand = load("foundation-program-houston.json")

    result = composer.compose(
        content, brand, tmp_path / "qr.png", campaign="aug", source="instagram"
    )

    printed = [line for line in content.cta_lines if "axon22yards" in line]
    assert printed == ["axon22yards.com/join"], "printed link must stay typeable"
    assert "utm_campaign=aug" in result.scan_url
    assert "location=houston" in result.scan_url
    # The tagged URL is for the caption. Nobody should ever have to read a
    # query string off a poster, so it must not reach the artwork.
    assert "utm_campaign" not in result.html.read_text(encoding="utf-8")


def test_no_campaign_still_renders_and_still_carries_the_destination(composer, tmp_path):
    content, brand = load("foundation-program-houston.json")

    result = composer.compose(content, brand, tmp_path / "plain.png")

    assert result.scan_url == brand.registration_url
    assert result.missing_copy == []


def test_a_feed_post_carries_no_qr_by_default(composer, tmp_path):
    """Scanning a code with the phone that is displaying it is friction.

    The QR belongs on a printed flyer or facility signage; on a feed post the
    tagged link goes in the caption, one tap away.
    """
    content, brand = load("foundation-program-houston.json")

    plain = composer.compose(
        content, brand, tmp_path / "social.png", campaign="aug", source="instagram"
    )
    printed = composer.compose(
        content,
        brand,
        tmp_path / "flyer.png",
        campaign="aug",
        source="instagram",
        include_qr=True,
    )

    assert "data:image/png" not in plain.html.read_text(encoding="utf-8")
    assert "data:image/png" in printed.html.read_text(encoding="utf-8")
    # The tag is still produced either way — the caption needs it regardless.
    assert plain.scan_url == printed.scan_url


def test_two_column_layouts_do_not_stretch_their_blocks(composer, tmp_path):
    """Grid items fill their row by default, and a pill is not a pill when tall.

    `bottom_third` is the only two-column archetype and had no plate behind it
    until now, so this went unnoticed: a short chip row sharing a row with the
    price card grew to match it, and a 999px radius on a stretched box renders
    as an ellipse with the text spilling out of the top.
    """
    content, brand = load("after-school-houston.json")

    result = composer.compose(
        content,
        brand,
        tmp_path / "twocol.png",
        archetype_id=ArchetypeId.BOTTOM_THIRD,
        plate_file="dusk-floodlit-bottom-01.png",
    )

    session = composer.renderer._session()
    page = session.browser.new_page(viewport={"width": 800, "height": 600})
    try:
        page.goto(result.html.resolve().as_uri(), wait_until="networkidle")
        chips = page.evaluate(
            """() => [...document.querySelectorAll('.c-stats__chip')].map(el => {
                 const b = el.getBoundingClientRect();
                 return {w: b.width, h: b.height};
               })"""
        )
    finally:
        page.close()

    assert chips, "expected the detail lines to render as chips"
    for chip in chips:
        assert chip["h"] < chip["w"] / 2, f"chip stretched into an ellipse: {chip}"
