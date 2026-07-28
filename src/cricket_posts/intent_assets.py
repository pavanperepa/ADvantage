from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw

from .models import DesignSpec, IntentKind, Palette


IconDrawer = Callable[[ImageDraw.ImageDraw, str], None]


def _dumbbell(draw: ImageDraw.ImageDraw, color: str) -> None:
    draw.line((20, 36, 52, 36), fill=color, width=6)
    for x in (15, 51):
        draw.rounded_rectangle((x, 25, x + 6, 47), 2, fill=color)
    for x in (9, 57):
        draw.rounded_rectangle((x, 29, x + 6, 43), 2, fill=color)


def _target(draw: ImageDraw.ImageDraw, color: str) -> None:
    for inset in (10, 18, 27):
        draw.ellipse((inset, inset, 72 - inset, 72 - inset), outline=color, width=4)
    draw.line((36, 5, 36, 19), fill=color, width=4)
    draw.line((53, 19, 65, 7), fill=color, width=4)


def _book(draw: ImageDraw.ImageDraw, color: str) -> None:
    draw.line((36, 18, 36, 57), fill=color, width=4)
    draw.polygon([(10, 15), (33, 21), (33, 58), (10, 52)], outline=color)
    draw.polygon([(62, 15), (39, 21), (39, 58), (62, 52)], outline=color)
    draw.line((15, 25, 28, 29), fill=color, width=3)
    draw.line((44, 29, 57, 25), fill=color, width=3)


def _spark(draw: ImageDraw.ImageDraw, color: str) -> None:
    draw.polygon(
        [(36, 7), (42, 27), (63, 28), (46, 40), (51, 61), (36, 48), (21, 61), (26, 40), (9, 28), (30, 27)],
        fill=color,
    )


def _bat(draw: ImageDraw.ImageDraw, color: str) -> None:
    draw.polygon([(22, 55), (31, 61), (53, 24), (44, 18)], fill=color)
    draw.line((50, 20, 58, 9), fill=color, width=5)
    draw.ellipse((11, 12, 23, 24), fill=color)


def _ball(draw: ImageDraw.ImageDraw, color: str) -> None:
    draw.ellipse((12, 12, 60, 60), outline=color, width=5)
    draw.arc((25, 10, 47, 62), 80, 280, fill=color, width=4)
    draw.arc((25, 10, 47, 62), 260, 100, fill=color, width=4)


def _pulse(draw: ImageDraw.ImageDraw, color: str) -> None:
    draw.line(
        [(7, 40), (20, 40), (27, 24), (36, 52), (44, 31), (51, 40), (65, 40)],
        fill=color,
        width=5,
        joint="curve",
    )


def _people(draw: ImageDraw.ImageDraw, color: str) -> None:
    draw.ellipse((12, 12, 29, 29), fill=color)
    draw.ellipse((42, 17, 58, 33), fill=color)
    draw.arc((5, 26, 38, 65), 190, 350, fill=color, width=6)
    draw.arc((35, 31, 65, 64), 190, 350, fill=color, width=6)


def _calendar(draw: ImageDraw.ImageDraw, color: str) -> None:
    draw.rounded_rectangle((11, 16, 61, 60), 5, outline=color, width=5)
    draw.line((12, 29, 60, 29), fill=color, width=4)
    draw.line((23, 10, 23, 23), fill=color, width=5)
    draw.line((49, 10, 49, 23), fill=color, width=5)


def _check(draw: ImageDraw.ImageDraw, color: str) -> None:
    draw.rounded_rectangle((12, 12, 60, 60), 8, outline=color, width=5)
    draw.line((22, 37, 32, 47, 52, 25), fill=color, width=6, joint="curve")


def _trophy(draw: ImageDraw.ImageDraw, color: str) -> None:
    draw.pieslice((20, 10, 52, 45), 0, 180, fill=color)
    draw.arc((7, 13, 29, 39), 80, 280, fill=color, width=4)
    draw.arc((43, 13, 65, 39), 260, 100, fill=color, width=4)
    draw.line((36, 37, 36, 55), fill=color, width=5)
    draw.line((24, 58, 48, 58), fill=color, width=6)


def _wickets(draw: ImageDraw.ImageDraw, color: str) -> None:
    for x in (22, 36, 50):
        draw.line((x, 18, x, 59), fill=color, width=5)
    draw.line((18, 17, 40, 17), fill=color, width=4)
    draw.line((34, 12, 55, 12), fill=color, width=4)


def _phone(draw: ImageDraw.ImageDraw, color: str) -> None:
    draw.arc((15, 10, 57, 62), 125, 315, fill=color, width=8)
    draw.line((18, 19, 28, 29), fill=color, width=8)
    draw.line((45, 46, 55, 55), fill=color, width=8)


def _pin(draw: ImageDraw.ImageDraw, color: str) -> None:
    draw.ellipse((18, 9, 54, 45), outline=color, width=5)
    draw.polygon([(20, 35), (52, 35), (36, 64)], fill=color)
    draw.ellipse((29, 20, 43, 34), fill="#000000")


ICON_DRAWERS: dict[IntentKind, IconDrawer] = {
    IntentKind.STRENGTH: _dumbbell,
    IntentKind.COORDINATION: _target,
    IntentKind.LEARNING: _book,
    IntentKind.FUN: _spark,
    IntentKind.BATTING: _bat,
    IntentKind.BOWLING: _ball,
    IntentKind.FITNESS: _pulse,
    IntentKind.COACHING: _people,
    IntentKind.FRIENDSHIP: _people,
    IntentKind.CONFIDENCE: _check,
    IntentKind.SCHEDULE: _calendar,
    IntentKind.REGISTRATION: _check,
    IntentKind.TROPHY: _trophy,
    IntentKind.FACILITY: _wickets,
    IntentKind.CONTACT: _phone,
    IntentKind.LOCATION: _pin,
    IntentKind.GENERIC: _spark,
}


def _render_icon(path: Path, kind: IntentKind, palette: Palette) -> Path:
    scale = 3
    image = Image.new("RGBA", (72 * scale, 72 * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (2 * scale, 2 * scale, 70 * scale, 70 * scale),
        radius=18 * scale,
        fill=palette.accent,
    )
    small = Image.new("RGBA", (72, 72), (0, 0, 0, 0))
    small_draw = ImageDraw.Draw(small)
    ICON_DRAWERS[kind](small_draw, palette.ink)
    image.alpha_composite(small.resize(image.size, Image.Resampling.NEAREST))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.resize((72, 72), Image.Resampling.LANCZOS).save(path, "PNG", optimize=True)
    return path


def ensure_intent_assets(
    destination: Path,
    design: DesignSpec,
) -> dict[str, str]:
    assets: dict[str, str] = {}
    for intent in design.visual_intents:
        path = destination / f"{intent.kind.value}.png"
        if not path.exists():
            _render_icon(path, intent.kind, design.palette)
        assets[intent.source_text] = path.resolve().as_uri()
    return assets
