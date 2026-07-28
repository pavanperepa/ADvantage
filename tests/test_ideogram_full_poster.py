from __future__ import annotations

from PIL import Image

from cricket_posts.ideogram import (
    _normalize_full_poster,
    full_poster_json_prompt,
    full_poster_prompt,
)
from cricket_posts.layout import poster_copy_lines
from cricket_posts.models import BrandProfile


def test_full_poster_prompt_preserves_light_copy(load_content):
    content = load_content("information.json")
    prompt = full_poster_prompt(content, BrandProfile(name="22 Yards Houston"))

    assert '"SUMMER HOURS"' in prompt
    assert '"EFFECTIVE JULY 01"' in prompt
    assert '"boundarycricket.com · (469) 555-0188"' in prompt
    assert "Do not fix spelling" in prompt


def test_full_poster_json_prompt_keeps_every_copy_line_verbatim(load_content):
    content = load_content("information.json")
    brand = BrandProfile(name="22 Yards Houston")
    prompt = full_poster_json_prompt(content, brand)
    elements = prompt["compositional_deconstruction"]["elements"]
    rendered_lines = [
        element["text"] for element in elements if element["type"] == "text"
    ]

    assert rendered_lines == poster_copy_lines(content, brand)


def test_full_poster_is_normalized_to_1080x1350_without_cropping(tmp_path):
    source = tmp_path / "source.png"
    destination = tmp_path / "poster.png"
    Image.new("RGB", (1728, 2304), "#234567").save(source)

    _normalize_full_poster(source, destination, background_color="#071426")

    with Image.open(destination) as image:
        assert image.size == (1080, 1350)
