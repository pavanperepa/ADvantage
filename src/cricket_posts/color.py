"""Pure colour maths for deriving theme palettes from a brand palette.

No dependencies and no I/O, so every rule here is unit-testable. The important
function is :func:`ensure_contrast`: generated themes must clear the same 4.5:1
gate the deterministic audit enforces, so colours are nudged until they do rather
than hoping a hand-picked hex happens to pass.
"""

from __future__ import annotations

import math
import re

HEX_PATTERN = re.compile(r"^#?([0-9A-Fa-f]{6})$")

RGB = tuple[int, int, int]
HSL = tuple[float, float, float]


def parse_hex(value: str) -> RGB:
    match = HEX_PATTERN.match(value.strip())
    if not match:
        raise ValueError(f"Not a 6-digit hex colour: {value!r}")
    digits = match.group(1)
    return (
        int(digits[0:2], 16),
        int(digits[2:4], 16),
        int(digits[4:6], 16),
    )


def to_hex(rgb: RGB) -> str:
    return "#" + "".join(f"{max(0, min(255, round(channel))):02X}" for channel in rgb)


def rgb_to_hsl(rgb: RGB) -> HSL:
    red, green, blue = (channel / 255 for channel in rgb)
    high = max(red, green, blue)
    low = min(red, green, blue)
    lightness = (high + low) / 2
    if high == low:
        return (0.0, 0.0, lightness)
    delta = high - low
    saturation = (
        delta / (2 - high - low) if lightness > 0.5 else delta / (high + low)
    )
    if high == red:
        hue = ((green - blue) / delta) % 6
    elif high == green:
        hue = (blue - red) / delta + 2
    else:
        hue = (red - green) / delta + 4
    return (hue * 60, saturation, lightness)


def hsl_to_rgb(hsl: HSL) -> RGB:
    hue, saturation, lightness = hsl
    hue = hue % 360
    chroma = (1 - abs(2 * lightness - 1)) * saturation
    secondary = chroma * (1 - abs((hue / 60) % 2 - 1))
    offset = lightness - chroma / 2
    if hue < 60:
        parts = (chroma, secondary, 0.0)
    elif hue < 120:
        parts = (secondary, chroma, 0.0)
    elif hue < 180:
        parts = (0.0, chroma, secondary)
    elif hue < 240:
        parts = (0.0, secondary, chroma)
    elif hue < 300:
        parts = (secondary, 0.0, chroma)
    else:
        parts = (chroma, 0.0, secondary)
    return tuple(round((part + offset) * 255) for part in parts)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def with_lightness(value: str, lightness: float) -> str:
    hue, saturation, _ = rgb_to_hsl(parse_hex(value))
    return to_hex(hsl_to_rgb((hue, saturation, _clamp(lightness))))


def lighten(value: str, amount: float) -> str:
    hue, saturation, lightness = rgb_to_hsl(parse_hex(value))
    return to_hex(hsl_to_rgb((hue, saturation, _clamp(lightness + amount))))


def darken(value: str, amount: float) -> str:
    return lighten(value, -amount)


def saturate(value: str, amount: float) -> str:
    hue, saturation, lightness = rgb_to_hsl(parse_hex(value))
    return to_hex(hsl_to_rgb((hue, _clamp(saturation + amount), lightness)))


def desaturate(value: str, amount: float) -> str:
    return saturate(value, -amount)


def rotate_hue(value: str, degrees: float) -> str:
    hue, saturation, lightness = rgb_to_hsl(parse_hex(value))
    return to_hex(hsl_to_rgb((hue + degrees, saturation, lightness)))


def mix(first: str, second: str, weight: float = 0.5) -> str:
    """Blend two colours. ``weight`` is how much of ``second`` to use."""
    weight = _clamp(weight)
    left = parse_hex(first)
    right = parse_hex(second)
    return to_hex(
        tuple(
            left[index] * (1 - weight) + right[index] * weight for index in range(3)
        )
    )


def relative_luminance(value: str) -> float:
    channels = []
    for channel in parse_hex(value):
        normalized = channel / 255
        channels.append(
            normalized / 12.92
            if normalized <= 0.04045
            else math.pow((normalized + 0.055) / 1.055, 2.4)
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(first: str, second: str) -> float:
    left = relative_luminance(first)
    right = relative_luminance(second)
    lighter = max(left, right)
    darker = min(left, right)
    return (lighter + 0.05) / (darker + 0.05)


def readable_on(background: str, *candidates: str) -> str:
    """Pick whichever candidate reads best against ``background``."""
    if not candidates:
        raise ValueError("readable_on needs at least one candidate colour.")
    return max(candidates, key=lambda candidate: contrast_ratio(candidate, background))


def ensure_contrast(
    foreground: str,
    background: str,
    minimum: float = 4.5,
    steps: int = 40,
) -> str:
    """Walk ``foreground`` lighter or darker until it clears ``minimum``.

    Hue and saturation are preserved so the colour still belongs to the brand;
    only lightness moves.

    Both directions are searched rather than guessing one from the background.
    A mid-tone background can be too dark to lighten away from and too light to
    darken away from under a naive threshold, and against something like a mid
    cyan only one direction can actually reach the floor at all.
    """
    if contrast_ratio(foreground, background) >= minimum:
        return foreground
    hue, saturation, lightness = rgb_to_hsl(parse_hex(foreground))
    best: tuple[int, str] | None = None
    for direction in (1.0, -1.0):
        for step in range(1, steps + 1):
            candidate_lightness = _clamp(lightness + direction * step / steps)
            candidate = to_hex(hsl_to_rgb((hue, saturation, candidate_lightness)))
            if contrast_ratio(candidate, background) >= minimum:
                # Prefer whichever direction needed the smaller move, so the
                # colour stays as close to the supplied one as possible.
                if best is None or step < best[0]:
                    best = (step, candidate)
                break
    if best is not None:
        return best[1]
    return max(
        ("#FFFFFF", "#000000"),
        key=lambda candidate: contrast_ratio(candidate, background),
    )
