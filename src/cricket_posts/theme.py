"""Resolve a StyleIntent plus a brand palette into a concrete ThemePack.

The brand's hues are never swapped out — that would break the visual consistency
the academy relies on. What an intent changes is how those hues are *deployed*:
how dominant the accent is, how much the surfaces are tinted, how the type is
set, how much shape and decoration the design carries, and how much air it gets.

Every colour that carries text is passed through ``ensure_contrast`` so a
generated theme cannot fail the deterministic 4.5:1 audit gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .color import (
    contrast_ratio,
    darken,
    desaturate,
    ensure_contrast,
    lighten,
    mix,
    readable_on,
    saturate,
)
from .models import (
    ColorMode,
    Decoration,
    FontPreset,
    Palette,
    StyleIntent,
    ThemeColors,
    ThemePack,
)

BODY_CONTRAST_FLOOR = 4.5
# Headings are large, so WCAG allows 3:1. Keeping a little margin above that.
HEADING_CONTRAST_FLOOR = 3.5


@dataclass(frozen=True)
class IntentRecipe:
    font_preset: FontPreset
    display_weight: int = 700
    display_tracking: float = 0.0
    body_weight: int = 400
    radius_px: int = 0
    border_width_px: int = 1
    accent_bar_px: int = 5
    panel_opacity: float = 0.88
    shadow_strength: float = 0.2
    spacing_bias: float = 1.0
    decoration: Decoration = Decoration.GRADIENT
    # colour deployment
    accent_saturation: float = 0.0
    surface_tint: float = 0.0
    panel_lift: float = 0.04
    heading_uses_accent: bool = True
    field_notes: str = field(default="")


INTENT_RECIPES: dict[StyleIntent, IntentRecipe] = {
    StyleIntent.BRIGHT_VIBRANT: IntentRecipe(
        font_preset=FontPreset.ROUNDED,
        display_weight=700,
        display_tracking=-0.01,
        body_weight=400,
        radius_px=22,
        border_width_px=0,
        accent_bar_px=0,
        panel_opacity=0.92,
        shadow_strength=0.34,
        spacing_bias=1.0,
        decoration=Decoration.SHAPES,
        accent_saturation=0.22,
        surface_tint=0.14,
        panel_lift=0.10,
        field_notes="saturated accent, tinted panels, soft rounded cards",
    ),
    StyleIntent.MINIMAL_CLEAN: IntentRecipe(
        font_preset=FontPreset.GEOMETRIC,
        display_weight=600,
        display_tracking=-0.02,
        body_weight=400,
        radius_px=4,
        border_width_px=1,
        accent_bar_px=0,
        panel_opacity=0.72,
        shadow_strength=0.0,
        spacing_bias=1.28,
        decoration=Decoration.NONE,
        accent_saturation=-0.30,
        surface_tint=0.0,
        panel_lift=0.03,
        heading_uses_accent=False,
        field_notes="accent reduced to a whisper, no shadow, generous air",
    ),
    StyleIntent.PREMIUM_ELEGANT: IntentRecipe(
        font_preset=FontPreset.EDITORIAL,
        display_weight=700,
        display_tracking=-0.025,
        body_weight=400,
        radius_px=2,
        border_width_px=1,
        accent_bar_px=2,
        panel_opacity=0.80,
        shadow_strength=0.10,
        spacing_bias=1.18,
        decoration=Decoration.SPOTLIGHT,
        accent_saturation=-0.22,
        surface_tint=0.05,
        panel_lift=0.05,
        field_notes="desaturated metallics, hairline rules, serif display",
    ),
    StyleIntent.BOLD_ATTENTION: IntentRecipe(
        font_preset=FontPreset.IMPACT,
        # Archivo Black ships one weight and is already black; asking for 900
        # would make the browser synthesize a smeared faux-bold.
        display_weight=400,
        display_tracking=-0.005,
        body_weight=600,
        radius_px=0,
        border_width_px=0,
        accent_bar_px=12,
        panel_opacity=0.94,
        shadow_strength=0.30,
        spacing_bias=0.92,
        decoration=Decoration.DIAGONAL,
        accent_saturation=0.18,
        surface_tint=0.06,
        panel_lift=0.07,
        field_notes="heavy slabs, thick accent bars, maximum contrast",
    ),
    StyleIntent.PROFESSIONAL_CLEAN: IntentRecipe(
        font_preset=FontPreset.MODERN,
        display_weight=700,
        display_tracking=0.0,
        body_weight=400,
        radius_px=8,
        border_width_px=1,
        accent_bar_px=4,
        panel_opacity=0.88,
        shadow_strength=0.16,
        spacing_bias=1.08,
        decoration=Decoration.GRADIENT,
        accent_saturation=-0.10,
        surface_tint=0.02,
        panel_lift=0.05,
        field_notes="restrained corporate palette, even rhythm",
    ),
    StyleIntent.YOUTHFUL_ENERGETIC: IntentRecipe(
        font_preset=FontPreset.ATHLETIC,
        display_weight=400,
        display_tracking=0.01,
        body_weight=600,
        radius_px=14,
        border_width_px=0,
        accent_bar_px=8,
        panel_opacity=0.90,
        shadow_strength=0.30,
        spacing_bias=0.96,
        decoration=Decoration.DIAGONAL,
        accent_saturation=0.26,
        surface_tint=0.10,
        panel_lift=0.09,
        field_notes="condensed poster caps, punchy accent, angled energy",
    ),
    StyleIntent.PLAYFUL_FUN: IntentRecipe(
        font_preset=FontPreset.FRIENDLY,
        display_weight=700,
        display_tracking=-0.015,
        body_weight=400,
        radius_px=28,
        border_width_px=0,
        accent_bar_px=0,
        panel_opacity=0.93,
        shadow_strength=0.26,
        spacing_bias=1.04,
        decoration=Decoration.SHAPES,
        accent_saturation=0.20,
        surface_tint=0.16,
        panel_lift=0.11,
        field_notes="pill-soft cards, warm serif, high tint",
    ),
    StyleIntent.MODERN_SLEEK: IntentRecipe(
        font_preset=FontPreset.CONDENSED,
        display_weight=400,
        display_tracking=0.03,
        body_weight=400,
        radius_px=6,
        border_width_px=1,
        accent_bar_px=3,
        panel_opacity=0.78,
        shadow_strength=0.12,
        spacing_bias=1.14,
        decoration=Decoration.SPOTLIGHT,
        accent_saturation=0.04,
        surface_tint=0.0,
        panel_lift=0.04,
        field_notes="wide-tracked caps, cool surfaces, low ornament",
    ),
}


def build_theme(
    intent: StyleIntent,
    palette: Palette,
    color_mode: ColorMode = ColorMode.DARK,
    font_preset: FontPreset | None = None,
) -> ThemePack:
    recipe = INTENT_RECIPES[intent]
    dark = color_mode == ColorMode.DARK

    accent = palette.accent
    if recipe.accent_saturation > 0:
        accent = saturate(accent, recipe.accent_saturation)
    elif recipe.accent_saturation < 0:
        accent = desaturate(accent, -recipe.accent_saturation)

    base = palette.ink if dark else palette.surface
    opposite = palette.surface if dark else palette.ink

    # Tinting pulls the accent hue into the background so the whole poster reads
    # as one colour family instead of neutral boxes with a coloured highlight.
    bg = mix(base, accent, recipe.surface_tint)
    panel = lighten(bg, recipe.panel_lift) if dark else darken(bg, recipe.panel_lift)
    panel_border = (
        lighten(panel, 0.16) if dark else darken(panel, 0.14)
    )

    text = ensure_contrast(opposite, panel, BODY_CONTRAST_FLOOR)
    text_muted = ensure_contrast(
        mix(text, panel, 0.32), panel, BODY_CONTRAST_FLOOR
    )
    heading_source = accent if recipe.heading_uses_accent else text
    # A bright accent set as small type on a light surface has to be darkened so
    # far to clear the contrast floor that it turns muddy. Designers keep the
    # accent vivid as a fill and set the heading in ink instead, so do that
    # rather than degrading the brand colour into olive.
    if (
        recipe.heading_uses_accent
        and contrast_ratio(accent, panel) < HEADING_CONTRAST_FLOOR
    ):
        heading_source = text
    heading = ensure_contrast(heading_source, panel, HEADING_CONTRAST_FLOOR)
    accent_text = ensure_contrast(
        readable_on(accent, palette.ink, palette.surface),
        accent,
        BODY_CONTRAST_FLOOR,
    )
    highlight = ensure_contrast(palette.highlight, panel, HEADING_CONTRAST_FLOOR)
    highlight_text = ensure_contrast(
        readable_on(highlight, palette.ink, palette.surface),
        highlight,
        BODY_CONTRAST_FLOOR,
    )

    return ThemePack(
        intent=intent,
        font_preset=font_preset or recipe.font_preset,
        colors=ThemeColors(
            bg=bg,
            panel=panel,
            panel_border=panel_border,
            text=text,
            text_muted=text_muted,
            heading=heading,
            accent=accent,
            accent_text=accent_text,
            highlight=highlight,
            highlight_text=highlight_text,
            frame=mix(bg, text, 0.88),
        ),
        display_weight=recipe.display_weight,
        display_tracking=recipe.display_tracking,
        body_weight=recipe.body_weight,
        radius_px=recipe.radius_px,
        border_width_px=recipe.border_width_px,
        accent_bar_px=recipe.accent_bar_px,
        panel_opacity=recipe.panel_opacity,
        shadow_strength=recipe.shadow_strength,
        spacing_bias=recipe.spacing_bias,
        decoration=recipe.decoration,
    )


def theme_contrast_report(theme: ThemePack) -> dict[str, float]:
    """Measured ratios for the pairings the audit will check."""
    colors = theme.colors
    return {
        "text_on_panel": contrast_ratio(colors.text, colors.panel),
        "muted_on_panel": contrast_ratio(colors.text_muted, colors.panel),
        "heading_on_panel": contrast_ratio(colors.heading, colors.panel),
        "text_on_bg": contrast_ratio(colors.text, colors.bg),
        "accent_text_on_accent": contrast_ratio(colors.accent_text, colors.accent),
    }
