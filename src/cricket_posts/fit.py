"""The two-way fit engine.

The dead zone in the bottom-left of the earlier poster was not a prompting
failure. The plate decided where space was, the content decided how much there
was to say, and nothing reconciled them. This does the reconciling.

It is deterministic: no model, no prompt, no conversation. It measures the
rendered copy column, compares it against the calm rectangle discovered on the
plate, and applies moves in a fixed order until the fill lands in band.

Crucially it moves in **both** directions. The previous system only knew how to
shrink, so short copy left a hole. Growing — larger type, more leading, and
promoting `OPTIONAL` blocks — is what closes it.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable, Protocol

from .blocks import BlockPriority, ContentBlock

#: Proportion of the zone height the copy should occupy. Below the floor the
#: poster looks unfinished; above the ceiling it looks cramped. The floor sat
#: at 0.78, which let the engine stop with a fifth of the column empty and copy
#: smaller than it needed to be — legible on a desktop crop, not in a feed.
FILL_FLOOR = 0.88
FILL_CEILING = 0.97

TYPE_SCALE_MIN = 0.78
#: Raised alongside the floor: reaching a higher fill on a short brief needs
#: headroom the old ceiling did not leave.
TYPE_SCALE_MAX = 1.55
LEADING_MIN = 1.12
LEADING_MAX = 1.52
GAP_MIN = 10
GAP_MAX = 46


@dataclass(frozen=True)
class FitState:
    type_scale: float = 1.0
    leading: float = 1.34
    gap_px: int = 22
    #: Orders of OPTIONAL blocks currently included.
    promoted: frozenset[int] = field(default_factory=frozenset)
    #: Orders of PREFERRED blocks currently excluded.
    dropped: frozenset[int] = field(default_factory=frozenset)
    #: Set when growth was exhausted and the column should sit centred in the
    #: zone rather than hang from the top leaving a gap beneath it.
    centered: bool = False


@dataclass
class Measurement:
    height: float
    overflow: bool


class Measurer(Protocol):
    def __call__(self, state: FitState, blocks: list[ContentBlock]) -> Measurement: ...


@dataclass
class FitResult:
    state: FitState
    blocks: list[ContentBlock]
    fill: float
    iterations: int
    history: list[str]
    fits: bool
    overlong_fields: list[str]


def active_blocks(blocks: list[ContentBlock], state: FitState) -> list[ContentBlock]:
    selected = [
        block
        for block in blocks
        if block.priority is BlockPriority.REQUIRED
        or (block.priority is BlockPriority.PREFERRED and block.order not in state.dropped)
        or (block.priority is BlockPriority.OPTIONAL and block.order in state.promoted)
    ]
    return sorted(selected, key=lambda block: block.order)


def _optional_orders(blocks: list[ContentBlock]) -> list[int]:
    return [b.order for b in blocks if b.priority is BlockPriority.OPTIONAL]


def _preferred_orders(blocks: list[ContentBlock]) -> list[int]:
    """Least important first, so the cheapest thing is dropped soonest."""
    return [b.order for b in blocks if b.priority is BlockPriority.PREFERRED][::-1]


def _grow(state: FitState, blocks: list[ContentBlock]) -> tuple[FitState, str] | None:
    """Moves that consume more space, in the order a designer would try them."""
    for order in _optional_orders(blocks):
        if order not in state.promoted:
            return replace(state, promoted=state.promoted | {order}), f"promote block {order}"
    if state.type_scale < TYPE_SCALE_MAX:
        return replace(
            state, type_scale=round(min(TYPE_SCALE_MAX, state.type_scale + 0.04), 3)
        ), "type scale up"
    if state.leading < LEADING_MAX:
        return replace(state, leading=round(min(LEADING_MAX, state.leading + 0.04), 3)), "leading up"
    if state.gap_px < GAP_MAX:
        return replace(state, gap_px=min(GAP_MAX, state.gap_px + 4)), "gap up"
    return None


def _shrink(state: FitState, blocks: list[ContentBlock]) -> tuple[FitState, str] | None:
    """Moves that free space. Copy is never rewritten, only re-sized or dropped."""
    if state.gap_px > GAP_MIN:
        return replace(state, gap_px=max(GAP_MIN, state.gap_px - 4)), "gap down"
    if state.leading > LEADING_MIN:
        return replace(
            state, leading=round(max(LEADING_MIN, state.leading - 0.04), 3)
        ), "leading down"
    if state.type_scale > TYPE_SCALE_MIN:
        return replace(
            state, type_scale=round(max(TYPE_SCALE_MIN, state.type_scale - 0.04), 3)
        ), "type scale down"
    for order in sorted(state.promoted, reverse=True):
        return replace(state, promoted=state.promoted - {order}), f"demote block {order}"
    for order in _preferred_orders(blocks):
        if order not in state.dropped:
            return replace(state, dropped=state.dropped | {order}), f"drop block {order}"
    return None


def solve(
    blocks: list[ContentBlock],
    zone_height: float,
    measure: Measurer,
    *,
    max_iterations: int = 26,
) -> FitResult:
    state = FitState()
    history: list[str] = []
    measurement = measure(state, active_blocks(blocks, state))
    iterations = 0

    while iterations < max_iterations:
        fill = measurement.height / zone_height if zone_height else 0.0
        too_big = measurement.overflow or fill > FILL_CEILING
        too_small = not too_big and fill < FILL_FLOOR

        if not too_big and not too_small:
            break

        move = _shrink(state, blocks) if too_big else _grow(state, blocks)
        if move is None:
            break

        candidate, label = move
        trial = measure(candidate, active_blocks(blocks, candidate))
        trial_fill = trial.height / zone_height if zone_height else 0.0

        # A growth move that overshoots into overflow is worse than the gap it
        # was trying to close, so roll it back and stop growing.
        if too_small and (trial.overflow or trial_fill > FILL_CEILING):
            history.append(f"{label} (rolled back: would overflow)")
            break

        state, measurement = candidate, trial
        history.append(label)
        iterations += 1

    fill = measurement.height / zone_height if zone_height else 0.0
    final = active_blocks(blocks, state)
    fits = not measurement.overflow and fill <= FILL_CEILING
    overlong = (
        [block.heading or block.role.value for block in final if block.priority is BlockPriority.REQUIRED]
        if not fits
        else []
    )
    return FitResult(
        state=state,
        blocks=final,
        fill=round(fill, 4),
        iterations=iterations,
        history=history,
        fits=fits,
        overlong_fields=overlong,
    )
