"""Compose a poster from the three layers.

    content JSON
      -> derive_blocks            (priority-tagged, verbatim)
      -> select plate from bank   (free-space measured, not assumed)
      -> select archetype         (matched to the calm rectangle found)
      -> select subjects          (photographs first)
      -> fit.solve                (deterministic, both directions)
      -> render canvas -> PNG
      -> score + verify copy

No Ideogram call happens here. The banks are restocked occasionally; composing a
poster is local, free and repeatable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from PIL import Image

from .archetypes import ARCHETYPES, Archetype, ArchetypeId, select_archetype
from .blocks import BlockRole, ContentBlock, block_values, derive_blocks
from dataclasses import replace

from .fit import (
    FILL_FLOOR,
    FitResult,
    FitState,
    Measurement,
    active_blocks,
    solve,
)
from .layout_score import score_layout
from .models import (
    BrandProfile,
    ColorMode,
    PosterContent,
    Rect,
    StyleIntent,
    ThemePack,
)
from .plates import PlateBank, PlateChoice, select_plate
from .renderer import PROJECT_ROOT, TEMPLATE_DIR, find_browser
from .studio_renderer import FONT_STACKS, PlaywrightRenderer, build_geometry, measure_backdrops
from .subjects import SUBJECT_DIR, SubjectBank, SubjectEntry
from .theme import build_theme

STUDIO_DIR = TEMPLATE_DIR / "studio"
DOT_COLORS = ["#4CAF50", "#F59E0B", "#1C7ED6", "#7C3AED", "#E8590C", "#0CA678"]

ICON_SVG = {
    "pin": '<svg viewBox="0 0 24 24"><path d="M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>',
    "web": '<svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm6.9 9h-3a15.6 15.6 0 0 0-1.2-5.3A8 8 0 0 1 18.9 11zM12 4.1c.8 1.1 1.5 3 1.7 6.9h-3.4c.2-3.9.9-5.8 1.7-6.9zM4.3 13h3c.1 2.1.5 4 1.2 5.3A8 8 0 0 1 4.3 13zm3-2h-3a8 8 0 0 1 4.2-5.3A15.6 15.6 0 0 0 7.3 11zM12 19.9c-.8-1.1-1.5-3-1.7-6.9h3.4c-.2 3.9-.9 5.8-1.7 6.9zm2.7-1.6c.7-1.3 1.1-3.2 1.2-5.3h3a8 8 0 0 1-4.2 5.3z"/></svg>',
    "call": '<svg viewBox="0 0 24 24"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.24 11.4 11.4 0 0 0 3.6.58 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1 11.4 11.4 0 0 0 .58 3.6 1 1 0 0 1-.25 1z"/></svg>',
}

def sample_zone_color(plate: Path, zone: Rect) -> str:
    """Median colour inside a zone: what the copy will actually sit on."""
    with Image.open(plate) as image:
        crop = image.convert("RGB").crop(
            (int(zone.left), int(zone.top), int(zone.right), int(zone.bottom))
        ).resize((12, 12), Image.Resampling.BOX)
        pixels = list(crop.getdata())
    channels = [sorted(pixel[i] for pixel in pixels) for i in range(3)]
    median = tuple(channel[len(channel) // 2] for channel in channels)
    return "#" + "".join(f"{value:02X}" for value in median)


_PHONE = re.compile(r"[+(]?\d[\d()\s\-]{6,}")
_URL = re.compile(r"[\w.-]+\.(com|org|net|io|co)(/\S*)?", re.I)


#: How tall each figure after the first stands relative to the one before it.
#: They share a floor line, so height alone carries the age difference — which
#: is the whole point of pairing a ten year old with a five year old.
COMPANION_SCALE = 0.62


def place_subjects(
    entries: list[SubjectEntry],
    slot: Rect | None,
    *,
    root: Path = SUBJECT_DIR,
    companion_scale: float = COMPANION_SCALE,
) -> list[dict]:
    """Fit cut-outs into their slot, standing on its floor.

    The first figure is the hero: scaled to the largest size that fits the slot
    on both axes and anchored to the bottom outer corner. Bottom-anchoring
    matters — a batter floating with clear air under both feet looks pasted on,
    and the contact bar sits above the subject layer so the overlap reads as
    depth rather than as a mistake.

    Every later figure keeps that same floor line and steps down in height, then
    anchors to the inner edge. Aligning the feet and varying only the height is
    what makes one child read as younger than the other instead of simply
    further away.
    """
    if slot is None or not entries:
        return []

    placed: list[dict] = []
    hero_height = 0.0
    for index, entry in enumerate(entries):
        path = entry.path(root)
        with Image.open(path) as image:
            aspect = image.width / image.height

        if index == 0:
            width = min(slot.width, slot.height * aspect)
            hero_height = width / aspect
            left = slot.right - width
        else:
            height = min(hero_height * companion_scale**index, slot.height)
            width = height * aspect
            left = slot.left
        placed.append(
            {
                "url": path.resolve().as_uri(),
                "left": int(left),
                "top": int(slot.bottom - width / aspect),
                "width": int(width),
            }
        )
    return placed


@dataclass
class ComposeResult:
    poster: Path
    html: Path
    fit: FitResult
    archetype: Archetype
    plate: PlateChoice
    theme: ThemePack
    missing_copy: list[str]
    #: Copy present in the DOM but cropped or pushed off the canvas edge.
    clipped_copy: list[str]
    score_total: float
    zone: Rect


def _info_cells(blocks: list[ContentBlock]) -> list[dict]:
    """One cell per INFO_BAR block, in source order.

    Each block already carries its own label as the heading, so no value is
    re-classified here and a label cannot drift onto the wrong column.
    """
    cells: list[dict] = []
    for block in blocks:
        # A label with nothing under it is still copy — "REGISTER NOW" arrives
        # this way when there is no link or phone for it to describe.
        values = block.values or ([block.heading] if block.heading else [])
        label = block.heading if block.values else ""
        if not values:
            continue
        joined = " ".join(values)
        if any(_PHONE.fullmatch(value.strip()) for value in block.values):
            icon = "call"
        elif "@" in joined or _URL.search(joined):
            icon = "web"
        else:
            icon = "pin"
        cells.append(
            {
                "icon": icon,
                "label": label,
                "lines": values,
                "svg": Markup(ICON_SVG[icon]),
            }
        )
    return cells


class PosterComposer:
    def __init__(
        self,
        *,
        renderer: PlaywrightRenderer | None = None,
        plate_bank: PlateBank | None = None,
        subject_bank: SubjectBank | None = None,
    ) -> None:
        self.renderer = renderer or PlaywrightRenderer()
        self.plate_bank = plate_bank if plate_bank is not None else PlateBank.load()
        self.subject_bank = (
            subject_bank if subject_bank is not None else SubjectBank.load()
        )
        self.environment = Environment(
            loader=FileSystemLoader(STUDIO_DIR),
            autoescape=select_autoescape(("html", "xml")),
        )

    def _render_html(self, context: dict, destination: Path) -> Path:
        html = self.environment.get_template("canvas.html").render(**context)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(html, encoding="utf-8")
        return destination

    def compose(
        self,
        content: PosterContent,
        brand: BrandProfile,
        destination: Path,
        *,
        intent: StyleIntent = StyleIntent.BOLD_ATTENTION,
        color_mode: ColorMode = ColorMode.DARK,
        archetype_id: ArchetypeId | None = None,
        logo_path: Path | None = None,
        plate_file: str | None = None,
        subject_files: list[str] | None = None,
    ) -> ComposeResult:
        blocks = derive_blocks(content, brand)

        plate = select_plate(
            self.plate_bank,
            archetype_id or ArchetypeId.LEFT_COLUMN,
            intent,
            only_file=plate_file,
        )
        if plate is None:
            raise RuntimeError(
                "No usable plate in the bank. Run `cricket-posts plates index` "
                "after adding background plates to assets/plates/."
            )

        chosen = select_archetype(
            [zone.box for zone in plate.freespace.zones],
            plate.freespace.width,
            plate.freespace.height,
            preferred=archetype_id,
        )
        archetype, zone = chosen if chosen else (ARCHETYPES[ArchetypeId.LEFT_COLUMN], plate.zone)

        width, height = plate.freespace.width, plate.freespace.height
        zone = archetype.shape_zone(zone, width, height)

        # Narrowing the column to the archetype's proportions usually frees up
        # depth: the plate's artwork cuts in diagonally, so a slimmer column
        # stays calm much further down than the widest-area rectangle did.
        # Without this the copy keeps the short zone and leaves a hole beneath.
        deeper = plate.freespace.tallest_within(zone.left, zone.right, zone.top)
        if deeper is not None:
            zone.bottom = min(
                max(zone.bottom, deeper.bottom),
                archetype.region_rect(width, height).bottom,
            )
        scale = width / 1728

        # Copy sits on the plate, so solve its colours against the colour the
        # plate actually is in that zone rather than an assumed panel.
        theme = build_theme(
            intent,
            brand.palette,
            color_mode,
            backdrop=sample_zone_color(plate.path, zone),
        )
        font_stack = FONT_STACKS[theme.font_preset.value]

        bar_blocks = [b for b in blocks if b.role is BlockRole.INFO_BAR]
        banner_block = next((b for b in blocks if b.role is BlockRole.BANNER), None)
        column = [b for b in blocks if b.role not in {BlockRole.INFO_BAR, BlockRole.BANNER}]

        subjects = place_subjects(
            self.subject_bank.select(
                tags=[intent.value], limit=1, only_files=subject_files
            ),
            archetype.subject_slot(zone, width, height),
        )

        html_path = destination.with_suffix(".html")

        def context_for(state: FitState, active: list[ContentBlock]) -> dict:
            return {
                "content": content,
                "brand": brand,
                "theme": theme,
                "archetype": archetype,
                "blocks": active,
                "banner_block": banner_block,
                "info_cells": _info_cells(bar_blocks),
                "subjects": subjects,
                # When the growth ladder runs out, centring turns a hole at the
                # bottom into balanced margins, which is what a designer does.
                "copy_justify": "center"
                if (state.centered or archetype.centered)
                else "flex-start",
                "zone": zone,
                "width": width,
                "height": height,
                "scale": round(scale, 4),
                "fit": {
                    "type_scale": state.type_scale,
                    "leading": state.leading,
                    "gap_px": int(state.gap_px * scale),
                },
                "plate_url": plate.path.resolve().as_uri(),
                "fonts_url": (STUDIO_DIR / "fonts.css").resolve().as_uri(),
                "canvas_css_url": (STUDIO_DIR / "canvas.css").resolve().as_uri(),
                "logo_url": logo_path.resolve().as_uri() if logo_path and logo_path.exists() else None,
                "display_font": font_stack["display"],
                "body_font": font_stack["body"],
                "dot_colors": DOT_COLORS,
            }

        session = self.renderer._session()
        page = session.browser.new_page(
            viewport={"width": width, "height": height}, device_scale_factor=1
        )
        try:
            def measure(state: FitState, active: list[ContentBlock]) -> Measurement:
                self._render_html(context_for(state, active), html_path)
                page.goto(html_path.resolve().as_uri(), wait_until="domcontentloaded")
                page.evaluate("() => document.fonts.ready.then(() => true)")
                return Measurement(
                    **page.evaluate(
                        """
                        () => {
                          const zone = document.querySelector('[data-region="copy"]');
                          const stack = document.querySelector('[data-stack]');
                          if (!zone || !stack) return { height: 0, overflow: false };
                          const height = stack.scrollHeight;
                          return {
                            height,
                            overflow: height > zone.clientHeight + 2,
                          };
                        }
                        """
                    )
                )

            result = solve([*column], zone.height, measure)
            if result.fill < FILL_FLOOR:
                result.state = replace(result.state, centered=True)

            # Final render at the solved state.
            self._render_html(context_for(result.state, result.blocks), html_path)
            page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
            page.evaluate("() => document.fonts.ready.then(() => true)")
            destination.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(
                path=str(destination),
                clip={"x": 0, "y": 0, "width": width, "height": height},
            )
            rendered_text = page.evaluate("() => document.body.innerText")
            # innerText reports what is in the DOM, not what survived to the
            # pixels. Contact values are `nowrap`, so an over-wide bar crops
            # them mid-string and the verbatim check still passes — a phone
            # number missing its last digits is worse than one left out.
            clipped = page.evaluate(
                """
                () => {
                  const out = [];
                  const frame = document.querySelector('.canvas').getBoundingClientRect();
                  // Leaf text nodes only: reporting ancestors as well just
                  // repeats the same string at every level of the tree.
                  document.querySelectorAll('[data-audit] *').forEach(el => {
                    if (el.children.length) return;
                    const text = (el.textContent || '').trim();
                    if (!text) return;
                    const box = el.getBoundingClientRect();
                    // Off the artboard is always lost: .canvas hides overflow.
                    if (box.left < frame.left - 1 || box.right > frame.right + 1
                        || box.top < frame.top - 1 || box.bottom > frame.bottom + 1) {
                      out.push(text);
                      return;
                    }
                    // Otherwise only an ancestor that actually crops counts.
                    // Spilling out of a box with visible overflow is how the
                    // display type is meant to sit against the plate.
                    for (let node = el; node && node !== document.body; node = node.parentElement) {
                      const style = getComputedStyle(node);
                      const crops = style.overflowX !== 'visible' || style.overflowY !== 'visible';
                      if (crops && (node.scrollWidth > node.clientWidth + 1
                                    || node.scrollHeight > node.clientHeight + 1)) {
                        out.push(text);
                        return;
                      }
                    }
                  });
                  return [...new Set(out)];
                }
                """
            )
        finally:
            page.close()

        def norm(value: str) -> str:
            return re.sub(r"\s+", " ", value).strip()

        visible = norm(rendered_text)
        expected = block_values([*result.blocks, *bar_blocks])
        if banner_block and banner_block.order in result.state.promoted:
            expected += banner_block.display_values()
        missing = [value for value in expected if norm(value) not in visible]

        return ComposeResult(
            poster=destination,
            html=html_path,
            fit=result,
            archetype=archetype,
            plate=plate,
            theme=theme,
            missing_copy=missing,
            clipped_copy=clipped,
            score_total=0.0,
            zone=zone,
        )
