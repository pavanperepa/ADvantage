from __future__ import annotations

from cricket_posts.layout_score import score_layout
from cricket_posts.models import (
    CompositionMode,
    InkKind,
    InkRect,
    PosterGeometry,
    Rect,
    RegionGeometry,
    TextBackdrop,
    VisualTreatment,
)


def rect(left: float, top: float, right: float, bottom: float) -> Rect:
    return Rect(left=left, top=top, right=right, bottom=bottom)


def card(
    region_id: str,
    left: float,
    top: float,
    right: float,
    bottom: float,
    *,
    ink_area: float | None = None,
) -> RegionGeometry:
    box = rect(left, top, right, bottom)
    return RegionGeometry(
        region_id=region_id,
        parent_id="body.grid",
        depth=2,
        box=box,
        ink_area=box.area * 0.5 if ink_area is None else ink_area,
        text_length=60,
        font_size=30.0,
        is_panel=True,
    )


def backdrop(contrast: float, stdev: float = 0.01) -> TextBackdrop:
    return TextBackdrop(
        region_id="body.card.0",
        contrast_worst=contrast,
        contrast_median=contrast,
        luminance_stdev=stdev,
        sample_count=500,
    )


def geometry(
    *,
    regions: list[RegionGeometry] | None = None,
    ink_rects: list[InkRect] | None = None,
    backdrops: list[TextBackdrop] | None = None,
    font_census: list[tuple[float, float]] | None = None,
    composition: CompositionMode = CompositionMode.BALANCED,
    treatment: VisualTreatment = VisualTreatment.HERO,
    art: Rect | None = None,
) -> PosterGeometry:
    return PosterGeometry(
        width=1080,
        height=1350,
        composition=composition,
        visual_treatment=treatment,
        regions=regions or [],
        ink_rects=ink_rects or [],
        text_backdrops=backdrops if backdrops is not None else [backdrop(12.0)],
        font_census=font_census or [(100.0, 40000.0), (30.0, 90000.0)],
        art=art,
    )


def metric(result, name: str):
    found = result.metric(name)
    assert found is not None, f"missing metric {name}"
    return found


def aligned_grid() -> list[RegionGeometry]:
    return [
        card("body.card.0", 100, 300, 520, 700),
        card("body.card.1", 560, 300, 980, 700),
        card("body.card.2", 100, 740, 520, 1140),
        card("body.card.3", 560, 740, 980, 1140),
    ]


def test_perfectly_aligned_grid_scores_alignment_one():
    result = score_layout(geometry(regions=aligned_grid()))

    assert metric(result, "alignment").score == 1.0


def test_five_pixel_jitter_is_penalised_as_near_miss():
    regions = aligned_grid()
    nudged = regions[2]
    regions[2] = card(
        nudged.region_id,
        nudged.box.left + 5,
        nudged.box.top,
        nudged.box.right + 5,
        nudged.box.bottom,
    )

    result = score_layout(geometry(regions=regions))

    assert metric(result, "alignment").score < 0.6


def test_far_offset_is_not_treated_as_a_near_miss():
    # A deliberate 200px offset is a layout decision, not a sloppy edge.
    regions = aligned_grid()
    nudged = regions[2]
    regions[2] = card(
        nudged.region_id,
        nudged.box.left + 200,
        nudged.box.top,
        nudged.box.right + 200,
        nudged.box.bottom,
    )

    result = score_layout(geometry(regions=regions))

    assert metric(result, "alignment").score == 1.0


def test_sparse_canvas_is_penalised_in_an_information_dense_layout():
    ink = [
        InkRect(left=100, top=100, right=300, bottom=160, kind=InkKind.TEXT),
        InkRect(left=100, top=200, right=320, bottom=260, kind=InkKind.TEXT),
        InkRect(left=100, top=300, right=280, bottom=360, kind=InkKind.TEXT),
    ]
    result = score_layout(
        geometry(ink_rects=ink, composition=CompositionMode.INFORMATION_DENSE)
    )

    whitespace = metric(result, "whitespace")
    assert whitespace.raw > 0.9
    assert whitespace.score < 0.3


def test_single_type_size_scores_flat_hierarchy():
    result = score_layout(geometry(font_census=[(30.0, 90000.0)]))

    hierarchy = metric(result, "hierarchy")
    assert hierarchy.score < 0.5
    assert "one significant type size" in hierarchy.note


def test_barely_separated_type_sizes_score_below_a_clear_ratio():
    flat = score_layout(geometry(font_census=[(32.0, 40000.0), (30.0, 90000.0)]))
    clear = score_layout(geometry(font_census=[(72.0, 40000.0), (30.0, 90000.0)]))

    assert metric(flat, "hierarchy").score < metric(clear, "hierarchy").score
    assert metric(clear, "hierarchy").score == 1.0


def test_crowding_penalises_both_cramped_and_hollow_cards():
    box = rect(100, 300, 520, 700)
    cramped = score_layout(
        geometry(regions=[card("body.card.0", 100, 300, 520, 700,
                               ink_area=box.area * 0.95)])
    )
    hollow = score_layout(
        geometry(regions=[card("body.card.0", 100, 300, 520, 700,
                               ink_area=box.area * 0.05)])
    )
    comfortable = score_layout(
        geometry(regions=[card("body.card.0", 100, 300, 520, 700,
                               ink_area=box.area * 0.5)])
    )

    assert metric(comfortable, "crowding").score == 1.0
    assert metric(cramped, "crowding").score < 0.5
    assert metric(hollow, "crowding").score < 0.5


def test_measured_contrast_drives_its_metric():
    weak = score_layout(geometry(backdrops=[backdrop(1.4)]))
    strong = score_layout(geometry(backdrops=[backdrop(12.0)]))

    assert metric(weak, "text_backdrop_contrast").score == 0.0
    assert metric(strong, "text_backdrop_contrast").score == 1.0


def test_busy_backdrop_is_penalised():
    calm = score_layout(geometry(backdrops=[backdrop(12.0, stdev=0.005)]))
    busy = score_layout(geometry(backdrops=[backdrop(12.0, stdev=0.24)]))

    assert metric(calm, "backdrop_busyness").score > 0.9
    assert metric(busy, "backdrop_busyness").score < 0.1


def test_hero_art_is_a_backdrop_but_a_vignette_occupies_the_canvas():
    ink = [InkRect(left=100, top=100, right=400, bottom=300, kind=InkKind.TEXT)]
    inset = rect(600, 700, 1000, 1100)

    hero = score_layout(
        geometry(ink_rects=ink, treatment=VisualTreatment.HERO, art=rect(0, 0, 1080, 1350))
    )
    vignette = score_layout(
        geometry(ink_rects=ink, treatment=VisualTreatment.VIGNETTE, art=inset)
    )

    # Full-bleed hero artwork must not be counted as occupied canvas, otherwise
    # whitespace would collapse to zero for every art-forward poster.
    assert metric(hero, "whitespace").raw > 0.9
    assert metric(vignette, "whitespace").raw < metric(hero, "whitespace").raw


def test_image_dominance_target_follows_the_visual_treatment():
    ink = [InkRect(left=0, top=0, right=1080, bottom=200, kind=InkKind.PANEL)]
    full_bleed = rect(0, 0, 1080, 1350)

    hero = score_layout(
        geometry(ink_rects=ink, treatment=VisualTreatment.HERO, art=full_bleed)
    )
    vignette = score_layout(
        geometry(ink_rects=ink, treatment=VisualTreatment.VIGNETTE, art=full_bleed)
    )

    # The same measurement is right for a hero and far too dominant for a vignette.
    assert metric(hero, "image_dominance").score > metric(vignette, "image_dominance").score


def test_uneven_sibling_gaps_score_below_even_ones():
    even = [
        card("body.card.0", 100, 100, 900, 300),
        card("body.card.1", 100, 340, 900, 540),
        card("body.card.2", 100, 580, 900, 780),
    ]
    uneven = [
        card("body.card.0", 100, 100, 900, 300),
        card("body.card.1", 100, 310, 900, 510),
        card("body.card.2", 100, 900, 900, 1100),
    ]

    assert (
        metric(score_layout(geometry(regions=even)), "spacing_consistency").score
        > metric(score_layout(geometry(regions=uneven)), "spacing_consistency").score
    )


def test_a_good_layout_clearly_outranks_a_bad_one():
    good = score_layout(
        geometry(
            regions=aligned_grid(),
            ink_rects=[
                InkRect(left=100, top=120, right=900, bottom=240, kind=InkKind.TEXT),
                InkRect(left=100, top=300, right=520, bottom=700, kind=InkKind.PANEL),
                InkRect(left=560, top=300, right=980, bottom=700, kind=InkKind.PANEL),
                InkRect(left=100, top=740, right=520, bottom=1140, kind=InkKind.PANEL),
                InkRect(left=560, top=740, right=980, bottom=1140, kind=InkKind.PANEL),
            ],
            backdrops=[backdrop(11.0, stdev=0.01)],
            font_census=[(96.0, 40000.0), (30.0, 120000.0)],
        )
    )
    bad = score_layout(
        geometry(
            regions=[
                card("body.card.0", 40, 40, 300, 200, ink_area=260 * 160 * 0.97),
                card("body.card.1", 45, 210, 302, 380, ink_area=257 * 170 * 0.96),
                card("body.card.2", 38, 900, 297, 1010, ink_area=259 * 110 * 0.98),
            ],
            ink_rects=[
                InkRect(left=40, top=40, right=300, bottom=200, kind=InkKind.PANEL),
                InkRect(left=45, top=210, right=302, bottom=380, kind=InkKind.PANEL),
                InkRect(left=38, top=900, right=297, bottom=1010, kind=InkKind.PANEL),
            ],
            backdrops=[backdrop(1.6, stdev=0.22)],
            font_census=[(31.0, 40000.0), (30.0, 90000.0)],
        )
    )

    assert good.total > bad.total + 0.25


def test_weights_follow_the_composition_and_sum_over_present_metrics():
    result = score_layout(geometry(composition=CompositionMode.INFORMATION_DENSE))

    assert result.weights_profile == "information_dense"
    assert 0.0 <= result.total <= 1.0
    # alignment carries the most weight in dense layouts
    assert metric(result, "alignment").weight == 0.17
