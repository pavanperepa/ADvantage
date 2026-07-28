"""Region repair through Ideogram's inpainting endpoint.

Only ``ideogram-v3`` exposes an edit route; ``ideogram-v4`` has generate but no
edit, so repairs run on v3 regardless of which model produced the original.

The endpoint requires a strictly black-and-white mask the same size as the
image. Two uses matter here:

``repair_text``
    Ask the model to re-render a botched region with the correct string. Still
    non-deterministic, so the result must be proofread.

``clear_region``
    Ask the model to wipe a region back to a clean empty surface. This is the
    dependable one: an empty bar cannot be misspelled, and exact copy is then
    composited on top by the deterministic renderer.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import requests
from PIL import Image, ImageDraw

from .ideogram import IdeogramResult, _download_result, _request_with_retries

EDIT_ENDPOINT = "https://api.ideogram.ai/v1/ideogram-v3/edit"

Box = tuple[int, int, int, int]


def build_mask(
    size: tuple[int, int],
    boxes: list[Box],
    *,
    edit_is_black: bool = True,
) -> Image.Image:
    """A pure black/white RGB mask marking ``boxes`` as the editable regions.

    The endpoint rejects anti-aliased or greyscale masks, so rectangles are
    drawn with hard edges and the image stays in RGB.
    """
    keep, edit = ("white", "black") if edit_is_black else ("black", "white")
    mask = Image.new("RGB", size, keep)
    painter = ImageDraw.Draw(mask)
    for box in boxes:
        painter.rectangle(box, fill=edit)
    return mask


def _png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def edit_region(
    source: Path,
    mask: Image.Image,
    prompt: str,
    destination: Path,
    *,
    rendering_speed: str = "QUALITY",
    seed: int | None = None,
) -> IdeogramResult:
    api_key = os.getenv("IDEOGRAM_API_KEY")
    if not api_key:
        raise RuntimeError("IDEOGRAM_API_KEY is missing. Add it to .env.")
    with Image.open(source) as image:
        image_bytes = _png_bytes(image.convert("RGB"))
        if mask.size != image.size:
            raise ValueError(
                f"Mask {mask.size} must match the image {image.size}."
            )
    files: dict[str, tuple] = {
        "image": ("image.png", image_bytes, "image/png"),
        "mask": ("mask.png", _png_bytes(mask), "image/png"),
        "prompt": (None, prompt),
        "rendering_speed": (None, rendering_speed),
    }
    if seed is not None:
        files["seed"] = (None, str(seed))
    response = _request_with_retries(
        headers={"Api-Key": api_key},
        files=files,
        endpoint=EDIT_ENDPOINT,
    )
    response.raise_for_status()
    return _download_result(response, destination, used_json_prompt=False)


def repair_text(
    source: Path,
    boxes: list[Box],
    exact_lines: list[str],
    destination: Path,
    *,
    surface_description: str = "a clean white rounded information bar",
    **kwargs,
) -> IdeogramResult:
    quoted = "\n".join(f'"{line}"' for line in exact_lines)
    prompt = (
        f"Replace the masked area with {surface_description} containing only this "
        f"text, rendered exactly as written with no corrections, substitutions, "
        f"added punctuation or extra words:\n{quoted}\n"
        "Use a clean bold sans-serif in dark navy on white. Keep the surrounding "
        "artwork style consistent. Do not add any other words, icons or logos."
    )
    with Image.open(source) as image:
        mask = build_mask(image.size, boxes)
    return edit_region(source, mask, prompt, destination, **kwargs)


def clear_region(
    source: Path,
    boxes: list[Box],
    destination: Path,
    *,
    surface_description: str = (
        "a clean empty white rounded information bar with a soft drop shadow, "
        "completely blank with no text, no icons and no symbols of any kind"
    ),
    **kwargs,
) -> IdeogramResult:
    prompt = (
        f"Replace the masked area with {surface_description}. The area must be "
        "entirely free of letters, numbers, words, glyphs, logos and pictograms. "
        "Keep the surrounding poster style and colours consistent."
    )
    with Image.open(source) as image:
        mask = build_mask(image.size, boxes)
    return edit_region(source, mask, prompt, destination, **kwargs)
