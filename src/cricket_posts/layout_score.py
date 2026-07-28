"""Deterministic aesthetic scoring for a rendered poster.

Everything here is a pure function of measured geometry: no browser, no file
system, no network. That is deliberate — the scoring rules are the part most
likely to need tuning, and they should be testable from synthetic geometry
without rendering anything.

The audit in ``studio_renderer`` answers "is this poster valid?". This module
answers the separate question "is this poster any good?", and never contributes
to ``ValidationReport.valid``.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict

from .models import (
    CompositionMode,
    InkKind,
    LayoutScore,
    MetricScore,
    PosterGeometry,
    Rect,
    VisualTreatment,
)


CELL_PX = 10

# Fraction of the canvas that should be left empty, per composition mode.
WHITESPACE_BANDS: dict[CompositionMode, tuple[float, float]] = {
    CompositionMode.ART_FORWARD: (0.42, 0.62),
    CompositionMode.BALANCED: (0.30, 0.48),
    CompositionMode.INFORMATION_DENSE: (0.15, 0.32),
}

# How much of the canvas the artwork should still be visible across. This tracks
# the visual treatment rather than the composition: a hero treatment is a
# full-bleed photograph with panels laid over it and is meant to stay dominant,
# whereas a vignette is a small inset image and should not be.
IMAGE_TARGETS: dict[VisualTreatment, float] = {
    VisualTreatment.HERO: 0.60,
    VisualTreatment.VIGNETTE: 0.22,
}

# Visual mass carried by each kind of ink when locating the centre of gravity.
INK_WEIGHTS: dict[InkKind, float] = {
    InkKind.TEXT: 1.0,
    InkKind.PANEL: 0.35,
    InkKind.IMAGE: 0.8,
}

# Asymmetry is deliberate in art-forward layouts, where the copy sits on one side
# and the photographic subject counterweights it on the other. Only ink is
# measured here, so those layouts must be allowed a larger centre-of-mass offset
# before it counts as imbalance.
BALANCE_TOLERANCE: dict[CompositionMode, float] = {
    CompositionMode.ART_FORWARD: 0.55,
    CompositionMode.BALANCED: 0.42,
    CompositionMode.INFORMATION_DENSE: 0.32,
}

# Edges this far apart read as a mistake rather than a deliberate offset.
NEAR_MISS_MIN = 2.0
NEAR_MISS_MAX = 8.0

# A card should be neither cramped nor hollow.
CROWDING_BAND = (0.35, 0.70)
# Largest-to-second-largest type size.
HIERARCHY_BAND = (1.5, 3.0)

WEIGHT_PROFILES: dict[CompositionMode, dict[str, float]] = {
    CompositionMode.ART_FORWARD: {
        "whitespace": 0.12,
        "balance": 0.14,
        "alignment": 0.14,
        "spacing_consistency": 0.10,
        "crowding": 0.10,
        "hierarchy": 0.14,
        "image_dominance": 0.10,
        "text_backdrop_contrast": 0.10,
        "backdrop_busyness": 0.06,
    },
    CompositionMode.BALANCED: {
        "whitespace": 0.12,
        "balance": 0.13,
        "alignment": 0.15,
        "spacing_consistency": 0.11,
        "crowding": 0.12,
        "hierarchy": 0.12,
        "image_dominance": 0.08,
        "text_backdrop_contrast": 0.11,
        "backdrop_busyness": 0.06,
    },
    CompositionMode.INFORMATION_DENSE: {
        "whitespace": 0.10,
        "balance": 0.12,
        "alignment": 0.17,
        "spacing_consistency": 0.13,
        "crowding": 0.14,
        "hierarchy": 0.10,
        "image_dominance": 0.05,
        "text_backdrop_contrast": 0.13,
        "backdrop_busyness": 0.06,
    },
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _band_score(value: float, low: float, high: float, falloff: float) -> float:
    """1.0 inside the band, decaying linearly to 0 once ``falloff`` outside it."""
    if low <= value <= high:
        return 1.0
    distance = low - value if value < low else value - high
    return _clamp(1.0 - distance / falloff)


def _grid_size(geometry: PosterGeometry) -> tuple[int, int]:
    return (
        max(1, geometry.width // CELL_PX),
        max(1, geometry.height // CELL_PX),
    )


def _mark(grid: bytearray, cols: int, rows: int, rect: Rect) -> None:
    if rect.width <= 0 or rect.height <= 0:
        return
    first_col = max(0, int(rect.left // CELL_PX))
    first_row = max(0, int(rect.top // CELL_PX))
    last_col = min(cols - 1, int((rect.right - 0.001) // CELL_PX))
    last_row = min(rows - 1, int((rect.bottom - 0.001) // CELL_PX))
    for row in range(first_row, last_row + 1):
        base = row * cols
        for col in range(first_col, last_col + 1):
            grid[base + col] = 1


def _raster(geometry: PosterGeometry, rects: list[Rect]) -> tuple[bytearray, int, int]:
    cols, rows = _grid_size(geometry)
    grid = bytearray(cols * rows)
    for rect in rects:
        _mark(grid, cols, rows, rect)
    return grid, cols, rows


def _bounded_art(geometry: PosterGeometry) -> Rect | None:
    """The artwork when it behaves as a placed element rather than a backdrop.

    A vignette is an inset image with edges, so it occupies canvas and carries
    visual mass. Hero artwork is full-bleed: treating it as an element would make
    whitespace zero and every centre of mass dead centre, hiding real problems.
    """
    if geometry.visual_treatment is VisualTreatment.VIGNETTE:
        return geometry.art
    return None


def _whitespace(geometry: PosterGeometry) -> MetricScore:
    occupied: list[Rect] = list(geometry.ink_rects)
    bounded = _bounded_art(geometry)
    if bounded is not None:
        occupied.append(bounded)
    grid, cols, rows = _raster(geometry, occupied)
    total = cols * rows
    ratio = 1.0 - (sum(grid) / total if total else 0.0)
    low, high = WHITESPACE_BANDS[geometry.composition]
    return MetricScore(
        name="whitespace",
        raw=round(ratio, 4),
        score=_band_score(ratio, low, high, 0.22),
        note=f"target {low:.2f}-{high:.2f} for {geometry.composition.value}",
    )


def _balance(geometry: PosterGeometry) -> MetricScore:
    masses: list[tuple[Rect, float]] = [
        (rect, INK_WEIGHTS.get(rect.kind, 1.0)) for rect in geometry.ink_rects
    ]
    bounded = _bounded_art(geometry)
    if bounded is not None:
        masses.append((bounded, INK_WEIGHTS[InkKind.IMAGE]))

    total_mass = 0.0
    moment_x = 0.0
    moment_y = 0.0
    for rect, weight in masses:
        mass = rect.area * weight
        if mass <= 0:
            continue
        total_mass += mass
        moment_x += mass * (rect.left + rect.right) / 2
        moment_y += mass * (rect.top + rect.bottom) / 2
    if total_mass <= 0:
        return MetricScore(name="balance", raw=0.0, score=0.0, note="no ink")
    offset_x = (moment_x / total_mass - geometry.width / 2) / (geometry.width / 2)
    offset_y = (moment_y / total_mass - geometry.height / 2) / (geometry.height / 2)
    offset = math.hypot(offset_x, offset_y)
    tolerance = BALANCE_TOLERANCE[geometry.composition]
    return MetricScore(
        name="balance",
        raw=round(offset, 4),
        score=_clamp(1.0 - offset / tolerance),
        note=(
            f"centre of mass offset dx={offset_x:+.3f} dy={offset_y:+.3f}, "
            f"tolerance {tolerance:.2f}"
        ),
    )


def _alignment_rects(geometry: PosterGeometry) -> list[Rect]:
    rects: list[Rect] = [
        region.box
        for region in geometry.regions
        if not region.is_art and region.region_id != "frame" and region.box.area > 0
    ]
    rects.extend(
        rect for rect in geometry.ink_rects if rect.kind is InkKind.PANEL
    )
    return rects


def _alignment(geometry: PosterGeometry) -> MetricScore:
    rects = _alignment_rects(geometry)
    if len(rects) < 2:
        return MetricScore(name="alignment", raw=0.0, score=1.0, note="too few edges")
    near_miss = 0
    total = 0
    for values in (
        [rect.left for rect in rects],
        [rect.right for rect in rects],
        [rect.top for rect in rects],
        [rect.bottom for rect in rects],
    ):
        for index, value in enumerate(values):
            total += 1
            for other_index, other in enumerate(values):
                if index == other_index:
                    continue
                delta = abs(value - other)
                if NEAR_MISS_MIN <= delta <= NEAR_MISS_MAX:
                    near_miss += 1
                    break
    ratio = near_miss / total if total else 0.0
    return MetricScore(
        name="alignment",
        raw=round(ratio, 4),
        score=_clamp(1.0 - ratio / 0.5),
        note=f"{near_miss}/{total} edges land 2-8px from another edge",
    )


def _spacing_consistency(geometry: PosterGeometry) -> MetricScore:
    families: dict[str, list[Rect]] = defaultdict(list)
    for region in geometry.regions:
        if region.is_art or not region.parent_id:
            continue
        families[region.parent_id].append(region.box)
    variations: list[float] = []
    weights: list[float] = []
    for boxes in families.values():
        if len(boxes) < 3:
            continue
        spread_x = max(box.left for box in boxes) - min(box.left for box in boxes)
        spread_y = max(box.top for box in boxes) - min(box.top for box in boxes)
        if spread_y >= spread_x:
            ordered = sorted(boxes, key=lambda box: box.top)
            gaps = [
                ordered[index + 1].top - ordered[index].bottom
                for index in range(len(ordered) - 1)
            ]
        else:
            ordered = sorted(boxes, key=lambda box: box.left)
            gaps = [
                ordered[index + 1].left - ordered[index].right
                for index in range(len(ordered) - 1)
            ]
        gaps = [gap for gap in gaps if gap >= 0]
        if len(gaps) < 2:
            continue
        mean = statistics.fmean(gaps)
        if mean <= 0.5:
            continue
        variations.append(statistics.pstdev(gaps) / mean)
        weights.append(float(len(gaps)))
    if not variations:
        return MetricScore(
            name="spacing_consistency",
            raw=0.0,
            score=1.0,
            note="no repeated sibling groups",
        )
    variation = sum(v * w for v, w in zip(variations, weights)) / sum(weights)
    return MetricScore(
        name="spacing_consistency",
        raw=round(variation, 4),
        score=_clamp(1.0 - variation),
        note=f"gap coefficient of variation across {len(variations)} group(s)",
    )


def _crowding(geometry: PosterGeometry) -> MetricScore:
    cards = [
        region
        for region in geometry.regions
        if region.is_panel and region.box.area > 0 and region.text_length > 0
    ]
    if not cards:
        return MetricScore(name="crowding", raw=0.0, score=1.0, note="no cards")
    low, high = CROWDING_BAND
    fills = [_clamp(card.fill_ratio, 0.0, 2.0) for card in cards]
    scores = [_band_score(fill, low, high, 0.30) for fill in fills]
    return MetricScore(
        name="crowding",
        raw=round(statistics.fmean(fills), 4),
        score=statistics.fmean(scores),
        note=f"mean ink fill across {len(cards)} card(s), target {low:.2f}-{high:.2f}",
    )


def _hierarchy(geometry: PosterGeometry) -> MetricScore:
    census = [(size, area) for size, area in geometry.font_census if area > 0]
    if not census:
        return MetricScore(name="hierarchy", raw=0.0, score=0.0, note="no type")
    total_ink = sum(area for _, area in census)
    significant = sorted(
        {size for size, area in census if area >= total_ink * 0.01},
        reverse=True,
    )
    if len(significant) < 2:
        return MetricScore(
            name="hierarchy",
            raw=1.0,
            score=0.3,
            note="only one significant type size",
        )
    ratio = significant[0] / significant[1]
    low, high = HIERARCHY_BAND
    return MetricScore(
        name="hierarchy",
        raw=round(ratio, 4),
        score=_band_score(ratio, low, high, 1.5),
        note=f"{significant[0]:.0f}px over {significant[1]:.0f}px",
    )


def _image_dominance(geometry: PosterGeometry) -> MetricScore | None:
    if geometry.art is None or geometry.art.area <= 0:
        return None
    panels = [rect for rect in geometry.ink_rects if rect.kind is not InkKind.TEXT]
    grid, cols, rows = _raster(geometry, list(panels))
    art = geometry.art
    first_col = max(0, int(art.left // CELL_PX))
    first_row = max(0, int(art.top // CELL_PX))
    last_col = min(cols - 1, int((art.right - 0.001) // CELL_PX))
    last_row = min(rows - 1, int((art.bottom - 0.001) // CELL_PX))
    visible = 0
    for row in range(first_row, last_row + 1):
        base = row * cols
        for col in range(first_col, last_col + 1):
            if not grid[base + col]:
                visible += 1
    fraction = visible / (cols * rows) if cols * rows else 0.0
    target = IMAGE_TARGETS[geometry.visual_treatment]
    return MetricScore(
        name="image_dominance",
        raw=round(fraction, 4),
        score=_band_score(fraction, target - 0.15, target + 0.15, 0.25),
        note=(
            f"artwork visible across {fraction:.2f} of canvas, target ~{target:.2f} "
            f"for {geometry.visual_treatment.value}"
        ),
    )


def _text_backdrop_contrast(geometry: PosterGeometry) -> MetricScore | None:
    if not geometry.text_backdrops:
        return None
    worst = min(item.contrast_worst for item in geometry.text_backdrops)
    return MetricScore(
        name="text_backdrop_contrast",
        raw=round(worst, 3),
        score=_clamp((worst - 3.0) / 4.0),
        note=f"worst measured ratio {worst:.2f}:1",
    )


def _backdrop_busyness(geometry: PosterGeometry) -> MetricScore | None:
    if not geometry.text_backdrops:
        return None
    busiest = max(item.luminance_stdev for item in geometry.text_backdrops)
    return MetricScore(
        name="backdrop_busyness",
        raw=round(busiest, 4),
        score=_clamp(1.0 - busiest / 0.25),
        note=f"busiest backdrop luminance spread {busiest:.3f}",
    )


def score_layout(geometry: PosterGeometry) -> LayoutScore:
    weights = WEIGHT_PROFILES[geometry.composition]
    candidates = [
        _whitespace(geometry),
        _balance(geometry),
        _alignment(geometry),
        _spacing_consistency(geometry),
        _crowding(geometry),
        _hierarchy(geometry),
        _image_dominance(geometry),
        _text_backdrop_contrast(geometry),
        _backdrop_busyness(geometry),
    ]
    metrics = [metric for metric in candidates if metric is not None]
    for metric in metrics:
        metric.weight = weights.get(metric.name, 0.0)
    total_weight = sum(metric.weight for metric in metrics)
    total = (
        sum(metric.score * metric.weight for metric in metrics) / total_weight
        if total_weight > 0
        else 0.0
    )
    return LayoutScore(
        total=round(_clamp(total), 4),
        weights_profile=geometry.composition.value,
        metrics=metrics,
    )
