from __future__ import annotations

import re

import pytest

from cricket_posts.color import contrast_ratio, parse_hex, rgb_to_hsl
from cricket_posts.models import ColorMode, FontPreset, Palette, StyleIntent
from cricket_posts.renderer import ASSET_DIR, TEMPLATE_DIR
from cricket_posts.studio_renderer import FONT_STACKS
from cricket_posts.theme import (
    BODY_CONTRAST_FLOOR,
    HEADING_CONTRAST_FLOOR,
    INTENT_RECIPES,
    build_theme,
    theme_contrast_report,
)


FONT_DIR = ASSET_DIR / "fonts"
BRAND = Palette(ink="#071426", surface="#F6F1E6", accent="#FFD23F", highlight="#21C7FF")
MODES = (ColorMode.DARK, ColorMode.LIGHT)


def display_family(preset: FontPreset) -> str:
    """First family in the preset's display stack, as a font-file slug."""
    first = FONT_STACKS[preset.value]["display"].split(",")[0].strip()
    return first.lower().replace(" ", "-")


def body_family(preset: FontPreset) -> str:
    first = FONT_STACKS[preset.value]["body"].split(",")[0].strip()
    return first.lower().replace(" ", "-")


@pytest.mark.parametrize("intent", list(StyleIntent))
@pytest.mark.parametrize("mode", MODES)
def test_every_theme_clears_the_audit_contrast_floors(intent, mode):
    report = theme_contrast_report(build_theme(intent, BRAND, mode))

    assert report["text_on_panel"] >= BODY_CONTRAST_FLOOR
    assert report["muted_on_panel"] >= BODY_CONTRAST_FLOOR
    assert report["text_on_bg"] >= BODY_CONTRAST_FLOOR
    assert report["accent_text_on_accent"] >= BODY_CONTRAST_FLOOR
    assert report["heading_on_panel"] >= HEADING_CONTRAST_FLOOR


@pytest.mark.parametrize("intent", list(StyleIntent))
@pytest.mark.parametrize("mode", MODES)
def test_chip_and_frame_colours_are_legible(intent, mode):
    colors = build_theme(intent, BRAND, mode).colors

    assert contrast_ratio(colors.highlight_text, colors.highlight) >= BODY_CONTRAST_FLOOR
    # The photo mount has to be visible against the page it sits on.
    assert contrast_ratio(colors.frame, colors.bg) >= 2.0


@pytest.mark.parametrize("mode", MODES)
def test_brand_accent_hue_survives_every_intent(mode):
    brand_hue = rgb_to_hsl(parse_hex(BRAND.accent))[0]

    for intent in StyleIntent:
        accent = build_theme(intent, BRAND, mode).colors.accent
        # Saturation and lightness may move; the hue is the brand and must not.
        assert rgb_to_hsl(parse_hex(accent))[0] == pytest.approx(brand_hue, abs=2.0)


def test_each_intent_selects_a_distinct_typeface():
    presets = [build_theme(intent, BRAND).font_preset for intent in StyleIntent]

    assert len(set(presets)) == len(list(StyleIntent))


def test_an_explicit_font_preset_overrides_the_intent_default():
    theme = build_theme(
        StyleIntent.PLAYFUL_FUN, BRAND, ColorMode.DARK, FontPreset.IMPACT
    )

    assert theme.font_preset == FontPreset.IMPACT
    assert theme.intent == StyleIntent.PLAYFUL_FUN


def test_intents_differ_across_several_design_axes():
    minimal = build_theme(StyleIntent.MINIMAL_CLEAN, BRAND)
    playful = build_theme(StyleIntent.PLAYFUL_FUN, BRAND)

    # Variations must be more than a colour tweak.
    assert minimal.radius_px != playful.radius_px
    assert minimal.decoration != playful.decoration
    assert minimal.font_preset != playful.font_preset
    assert minimal.spacing_bias != playful.spacing_bias
    assert minimal.shadow_strength != playful.shadow_strength


def test_minimal_intent_is_airier_and_flatter_than_bold():
    minimal = build_theme(StyleIntent.MINIMAL_CLEAN, BRAND)
    bold = build_theme(StyleIntent.BOLD_ATTENTION, BRAND)

    assert minimal.spacing_bias > bold.spacing_bias
    assert minimal.shadow_strength < bold.shadow_strength
    assert minimal.accent_bar_px < bold.accent_bar_px


@pytest.mark.parametrize("preset", list(FontPreset))
def test_every_preset_requests_a_weight_that_is_actually_bundled(preset):
    """Guards against faux-bold: asking for a weight with no file behind it."""
    available = {path.stem for path in FONT_DIR.glob("*.woff2")}
    intents = [
        intent
        for intent, recipe in INTENT_RECIPES.items()
        if recipe.font_preset == preset
    ]
    for intent in intents:
        theme = build_theme(intent, BRAND, ColorMode.DARK, preset)
        assert f"{display_family(preset)}-{theme.display_weight}" in available
        assert f"{body_family(preset)}-{theme.body_weight}" in available


def test_font_css_only_references_files_that_exist():
    css = (TEMPLATE_DIR / "studio" / "fonts.css").read_text(encoding="utf-8")
    referenced = re.findall(r'url\("\.\./\.\./assets/fonts/([^"]+)"\)', css)

    assert referenced
    for name in referenced:
        assert (FONT_DIR / name).exists(), f"fonts.css points at missing {name}"


def test_every_font_stack_names_a_bundled_family_first():
    bundled = {path.stem.rsplit("-", 1)[0] for path in FONT_DIR.glob("*.woff2")}

    for preset in FontPreset:
        assert display_family(preset) in bundled
        assert body_family(preset) in bundled


def test_theme_carries_no_case_transform():
    """Restyling copy to uppercase would alter innerText and break the copy audit."""
    theme = build_theme(StyleIntent.BOLD_ATTENTION, BRAND)

    assert not hasattr(theme, "display_case")
