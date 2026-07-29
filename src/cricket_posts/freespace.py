"""Discover where copy can actually go on a generated art plate.

The negative-space brief in a prompt is a request, not a contract. An early
attempt at reserving zones produced literal cream cards in arbitrary positions,
and a later one had the model invent a headline inside a region it was asked to
clear. So nothing here trusts the brief: it measures the pixels.

Two signals decide whether a cell can carry text, both computed with PIL alone
so there is no numpy dependency:

* **edge density** — ``FIND_EDGES`` catches texture, subject boundaries and fine
  decorative marks.
* **local range** — a max-filter minus a min-filter catches strong smooth
  gradients that produce few edges but still ruin legibility.

A cell is *calm* when both are low. The largest all-calm rectangles are then the
candidate copy zones, which is what the fit engine sizes content against.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter
from pydantic import BaseModel, ConfigDict, Field

from .models import Rect

CELL_PX = 10
# Calibrated in `docs`/calibration against real plates; see tune_thresholds().
DEFAULT_EDGE_MAX = 14.0
DEFAULT_RANGE_MAX = 26.0
# A zone smaller than this cannot hold a readable block of copy.
MIN_ZONE_W = 240
MIN_ZONE_H = 150


class FreeZone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    box: Rect
    edge_mean: float = 0.0
    range_mean: float = 0.0
    luma_mean: float = 0.0

    @property
    def area(self) -> float:
        return self.box.area


class FreeSpaceMap(BaseModel):
    """Per-cell calmness for one plate, plus the usable rectangles."""

    model_config = ConfigDict(extra="forbid")

    source: str = ""
    width: int
    height: int
    cell_px: int = CELL_PX
    cols: int
    rows: int
    calm: list[bool] = Field(default_factory=list)
    zones: list[FreeZone] = Field(default_factory=list)

    @property
    def calm_fraction(self) -> float:
        return sum(self.calm) / len(self.calm) if self.calm else 0.0

    def largest(self) -> FreeZone | None:
        return self.zones[0] if self.zones else None

    def tallest_within(self, left: float, right: float, top: float = 0.0) -> Rect | None:
        """The deepest run of calm rows spanning every column in ``left..right``.

        ``zones`` ranks rectangles by area, which favours wide-and-short ones.
        That is the right answer to "where is there room at all", but once a
        layout has committed to a column width the useful question changes to
        "how far down does *this* column stay calm" — and on a plate whose
        artwork cuts in diagonally the two answers differ by a lot of poster.
        """
        col0 = max(0, int(left // self.cell_px))
        col1 = min(self.cols - 1, int((right - 1) // self.cell_px))
        row_from = max(0, int(top // self.cell_px))
        if col0 > col1 or not self.calm:
            return None

        best: tuple[int, int] | None = None
        run_start: int | None = None
        for row in range(row_from, self.rows + 1):
            base = row * self.cols
            clear = row < self.rows and all(
                self.calm[base + col] for col in range(col0, col1 + 1)
            )
            if clear:
                run_start = row if run_start is None else run_start
                continue
            if run_start is not None:
                if best is None or (row - run_start) > (best[1] - best[0]):
                    best = (run_start, row)
                run_start = None
        if best is None:
            return None
        return Rect(
            left=col0 * self.cell_px,
            top=best[0] * self.cell_px,
            right=(col1 + 1) * self.cell_px,
            bottom=best[1] * self.cell_px,
        )



def _cell_means(image: Image.Image, cols: int, rows: int) -> list[float]:
    """Mean value per cell, via a BOX downscale (an exact area average)."""
    small = image.resize((cols, rows), Image.Resampling.BOX)
    return [float(value) for value in small.getdata()]


def _measure(
    image: Image.Image,
    cell_px: int,
) -> tuple[int, int, list[float], list[float], list[float]]:
    cols = max(1, image.width // cell_px)
    rows = max(1, image.height // cell_px)
    grey = image.convert("L")

    edges = grey.filter(ImageFilter.FIND_EDGES)
    # A smooth but steep gradient produces almost no edges yet still destroys
    # legibility, so measure local dynamic range as well.
    spread = ImageChops.difference(
        grey.filter(ImageFilter.MaxFilter(5)),
        grey.filter(ImageFilter.MinFilter(5)),
    )
    return (
        cols,
        rows,
        _cell_means(edges, cols, rows),
        _cell_means(spread, cols, rows),
        _cell_means(grey, cols, rows),
    )


def _largest_rectangle(calm: list[bool], cols: int, rows: int) -> tuple[int, int, int, int] | None:
    """Largest all-true axis-aligned rectangle, in cell coordinates.

    Standard largest-rectangle-in-histogram sweep: O(rows x cols).
    Returns ``(col0, row0, col1, row1)`` inclusive, or None.
    """
    heights = [0] * cols
    best_area = 0
    best: tuple[int, int, int, int] | None = None
    for row in range(rows):
        base = row * cols
        for col in range(cols):
            heights[col] = heights[col] + 1 if calm[base + col] else 0
        stack: list[int] = []
        for col in range(cols + 1):
            current = heights[col] if col < cols else 0
            while stack and heights[stack[-1]] > current:
                height = heights[stack.pop()]
                left = stack[-1] + 1 if stack else 0
                area = height * (col - left)
                if area > best_area:
                    best_area = area
                    best = (left, row - height + 1, col - 1, row)
            stack.append(col)
    return best


def analyze(
    source: Path | Image.Image,
    *,
    cell_px: int = CELL_PX,
    edge_max: float = DEFAULT_EDGE_MAX,
    range_max: float = DEFAULT_RANGE_MAX,
    min_zone: tuple[int, int] = (MIN_ZONE_W, MIN_ZONE_H),
    max_zones: int = 4,
) -> FreeSpaceMap:
    if isinstance(source, Image.Image):
        image = source.convert("RGB")
        name = ""
    else:
        with Image.open(source) as handle:
            image = handle.convert("RGB")
        name = str(source)

    cols, rows, edge, spread, luma = _measure(image, cell_px)
    calm = [
        edge[index] <= edge_max and spread[index] <= range_max
        for index in range(cols * rows)
    ]

    zones: list[FreeZone] = []
    working = list(calm)
    min_cols = max(1, min_zone[0] // cell_px)
    min_rows = max(1, min_zone[1] // cell_px)
    for _ in range(max_zones):
        found = _largest_rectangle(working, cols, rows)
        if found is None:
            break
        col0, row0, col1, row1 = found
        if (col1 - col0 + 1) < min_cols or (row1 - row0 + 1) < min_rows:
            break
        cells = [
            row * cols + col
            for row in range(row0, row1 + 1)
            for col in range(col0, col1 + 1)
        ]
        zones.append(
            FreeZone(
                box=Rect(
                    left=col0 * cell_px,
                    top=row0 * cell_px,
                    right=(col1 + 1) * cell_px,
                    bottom=(row1 + 1) * cell_px,
                ),
                edge_mean=round(sum(edge[i] for i in cells) / len(cells), 3),
                range_mean=round(sum(spread[i] for i in cells) / len(cells), 3),
                luma_mean=round(sum(luma[i] for i in cells) / len(cells), 3),
            )
        )
        for index in cells:
            working[index] = False

    return FreeSpaceMap(
        source=name,
        width=image.width,
        height=image.height,
        cell_px=cell_px,
        cols=cols,
        rows=rows,
        calm=calm,
        zones=zones,
    )


def cache_path(plate: Path) -> Path:
    return plate.with_suffix(".freespace.json")


def load_or_analyze(plate: Path, **kwargs) -> FreeSpaceMap:
    """Analysis is deterministic, so cache it beside the plate."""
    cached = cache_path(plate)
    if cached.exists() and cached.stat().st_mtime >= plate.stat().st_mtime:
        return FreeSpaceMap.model_validate_json(cached.read_text(encoding="utf-8"))
    result = analyze(plate, **kwargs)
    cached.write_text(result.model_dump_json(), encoding="utf-8")
    return result


def debug_overlay(plate: Path, result: FreeSpaceMap, destination: Path) -> Path:
    """Tint non-calm cells and outline the zones, for eyeballing calibration."""
    with Image.open(plate) as handle:
        image = handle.convert("RGB")
    mask = Image.new("L", (result.cols, result.rows))
    mask.putdata([0 if flag else 140 for flag in result.calm])
    mask = mask.resize(image.size, Image.Resampling.NEAREST)
    tinted = Image.composite(
        Image.new("RGB", image.size, "#FF2D55"), image, mask
    )
    from PIL import ImageDraw

    painter = ImageDraw.Draw(tinted)
    for index, zone in enumerate(result.zones):
        painter.rectangle(
            (zone.box.left, zone.box.top, zone.box.right - 1, zone.box.bottom - 1),
            outline="#00E5FF",
            width=6,
        )
        painter.text((zone.box.left + 12, zone.box.top + 10), f"#{index + 1}", fill="#00E5FF")
    destination.parent.mkdir(parents=True, exist_ok=True)
    tinted.save(destination)
    return destination
