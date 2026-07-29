"""Harvest a layout from a generated poster via Ideogram's layerize-text.

The point is **not** to get Ideogram's words. It cannot typeset: a probe on our
own FULL-mode poster returned ``PROGRAM ARW``, ``CALL OR .US`` and
``Houston, 7X77 498-7152``, faithfully extracted because that is what was in the
pixels. Every string still comes from the content file.

What it *can* give us is the model's layout decisions — where a heading sits,
how large, what colour, what alignment, what role — plus a background with the
text lifted out. A poster generated *with* text composes better than one told to
leave a hole, because the model has to solve the whole page.

**The erase needs iterating.** One pass on our probe removed 19 blocks but left
the word ``BRIGHT`` burned into the plate; a second pass caught it. So the miss
is not systematic, and running to a fixed point is both the fix and the gate: a
harvest is only accepted once a pass comes back with nothing left to find.
Leftover glyphs are disqualifying here — every string on a finished poster has
to be ours and auditable.

One thing this cannot clean is a **logo**. The probe's invented "BUCAIRAIRY"
badge survived every pass, because it is artwork rather than text. Posters
harvested for templates must be briefed to carry no logo at all.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import requests
from pydantic import BaseModel, ConfigDict, Field

from .ideogram import _request_with_retries
from .models import Rect

LAYERIZE_ENDPOINT = "https://api.ideogram.ai/v1/ideogram-v3/layerize-text"

#: How many erase passes to allow before giving up on a source image.
MAX_PASSES = 4


class TextBlock(BaseModel):
    """One detected text block, as the vendor reports it."""

    model_config = ConfigDict(extra="ignore")

    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    angle: float = 0.0
    text: str = ""
    role: str = ""
    font_name: str = ""
    font_size: float = 0.0
    font_alternatives: list[str] = Field(default_factory=list)
    line_height: float = 0.0
    color: str = ""
    formatting: list[str] = Field(default_factory=list)
    alignment: str = ""
    #: Which erase pass found this. Anything above 1 was missed the first time,
    #: which in practice means a fragment of garbled type rather than a real
    #: component — the word "BRIGHT", left over from a mangled tagline, arrived
    #: on pass 2 and became a phantom heading slot. Worth reviewing, not
    #: worth discarding automatically: a genuinely low-contrast heading can
    #: also be missed once.
    found_on_pass: int = 1

    def box(self) -> Rect:
        return Rect(
            left=self.x,
            top=self.y,
            right=self.x + self.width,
            bottom=self.y + self.height,
        )


@dataclass
class LayerizePass:
    blocks: list[TextBlock]
    base_image: bytes


@dataclass
class HarvestResult:
    """Everything one source poster yielded."""

    blocks: list[TextBlock]
    base_image: bytes
    passes: int
    #: Text still detected when the pass budget ran out. Non-empty means the
    #: harvest must be rejected: those glyphs are baked into the plate.
    residue: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.residue


def _api_key() -> str:
    key = os.getenv("IDEOGRAM_API_KEY")
    if not key:
        raise RuntimeError("IDEOGRAM_API_KEY is not set; add it to .env")
    return key


def layerize(image: bytes, *, name: str = "poster.png", timeout: int = 300) -> LayerizePass:
    """One erase pass: detected blocks, plus the image with them removed."""
    response = _request_with_retries(
        headers={"Api-Key": _api_key()},
        files={"image": (name, image, "image/png")},
        endpoint=LAYERIZE_ENDPOINT,
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()

    blocks = [TextBlock.model_validate(block) for block in payload.get("text_blocks", [])]
    url = payload.get("base_image_url")
    if not url:
        # Nothing was found, so the image is already its own clean plate.
        return LayerizePass(blocks=blocks, base_image=image)
    erased = requests.get(url, timeout=timeout)
    erased.raise_for_status()
    return LayerizePass(blocks=blocks, base_image=erased.content)


def harvest(
    source: Path | bytes,
    *,
    max_passes: int = MAX_PASSES,
    layerizer=layerize,
) -> HarvestResult:
    """Erase to a fixed point, collecting every block found on the way.

    Stops when a pass finds nothing, which is the only evidence we have that the
    plate is actually clean. If the budget runs out with text still detected,
    the leftovers are reported rather than swallowed — a caller must not bank a
    plate with someone else's words still on it.
    """
    image = source.read_bytes() if isinstance(source, Path) else source
    collected: list[TextBlock] = []

    def stamp(blocks: list[TextBlock], attempt: int) -> list[TextBlock]:
        return [block.model_copy(update={"found_on_pass": attempt}) for block in blocks]

    for attempt in range(1, max_passes + 1):
        result = layerizer(image)
        if not result.blocks:
            return HarvestResult(blocks=collected, base_image=image, passes=attempt)
        collected.extend(stamp(result.blocks, attempt))
        image = result.base_image

    # One more look, so the residue we report is what is genuinely still there
    # rather than what the last erase pass had only just removed.
    final = layerizer(image)
    return HarvestResult(
        blocks=collected + stamp(final.blocks, max_passes + 1),
        base_image=image,
        passes=max_passes + 1,
        residue=[block.text for block in final.blocks if block.text.strip()],
    )
