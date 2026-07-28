from __future__ import annotations

import pytest

from cricket_posts.color import (
    contrast_ratio,
    darken,
    desaturate,
    ensure_contrast,
    hsl_to_rgb,
    lighten,
    mix,
    parse_hex,
    readable_on,
    relative_luminance,
    rgb_to_hsl,
    rotate_hue,
    saturate,
    to_hex,
)


BRAND = ("#071426", "#F6F1E6", "#FFD23F", "#21C7FF")


def test_hex_roundtrip():
    for value in BRAND:
        assert to_hex(parse_hex(value)) == value.upper()


def test_rejects_malformed_hex():
    with pytest.raises(ValueError):
        parse_hex("#12345")


@pytest.mark.parametrize("value", BRAND)
def test_hsl_roundtrip_is_stable(value):
    restored = to_hex(hsl_to_rgb(rgb_to_hsl(parse_hex(value))))
    original = parse_hex(value)
    recovered = parse_hex(restored)
    # Allow one unit of rounding drift per channel.
    assert all(abs(a - b) <= 1 for a, b in zip(original, recovered))


def test_lighten_and_darken_move_luminance_in_the_right_direction():
    base = "#3366AA"
    assert relative_luminance(lighten(base, 0.2)) > relative_luminance(base)
    assert relative_luminance(darken(base, 0.2)) < relative_luminance(base)


def test_lighten_and_darken_clamp_at_the_extremes():
    assert lighten("#FFFFFF", 0.5) == "#FFFFFF"
    assert darken("#000000", 0.5) == "#000000"


def test_saturate_and_desaturate_move_saturation():
    base = "#3366AA"
    assert rgb_to_hsl(parse_hex(saturate(base, 0.2)))[1] > rgb_to_hsl(parse_hex(base))[1]
    assert rgb_to_hsl(parse_hex(desaturate(base, 0.2)))[1] < rgb_to_hsl(parse_hex(base))[1]


def test_rotate_hue_preserves_saturation_and_lightness():
    _, saturation, lightness = rgb_to_hsl(parse_hex("#3366AA"))
    _, rotated_s, rotated_l = rgb_to_hsl(parse_hex(rotate_hue("#3366AA", 120)))
    assert rotated_s == pytest.approx(saturation, abs=0.02)
    assert rotated_l == pytest.approx(lightness, abs=0.02)


def test_mix_endpoints_and_midpoint():
    assert mix("#000000", "#FFFFFF", 0.0) == "#000000"
    assert mix("#000000", "#FFFFFF", 1.0) == "#FFFFFF"
    assert mix("#000000", "#FFFFFF", 0.5) == "#808080"


def test_contrast_ratio_matches_known_values():
    assert contrast_ratio("#FFFFFF", "#000000") == pytest.approx(21.0, abs=0.01)
    assert contrast_ratio("#FFFFFF", "#FFFFFF") == pytest.approx(1.0, abs=0.01)


def test_readable_on_picks_the_stronger_candidate():
    assert readable_on("#FFD23F", "#071426", "#F6F1E6") == "#071426"
    assert readable_on("#071426", "#071426", "#F6F1E6") == "#F6F1E6"


@pytest.mark.parametrize(
    "foreground,background",
    [
        ("#FFD23F", "#F6F1E6"),  # yellow on cream, hopeless as supplied
        ("#21C7FF", "#FFFFFF"),
        ("#071426", "#000000"),
        ("#808080", "#7F7F7F"),
    ],
)
def test_ensure_contrast_always_reaches_the_floor(foreground, background):
    adjusted = ensure_contrast(foreground, background, 4.5)

    assert contrast_ratio(adjusted, background) >= 4.5


def test_ensure_contrast_leaves_a_passing_colour_untouched():
    assert ensure_contrast("#FFFFFF", "#071426", 4.5) == "#FFFFFF"


def test_ensure_contrast_preserves_hue_where_it_can():
    background = "#F6F1E6"
    adjusted = ensure_contrast("#FFD23F", background, 4.5)
    original_hue = rgb_to_hsl(parse_hex("#FFD23F"))[0]
    adjusted_hue = rgb_to_hsl(parse_hex(adjusted))[0]

    assert adjusted != "#FFD23F"
    assert adjusted_hue == pytest.approx(original_hue, abs=2.0)
