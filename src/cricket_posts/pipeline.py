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
from .subjects import SubjectBank
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


@dataclass
class ComposeResult:
    poster: Path
    html: Path
    fit: FitResult
    archetype: Archetype
    plate: PlateChoice
    theme: ThemePack
    missing_copy: list[str]
    score_total: float
    zone: Rect


def _info_cells(block: ContentBlock) -> list[dict]:
    """Split the contact block into location / web / phone columns.

    Classification is by shape, not by rewriting: a value is only ever moved,
    never altered.
    """
    labels = [v for v in block.values if v.isupper() and not _PHONE.match(v) and len(v) < 24]
    phones = [v for v in block.values if _PHONE.fullmatch(v.strip())]
    urls = [v for v in block.values if _URL.search(v) and " " not in v]
    used = set(labels) | set(phones) | set(urls)
    location = [v for v in block.values if v not in used]

    cells: list[dict] = []
    if location:
        cells.append({"icon": "pin", "label": "", "lines": location, "svg": Markup(ICON_SVG["pin"])})
    if urls:
        cells.append(
            {
                "icon": "web",
                "label": labels[0] if labels else "",
                "lines": urls,
                "svg": Markup(ICON_SVG["web"]),
            }
        )
    if phones:
        cells.append(
            {
                "icon": "call",
                "label": labels[1] if len(labels) > 1 else "",
                "lines": phones,
                "svg": Markup(ICON_SVG["call"]),
            }
        )
    # Any label that found no column still has to appear somewhere.
    placed = {value for cell in cells for value in cell["lines"]}
    placed |= {cell["label"] for cell in cells if cell["label"]}
    orphans = [v for v in block.values if v not in placed]
    if orphans and cells:
        cells[0]["lines"] = cells[0]["lines"] + orphans
    elif orphans:
        cells.append({"icon": "pin", "label": "", "lines": orphans, "svg": Markup(ICON_SVG["pin"])})
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

        bar_block = next((b for b in blocks if b.role is BlockRole.INFO_BAR), None)
        banner_block = next((b for b in blocks if b.role is BlockRole.BANNER), None)
        column = [b for b in blocks if b.role not in {BlockRole.INFO_BAR, BlockRole.BANNER}]

        subjects = [
            {
                "url": entry.path().resolve().as_uri(),
                "left": int(width * 0.44),
                "top": int(height * 0.30),
                "width": int(width * 0.54),
            }
            for entry in self.subject_bank.select(limit=1)
        ]

        html_path = destination.with_suffix(".html")

        def context_for(state: FitState, active: list[ContentBlock]) -> dict:
            return {
                "content": content,
                "brand": brand,
                "theme": theme,
                "archetype": archetype,
                "blocks": active,
                "banner_block": banner_block,
                "info_cells": _info_cells(bar_block) if bar_block else [],
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
        finally:
            page.close()

        def norm(value: str) -> str:
            return re.sub(r"\s+", " ", value).strip()

        visible = norm(rendered_text)
        expected = block_values([*result.blocks, *( [bar_block] if bar_block else [] )])
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
            score_total=0.0,
            zone=zone,
        )
