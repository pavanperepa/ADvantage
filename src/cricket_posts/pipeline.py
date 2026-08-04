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

from .freespace import FreeSpaceMap, _largest_rectangle
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
    ContentType,
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
from .tracking import qr_code, tracked_url

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
_AMOUNT = re.compile(r"[$£€]\s?\d[\d,]*(?:\.\d{1,2})?")


def split_price(value: str) -> tuple[str, str] | None:
    """Split a price line into the words before the figure, and the figure.

    Only ever a split, never a rewrite: the two halves are contiguous slices of
    the source in their original order, so the rendered text still reads back as
    the line that was written. Returns None when there is no currency figure,
    and the caller falls back to the plain chip.
    """
    found = _AMOUNT.search(value)
    if not found:
        return None
    label = value[: found.start()].strip()
    amount = value[found.start() :].strip()
    return (label, amount) if amount else None


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

        if index == 0 and entry.scale is None:
            width = min(slot.width, slot.height * aspect)
            hero_height = width / aspect
        else:
            reference = hero_height or slot.height
            factor = entry.scale if entry.scale is not None else companion_scale**index
            height = min(reference * factor, slot.height)
            width = height * aspect
            hero_height = hero_height or height

        height = width / aspect
        if entry.at_x is not None:
            left = slot.left + slot.width * entry.at_x - width / 2
        elif index == 0:
            left = slot.right - width
        else:
            left = slot.left

        placed.append(
            {
                "url": path.resolve().as_uri(),
                "left": int(left),
                "top": int(slot.bottom - entry.lift * slot.height - height),
                "width": int(width),
            }
        )
    return placed


def brand_logo(brand: BrandProfile) -> Path | None:
    """The brand's own mark, resolved and existence-checked.

    A poster carrying the wrong academy's crest is worse than one carrying
    none, so a path that no longer resolves returns nothing rather than
    breaking the render — and the brand's logo is the default precisely so
    that producing a correctly-branded poster does not depend on remembering
    a flag.
    """
    if not brand.logo_path:
        return None
    path = Path(brand.logo_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path if path.exists() else None


@dataclass
class DeadSpace:
    """The largest region of canvas that is neither copy nor interesting art."""

    box: Rect | None
    fraction: float

    @property
    def ok(self) -> bool:
        return self.fraction < DEAD_SPACE_LIMIT


#: Share of the canvas one contiguous dead region may occupy before the poster
#: reads as unfinished. Judged by eye against the foundation poster, whose
#: bottom-left hole ran to roughly a sixth of the canvas.
DEAD_SPACE_LIMIT = 0.11


def dead_space(freespace: FreeSpaceMap, occupied: list[Rect]) -> DeadSpace:
    """Find the biggest hole in a finished poster.

    The fit engine measures fill *inside the copy zone*, which is blind to the
    thing it was built to prevent: the foundation poster reported 80% fill and
    "fits" while a third of the canvas sat empty, because the hole was outside
    the zone entirely. This asks the whole-canvas question instead.

    A cell is dead when the plate there is calm *and* nothing was drawn on it.
    Both halves matter — calm artwork with copy on it is a working column, and
    busy artwork with no copy is the photograph. Only their intersection is a
    hole.
    """
    cells = list(freespace.calm)
    cell_px = freespace.cell_px
    for box in occupied:
        for row in range(
            max(0, int(box.top // cell_px)),
            min(freespace.rows, int(box.bottom // cell_px) + 1),
        ):
            base = row * freespace.cols
            for col in range(
                max(0, int(box.left // cell_px)),
                min(freespace.cols, int(box.right // cell_px) + 1),
            ):
                cells[base + col] = False

    found = _largest_rectangle(cells, freespace.cols, freespace.rows)
    if found is None:
        return DeadSpace(box=None, fraction=0.0)
    col0, row0, col1, row1 = found
    box = Rect(
        left=col0 * cell_px,
        top=row0 * cell_px,
        right=(col1 + 1) * cell_px,
        bottom=(row1 + 1) * cell_px,
    )
    canvas = float(freespace.width * freespace.height)
    return DeadSpace(box=box, fraction=box.area / canvas if canvas else 0.0)


#: How much each axis contributes to two variants looking different. A change
#: of plate rebuilds the whole picture; a change of bullet treatment restyles
#: one block. Weighting them equally produces six posters that differ only in
#: details a viewer never notices.
AXIS_WEIGHTS = {"plate_file": 3.0, "intent": 2.0, "color_mode": 1.5, "bullets": 1.0}


@dataclass(frozen=True)
class VariantSpec:
    """One point in the space of posters this content could become."""

    plate_file: str
    intent: StyleIntent
    color_mode: ColorMode
    bullets: str

    def distance(self, other: "VariantSpec") -> float:
        return sum(
            weight
            for axis, weight in AXIS_WEIGHTS.items()
            if getattr(self, axis) != getattr(other, axis)
        )


def variant_specs(
    bank: PlateBank,
    *,
    count: int = 6,
    intents: list[StyleIntent] | None = None,
    bullets: list[str] | None = None,
    modes: list[ColorMode] | None = None,
    content_type: ContentType | None = None,
) -> list[VariantSpec]:
    """Pick `count` specs that are as unlike each other as possible.

    Rendering the whole product would be hundreds of posters to throw away, so
    the choosing happens on the descriptors and only the survivors get drawn.

    Greedy farthest-point selection: take an obvious first, then repeatedly add
    whichever candidate is furthest from everything chosen so far. Taking the
    first N of a shuffled list instead gives six posters that by chance share a
    plate, which is exactly the sameness this exists to avoid. Deterministic,
    so the same content and bank always offer the same set.
    """
    plates = [
        entry.file
        for entry in bank.candidates(content_type=content_type)
        if entry.path().exists()
    ]
    if not plates:
        return []

    candidates = [
        VariantSpec(plate_file=plate, intent=intent, color_mode=mode, bullets=style)
        for plate in plates
        for intent in (intents or list(StyleIntent))
        for mode in (modes or [ColorMode.DARK, ColorMode.LIGHT])
        for style in (bullets or ["auto", "rules", "feature"])
    ]

    chosen = [candidates[0]]
    remaining = candidates[1:]
    while remaining and len(chosen) < count:
        furthest = max(
            remaining, key=lambda spec: min(spec.distance(taken) for taken in chosen)
        )
        remaining.remove(furthest)
        chosen.append(furthest)
    return chosen


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
    #: Largest region of canvas that is neither copy nor interesting artwork.
    dead: DeadSpace
    #: The tagged destination encoded in the QR — also what to put in the
    #: caption, since the poster itself shows the short human-typeable link.
    scan_url: str
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
        self.environment.globals["price_parts"] = split_price

    def compose_variants(
        self,
        content: PosterContent,
        brand: BrandProfile,
        destination_dir: Path,
        *,
        count: int = 6,
        logo_path: Path | None = None,
    ) -> list[tuple[VariantSpec, ComposeResult]]:
        """Render several meaningfully different posters from one content file.

        The point of showing options is that choosing between rendered posters
        takes a person five seconds, whereas describing the trade-offs takes
        paragraphs — and it removes the need to know which plate to name, which
        is the thing currently standing between this engine and anyone using it
        without help.
        """
        results: list[tuple[VariantSpec, ComposeResult]] = []
        specs = variant_specs(
            self.plate_bank, count=count, content_type=content.content_type
        )
        for index, spec in enumerate(specs, 1):
            destination = destination_dir / f"variant-{index:02d}.png"
            try:
                results.append(
                    (
                        spec,
                        self.compose(
                            content,
                            brand,
                            destination,
                            intent=spec.intent,
                            color_mode=spec.color_mode,
                            logo_path=logo_path,
                            plate_file=spec.plate_file,
                            bullets_variant=spec.bullets,
                        ),
                    )
                )
            except Exception as exc:  # one bad plate must not lose the batch
                print(f"  variant {index} failed on {spec.plate_file}: {exc}")
        return results

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
        bullets_variant: str = "auto",
        campaign: str | None = None,
        source: str | None = None,
    ) -> ComposeResult:
        blocks = derive_blocks(content, brand)
        logo_path = logo_path or brand_logo(brand)
        scan_url = tracked_url(
            brand.registration_url or "", campaign=campaign, source=source
        )
        qr = qr_code(scan_url)

        plate = select_plate(
            self.plate_bank,
            archetype_id or ArchetypeId.LEFT_COLUMN,
            intent,
            only_file=plate_file,
            content_type=content.content_type,
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

        # A scene plate brought its own cast; adding a cut-out on top of it puts
        # two batters in one lane.
        subjects = (
            []
            if plate.entry.has_subjects
            else place_subjects(
                self.subject_bank.select(
                    tags=[intent.value], limit=1, only_files=subject_files
                ),
                archetype.subject_slot(zone, width, height),
            )
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
                "bullets_variant": bullets_variant,
                "qr_uri": qr.data_uri if qr else None,
                # Absolute pixels, deliberately outside the --s design scale:
                # whether a code scans is a property of real pixels, not of how
                # large the artboard happens to be.
                "qr_px": qr.rendered_px() if qr else 0,
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
            drawn = page.evaluate(
                """
                () => {
                  const frame = document.querySelector('.canvas').getBoundingClientRect();
                  const boxes = [];
                  document.querySelectorAll(
                    '[data-block], .canvas__bottom, .canvas__subject'
                  ).forEach(el => {
                    const b = el.getBoundingClientRect();
                    if (b.width > 0 && b.height > 0) {
                      boxes.push({
                        left: b.left - frame.left, top: b.top - frame.top,
                        right: b.right - frame.left, bottom: b.bottom - frame.top,
                      });
                    }
                  });
                  return boxes;
                }
                """
            )
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
            dead=dead_space(
                plate.freespace, [Rect(**box) for box in drawn]
            ),
            scan_url=scan_url,
            score_total=0.0,
            zone=zone,
        )
