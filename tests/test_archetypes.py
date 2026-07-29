from __future__ import annotations

from PIL import Image

from cricket_posts.archetypes import ARCHETYPES, ArchetypeId
from cricket_posts.freespace import analyze
from cricket_posts.models import Rect
from cricket_posts.pipeline import place_subjects
from cricket_posts.subjects import SubjectEntry

LEFT = ARCHETYPES[ArchetypeId.LEFT_COLUMN]
CENTER = ARCHETYPES[ArchetypeId.CENTER_STAGE]


def test_shape_zone_narrows_a_generous_measurement_to_the_layout():
    """The widest calm rectangle is not automatically the right copy column."""
    measured = Rect(left=10, top=10, right=620, bottom=820)

    shaped = LEFT.shape_zone(measured, 1080, 1350)

    assert shaped.width < measured.width
    assert shaped.left >= measured.left and shaped.right <= measured.right


def test_shape_zone_keeps_the_measurement_when_trimming_would_starve_the_copy():
    """A badly-placed layout still beats having nowhere to put the copy."""
    measured = Rect(left=700, top=10, right=1000, bottom=400)

    assert LEFT.shape_zone(measured, 1080, 1350) is measured


def test_subject_slot_never_overlaps_the_copy_zone():
    zone = Rect(left=32, top=40, right=453, bottom=980)

    slot = LEFT.subject_slot(zone, 1080, 1350)

    assert slot is not None
    assert slot.left >= zone.right


def test_centred_announcements_carry_no_subject():
    """Copy owns the middle there, so a figure could only sit on top of it."""
    assert CENTER.subject_slot(Rect(left=0, top=0, right=900, bottom=1000), 1080, 1350) is None


def test_tallest_within_finds_depth_a_widest_rectangle_misses():
    """A narrow column can run far deeper than the largest-area rectangle."""
    plate = Image.new("RGB", (400, 600), "white")
    # Texture over the lower right. The largest-area rectangle is the full-width
    # band above it, which stops at y=250; the narrow left column stays calm all
    # the way to the bottom edge.
    for x in range(150, 400):
        for y in range(250, 600):
            plate.putpixel((x, y), (0, 0, 0) if (x + y) % 2 else (255, 255, 255))

    result = analyze(plate, min_zone=(80, 80))
    widest = result.largest()
    # Measured from inside the frame: every column in the span must be calm, and
    # the outermost cells of any image read as edges.
    deep = result.tallest_within(20, 140)

    assert widest is not None and deep is not None
    assert deep.bottom > widest.box.bottom


def test_tallest_within_reports_nothing_when_the_column_is_never_calm():
    plate = Image.new("RGB", (200, 200))
    plate.putdata([(0, 0, 0) if (i // 3) % 2 else (255, 255, 255) for i in range(200 * 200)])

    assert analyze(plate, min_zone=(40, 40)).tallest_within(0, 200) is None


def test_a_cut_out_stands_on_the_floor_of_its_slot(tmp_path):
    """A figure with clear air under both feet reads as pasted on."""
    cut = tmp_path / "figure.png"
    Image.new("RGBA", (300, 900), (255, 0, 0, 255)).save(cut)
    slot = Rect(left=400, top=100, right=1000, bottom=1200)

    placed = place_subjects([SubjectEntry(file=cut.name)], slot, root=tmp_path)

    assert len(placed) == 1
    # Rounded to whole pixels on the way out, so allow a pixel of slack.
    assert abs(placed[0]["top"] + placed[0]["width"] / (300 / 900) - slot.bottom) <= 2
    assert abs(placed[0]["left"] + placed[0]["width"] - slot.right) <= 2


def test_a_second_figure_shares_the_floor_and_stands_shorter(tmp_path):
    """Same feet line, less height: that is what reads as younger.

    Shrinking a figure without re-seating it just makes it look further away.
    """
    for name in ("hero.png", "child.png"):
        Image.new("RGBA", (300, 900), (255, 0, 0, 255)).save(tmp_path / name)
    slot = Rect(left=400, top=100, right=1000, bottom=1200)

    hero, child = place_subjects(
        [SubjectEntry(file="hero.png"), SubjectEntry(file="child.png")],
        slot,
        root=tmp_path,
    )

    aspect = 300 / 900
    assert child["width"] < hero["width"]
    assert child["top"] > hero["top"]
    for figure in (hero, child):
        assert abs(figure["top"] + figure["width"] / aspect - slot.bottom) <= 2
    # The hero keeps the outer edge; the companion tucks in beside it.
    assert child["left"] < hero["left"]


def test_naming_subjects_keeps_the_order_asked_for(tmp_path):
    """The first name is the hero, so re-sorting would swap the figures."""
    from cricket_posts.subjects import SubjectBank, SubjectSource

    bank = SubjectBank(
        entries=[
            SubjectEntry(file="a.png", source=SubjectSource.PHOTO),
            SubjectEntry(file="b.png", source=SubjectSource.GENERATED),
        ]
    )

    chosen = bank.select(only_files=["b.png", "a.png"], root=tmp_path)

    assert [entry.file for entry in chosen] == ["b.png", "a.png"]


def test_no_slot_means_no_subject(tmp_path):
    Image.new("RGBA", (10, 10)).save(tmp_path / "figure.png")

    assert place_subjects([SubjectEntry(file="figure.png")], None, root=tmp_path) == []
