from __future__ import annotations

from PIL import Image, ImageDraw

from cricket_posts.freespace import analyze


def canvas(color: str = "#F4EFE3", size: tuple[int, int] = (1000, 1000)) -> Image.Image:
    return Image.new("RGB", size, color)


def hatch(image: Image.Image, start: int, end: int) -> Image.Image:
    painter = ImageDraw.Draw(image)
    for x in range(start, end, 7):
        painter.line((x, 0, x - 200, image.height), fill="#20304F", width=3)
    return image


def test_blank_canvas_is_almost_entirely_calm():
    result = analyze(canvas())

    assert result.calm_fraction > 0.9
    assert result.largest() is not None


def test_dense_texture_yields_no_usable_zone():
    result = analyze(hatch(canvas(), 0, 1000))

    assert result.calm_fraction < 0.2
    assert result.zones == []


def test_zone_is_found_on_the_calm_side_only():
    result = analyze(hatch(canvas(), 500, 1000))
    zone = result.largest()

    assert zone is not None
    # The busy half starts around x=300 once the diagonals lean left.
    assert zone.box.right <= 520
    assert zone.box.height > 800


def test_a_gentle_gradient_stays_usable():
    """Locally near-flat, so it holds text fine. The metric should not panic."""
    image = canvas()
    painter = ImageDraw.Draw(image)
    for y in range(image.height):
        shade = int(255 * y / image.height)
        painter.line((0, y, image.width, y), fill=(shade, shade, shade))

    assert analyze(image).calm_fraction > 0.9


def test_steep_repeating_gradient_is_rejected():
    """Local range catches banding that edge detection alone would miss."""
    image = canvas()
    painter = ImageDraw.Draw(image)
    for y in range(image.height):
        shade = int(255 * ((y % 24) / 24))
        painter.line((0, y, image.width, y), fill=(shade, shade, shade))

    result = analyze(image)

    assert result.calm_fraction < 0.2
    assert result.zones == []


def test_a_flat_colour_field_is_usable_however_dark():
    """Legibility on it is the contrast check's job, not this one's."""
    result = analyze(canvas("#101820"))

    assert result.calm_fraction > 0.9
    assert result.largest() is not None


def test_zones_do_not_overlap():
    image = canvas()
    painter = ImageDraw.Draw(image)
    painter.rectangle((450, 0, 550, 1000), fill="#20304F")

    result = analyze(image, max_zones=3)

    for first in range(len(result.zones)):
        for second in range(first + 1, len(result.zones)):
            a = result.zones[first].box
            b = result.zones[second].box
            overlap = (
                min(a.right, b.right) > max(a.left, b.left)
                and min(a.bottom, b.bottom) > max(a.top, b.top)
            )
            assert not overlap


def test_zone_respects_the_minimum_size():
    # Texture everything but a thin stripe narrower than the minimum width. A
    # flat fill would not do: a solid block is calm and legitimately usable.
    image = hatch(canvas(), 320, 1240)

    result = analyze(image, min_zone=(240, 150))

    assert result.zones == []


def test_measurements_are_reported_for_each_zone():
    result = analyze(canvas("#FFFFFF"))
    zone = result.largest()

    assert zone is not None
    assert zone.edge_mean == 0.0
    assert zone.luma_mean > 240


def test_grid_matches_the_declared_cell_size():
    result = analyze(canvas(size=(1080, 1350)), cell_px=10)

    assert (result.cols, result.rows) == (108, 135)
    assert len(result.calm) == 108 * 135


def test_film_grain_does_not_hide_a_usable_zone():
    """Photographic plates carry grain that lights up an edge filter.

    Untreated it speckles a flat field with failing cells until no all-calm
    rectangle survives, and a plate that is half plain navy panel measures as
    having nowhere at all to put copy.
    """
    import random

    from cricket_posts.freespace import analyze

    random.seed(7)
    plate = Image.new("RGB", (400, 400), (12, 38, 94))
    for x in range(400):
        for y in range(400):
            n = random.randint(-14, 14)
            plate.putpixel((x, y), (12 + n, 38 + n, 94 + n))

    result = analyze(plate, min_zone=(150, 150))

    assert result.largest() is not None, "grain swallowed an otherwise flat field"
    assert result.calm_fraction > 0.8


def test_a_cached_map_from_an_older_algorithm_is_recomputed(tmp_path):
    """Caches key on the plate's mtime, so a detector fix would not reach them."""
    import json

    from cricket_posts.freespace import ALGORITHM_VERSION, cache_path, load_or_analyze

    plate = tmp_path / "plate.png"
    Image.new("RGB", (300, 300), "white").save(plate)
    stale = load_or_analyze(plate).model_dump(mode="json")
    stale["version"] = ALGORITHM_VERSION - 1
    stale["zones"] = []
    cache_path(plate).write_text(json.dumps(stale), encoding="utf-8")

    assert load_or_analyze(plate).version == ALGORITHM_VERSION
