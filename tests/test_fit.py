from __future__ import annotations

from cricket_posts.blocks import BlockPriority, BlockRole, ContentBlock
from cricket_posts.fit import (
    FILL_CEILING,
    FILL_FLOOR,
    FitState,
    Measurement,
    active_blocks,
    solve,
)


def block(order: int, priority: BlockPriority, weight: float = 100.0) -> ContentBlock:
    return ContentBlock(
        role=BlockRole.PARAGRAPH,
        priority=priority,
        values=["x" * int(weight)],
        order=order,
    )


def fake_measurer(base: float, *, per_block: float = 100.0):
    """Height grows with type scale, leading, gaps and how many blocks are in."""

    def measure(state: FitState, blocks) -> Measurement:
        height = (
            base
            * state.type_scale
            * state.leading
            + len(blocks) * per_block * state.type_scale
            + max(0, len(blocks) - 1) * state.gap_px
        )
        return Measurement(height=height, overflow=height > 2000)

    return measure


def test_short_copy_grows_to_fill_the_zone():
    """The bottom-left gap: content ran out before the space did."""
    blocks = [
        block(0, BlockPriority.REQUIRED),
        block(1, BlockPriority.OPTIONAL),
        block(2, BlockPriority.OPTIONAL),
    ]

    result = solve(blocks, zone_height=1200.0, measure=fake_measurer(300.0))

    assert result.fill >= FILL_FLOOR
    assert result.fits
    assert any("promote" in step for step in result.history)


def test_growth_promotes_optional_blocks_before_inflating_type():
    blocks = [block(0, BlockPriority.REQUIRED), block(1, BlockPriority.OPTIONAL)]

    result = solve(blocks, zone_height=1000.0, measure=fake_measurer(300.0))

    assert result.history[0].startswith("promote")


def test_long_copy_shrinks_rather_than_overflowing():
    blocks = [block(index, BlockPriority.PREFERRED) for index in range(6)]
    blocks.insert(0, block(99, BlockPriority.REQUIRED))

    # 1500px is reachable by shrinking; a smaller zone would be genuinely
    # impossible and is covered by the overlong test below.
    result = solve(blocks, zone_height=1500.0, measure=fake_measurer(900.0))

    assert result.fits
    assert result.fill <= FILL_CEILING
    assert any(
        step.startswith(("gap down", "leading down", "type scale down", "drop"))
        for step in result.history
    )


def test_required_blocks_are_never_dropped():
    blocks = [block(index, BlockPriority.REQUIRED) for index in range(5)]

    result = solve(blocks, zone_height=120.0, measure=fake_measurer(1500.0))

    kept = {b.order for b in result.blocks}
    assert kept == {0, 1, 2, 3, 4}


def test_impossible_copy_is_reported_rather_than_silently_clipped():
    blocks = [block(index, BlockPriority.REQUIRED, weight=400) for index in range(8)]

    result = solve(blocks, zone_height=100.0, measure=fake_measurer(4000.0))

    assert not result.fits
    assert result.overlong_fields


def test_growth_rolls_back_when_it_would_overflow():
    """Better a small gap than clipped copy."""
    blocks = [block(0, BlockPriority.REQUIRED), block(1, BlockPriority.OPTIONAL, 900)]

    def measure(state: FitState, active) -> Measurement:
        height = 700.0 if len(active) == 1 else 1900.0
        return Measurement(height=height, overflow=height > 1000)

    result = solve(blocks, zone_height=1000.0, measure=measure)

    assert result.fits
    assert len(result.blocks) == 1
    assert any("rolled back" in step for step in result.history)


def test_a_layout_already_in_band_is_left_alone():
    blocks = [block(0, BlockPriority.REQUIRED)]

    def measure(state: FitState, active) -> Measurement:
        return Measurement(height=880.0, overflow=False)

    result = solve(blocks, zone_height=1000.0, measure=measure)

    assert result.iterations == 0
    assert result.history == []
    assert result.state == FitState()


def test_active_blocks_respects_priority_selection():
    blocks = [
        block(0, BlockPriority.REQUIRED),
        block(1, BlockPriority.PREFERRED),
        block(2, BlockPriority.OPTIONAL),
    ]
    state = FitState(promoted=frozenset({2}), dropped=frozenset({1}))

    assert [b.order for b in active_blocks(blocks, state)] == [0, 2]
