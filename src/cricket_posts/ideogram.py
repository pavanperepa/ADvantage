from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict

from .layout import poster_copy_lines
from .models import BrandProfile, DesignSpec, PosterContent, PostBrief


ENDPOINT = "https://api.ideogram.ai/v1/ideogram-v4/generate"


class IdeogramResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    seed: int | None = None
    resolution: str = ""
    prompt: str = ""
    request_id: str = ""
    used_json_prompt: bool = False


def _request_with_retries(
    *,
    headers: dict[str, str],
    files: dict[str, tuple[Any, ...]],
    attempts: int = 3,
    endpoint: str = ENDPOINT,
) -> requests.Response:
    response: requests.Response | None = None
    for attempt in range(attempts):
        response = requests.post(
            endpoint,
            headers=headers,
            files=files,
            timeout=180,
        )
        if response.status_code not in {429, 500, 502, 503, 504}:
            return response
        if attempt < attempts - 1:
            time.sleep(1.5 * (attempt + 1))
    assert response is not None
    return response


def _download_result(
    response: requests.Response,
    destination: Path,
    *,
    used_json_prompt: bool,
) -> IdeogramResult:
    response.raise_for_status()
    payload = response.json()
    items = payload.get("data") or []
    if not items or not items[0].get("url"):
        raise RuntimeError(f"Ideogram returned no image URL: {payload}")
    item = items[0]
    image_response = requests.get(item["url"], timeout=120)
    image_response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(image_response.content)
    return IdeogramResult(
        path=str(destination),
        seed=item.get("seed"),
        resolution=item.get("resolution", ""),
        prompt=item.get("prompt", ""),
        request_id=payload.get("request_id", ""),
        used_json_prompt=used_json_prompt,
    )


def generate_from_prompt(
    prompt: str,
    destination: Path,
    *,
    resolution: str = "1728x2304",
    rendering_speed: str = "TURBO",
) -> Path:
    api_key = os.getenv("IDEOGRAM_API_KEY")
    if not api_key:
        raise RuntimeError("IDEOGRAM_API_KEY is missing. Add it to .env.")

    headers = {"Api-Key": api_key}
    response = _request_with_retries(
        headers=headers,
        files={
            "text_prompt": (None, prompt),
            "resolution": (None, resolution),
            "rendering_speed": (None, rendering_speed),
            "enable_copyright_detection": (None, "true"),
        },
    )
    if response.status_code == 422:
        # Keep the prototype tolerant if an account/model revision rejects the
        # requested portrait resolution. V4 defaults to a documented 2K square.
        response = _request_with_retries(
            headers=headers,
            files={
                "text_prompt": (None, prompt),
                "rendering_speed": (None, rendering_speed),
                "enable_copyright_detection": (None, "true"),
            },
        )
    return Path(_download_result(response, destination, used_json_prompt=False).path)


def generate_art(post: PostBrief, destination: Path) -> Path:
    return generate_from_prompt(post.art_prompt, destination)


def _structured_prompt(design: DesignSpec) -> dict[str, Any]:
    focus_boxes = {
        "art_forward": {
            "left": [0, 150, 540, 1050],
            "center": [230, 140, 770, 1050],
            "right": [460, 140, 1000, 1050],
        },
        "balanced": {
            "left": [0, 100, 470, 930],
            "center": [270, 100, 730, 930],
            "right": [540, 100, 1000, 930],
        },
        "information_dense": {
            "left": [0, 80, 400, 760],
            "center": [300, 80, 700, 760],
            "right": [600, 80, 1000, 760],
        },
    }
    subject_by_family = {
        "announcement_hero": (
            "One large, realistic cricket athlete in an authentic training moment, photographed "
            "close enough for the person to remain visually dominant"
        ),
        "tournament_registration": (
            "One polished cricket trophy and one leather cricket ball, dramatically lit and "
            "large in the foreground"
        ),
        "tournament_category_grid": (
            "One polished cricket trophy and one leather cricket ball, dramatically lit and "
            "large in the upper foreground"
        ),
        "summer_camp": (
            "One dynamic teenage cricket batter mid-stroke, full protective equipment, large "
            "and sharply photographed"
        ),
        "coaching_services": (
            "One encouraging cricket coach teaching one young child how to hold a cricket bat, "
            "a warm authentic foundation-training moment, both people large and clearly visible"
        ),
        "lane_rental": (
            "One premium indoor cricket lane and bowling machine, strong depth and perspective, "
            "with one athlete preparing in the foreground"
        ),
    }
    subject_box = (
        [70, 70, 930, 950]
        if design.visual_treatment.value == "vignette"
        else focus_boxes[design.composition.value][design.art_focus]
    )
    background_description = (
        "A bright, complete, believable cricket environment with natural depth and edge-to-edge "
        "visual detail. No empty copy area and absolutely no signage, writing, borders, or interface."
        if design.visual_treatment.value == "vignette"
        else (
            "A believable full-frame cricket training environment with natural depth, dark "
            "uncluttered shadows, and absolutely no signage, writing, borders, or interface."
        )
    )
    subject_description = design.art_subject or subject_by_family[design.family.value]
    return {
        "high_level_description": design.art_prompt,
        "compositional_deconstruction": {
            "background": background_description,
            "elements": [
                {
                    "type": "obj",
                    "bbox": subject_box,
                    "desc": (
                        f"{subject_description}. Fill the assigned bounding box "
                        "with a single coherent photographic scene. No branding, writing, icons, "
                        "screens, diagrams, HUD elements, or interface graphics."
                    ),
                }
            ],
        },
        "style_description": {
            "aesthetics": "cinematic, authentic, focused, immersive",
            "lighting": "dramatic directional stadium light with deep clean shadows",
            "medium": "documentary editorial sports photography",
            "photo": "high-detail full-frame professional photograph without graphic design",
        },
    }


def generate_studio_art(
    design: DesignSpec,
    destination: Path,
    *,
    rendering_speed: str = "QUALITY",
) -> IdeogramResult:
    api_key = os.getenv("IDEOGRAM_API_KEY")
    if not api_key:
        raise RuntimeError("IDEOGRAM_API_KEY is missing. Add it to .env.")
    headers = {"Api-Key": api_key}
    json_prompt = _structured_prompt(design)
    resolution = (
        "2048x2048"
        if design.visual_treatment.value == "vignette"
        else "1728x2304"
    )
    response = _request_with_retries(
        headers=headers,
        files={
            "json_prompt": (
                None,
                json.dumps(json_prompt, ensure_ascii=False),
                "application/json",
            ),
            "resolution": (None, resolution),
            "rendering_speed": (None, rendering_speed),
            "enable_copyright_detection": (None, "true"),
        },
    )
    if response.status_code in {400, 422}:
        # Accounts and API revisions can differ in JSON-prompt validation.
        # Retain an explicit, guarded text-prompt fallback.
        fallback = _request_with_retries(
            headers=headers,
            files={
                "text_prompt": (None, design.art_prompt),
                "resolution": (None, resolution),
                "rendering_speed": (None, rendering_speed),
                "enable_copyright_detection": (None, "true"),
            },
        )
        return _download_result(fallback, destination, used_json_prompt=False)
    return _download_result(response, destination, used_json_prompt=True)


def full_poster_prompt(content: PosterContent, brand: BrandProfile) -> str:
    lines = poster_copy_lines(content, brand)
    exact_copy = "\n".join(f'{index + 1}. "{line}"' for index, line in enumerate(lines))
    return f"""Create a complete premium 4:5 vertical promotional poster for a cricket academy.
Make the cricket artwork visually dominant: cinematic training action, depth, atmosphere,
lighting, and a strong professional sports-advertising composition. Integrate the typography
into the artwork with a clear hierarchy and generous but intentional spacing.

Render every line below exactly as written. Do not fix spelling, change capitalization,
change punctuation, rephrase, omit, duplicate, or add any factual text:

{exact_copy}

Use the brand palette: ink {brand.palette.ink}, surface {brand.palette.surface},
accent {brand.palette.accent}, highlight {brand.palette.highlight}. Keep phone numbers,
dates, prices, class counts, and age ranges especially clear. Do not add sponsor names,
watermarks, placeholder text, or invented claims."""


def full_poster_json_prompt(
    content: PosterContent,
    brand: BrandProfile,
) -> dict[str, Any]:
    lines = poster_copy_lines(content, brand)
    copy_context = " ".join(lines).lower()
    organization = content.organization or brand.name
    schedule = content.schedule.display() if content.schedule else ""
    footer_values = {
        *content.location_lines,
        *(contact.display() for contact in content.contacts),
        *brand.contact_lines,
    }
    text_elements: list[dict[str, Any]] = []
    for line in lines:
        if line == content.title:
            description = (
                "The largest headline, bold condensed athletic display type, high visual priority."
            )
        elif line == organization:
            description = "Prominent academy name in a clean bold sports wordmark treatment."
        elif line == content.subtitle:
            description = "Strong supporting headline directly beneath the main title."
        elif line == schedule:
            description = "A highly legible schedule band with generous tracking."
        elif line == content.price_line:
            description = "A bold high-contrast price callout."
        elif line in content.detail_lines:
            description = "A compact bold program fact callout."
        elif line in footer_values:
            description = "Small but highly legible footer information."
        elif line in content.cta_lines:
            description = "A bold call-to-action treatment."
        else:
            description = "Supporting information in clear, readable type."
        text_elements.append(
            {
                "type": "text",
                "text": line,
                "desc": (
                    f"{description} Render this text exactly without correction, substitution, "
                    "translation, added punctuation, or additional words."
                ),
            }
        )

    if any(
        marker in copy_context
        for marker in ("foundation", "starting from 5", "children", "young players")
    ):
        campaign_description = (
            "A premium 4:5 vertical foundation cricket program announcement for young children, "
            "with a warm, optimistic coaching atmosphere, clear integrated typography, and a "
            "polished professional sports-academy hierarchy."
        )
        background_description = (
            "A modern indoor cricket facility with softly focused practice nets, deep navy "
            "shadows, warm golden light, restrained cyan rim light, and no environmental writing."
        )
        subject_description = (
            "An encouraging cricket coach kneeling beside a happy child around five years old, "
            "gently helping the child hold a cricket bat correctly; an authentic, welcoming "
            "foundation-training moment, both subjects large and visually dominant."
        )
    else:
        campaign_description = (
            "A premium 4:5 vertical cricket academy promotion with cinematic full-frame sports "
            "photography, clear integrated typography, and a polished professional hierarchy."
        )
        background_description = (
            "A full-frame dramatic cricket training environment with stadium lights, deep "
            "shadows, subtle rim light, and no environmental writing."
        )
        subject_description = (
            "A dynamic young cricket batter mid-stroke, large and visually dominant, wearing "
            "unbranded training clothing and full protective equipment."
        )

    return {
        "high_level_description": (
            f"{campaign_description} Use the brand colors {brand.palette.ink}, "
            f"{brand.palette.surface}, {brand.palette.accent}, and {brand.palette.highlight}."
        ),
        "compositional_deconstruction": {
            "background": background_description,
            "elements": [
                {
                    "type": "obj",
                    "bbox": [320, 180, 980, 880],
                    "desc": subject_description,
                },
                *text_elements,
            ],
        },
        "style_description": {
            "aesthetics": "premium, bold, cinematic, energetic, modern",
            "lighting": "dramatic stadium lighting with cyan rim light and warm highlights",
            "medium": "professional sports advertising photography and typography",
        },
    }


def _normalize_full_poster(
    source: Path,
    destination: Path,
    *,
    background_color: str,
) -> Path:
    with Image.open(source) as image:
        converted = image.convert("RGB")
        normalized = ImageOps.pad(
            converted,
            (1080, 1350),
            method=Image.Resampling.LANCZOS,
            color=background_color,
            centering=(0.5, 0.5),
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        normalized.save(destination, format="PNG", optimize=True)
    return destination


def generate_full_poster(
    content: PosterContent,
    brand: BrandProfile,
    raw_destination: Path,
    poster_destination: Path,
    *,
    rendering_speed: str = "QUALITY",
) -> IdeogramResult:
    api_key = os.getenv("IDEOGRAM_API_KEY")
    if not api_key:
        raise RuntimeError("IDEOGRAM_API_KEY is missing. Add it to .env.")
    prompt = full_poster_prompt(content, brand)
    json_prompt = full_poster_json_prompt(content, brand)
    headers = {"Api-Key": api_key}
    files = {
        "json_prompt": (
            None,
            json.dumps(json_prompt, ensure_ascii=False),
            "application/json",
        ),
        "resolution": (None, "1792x2240"),
        "rendering_speed": (None, rendering_speed),
        "enable_copyright_detection": (None, "true"),
    }
    response = _request_with_retries(headers=headers, files=files)
    if response.status_code in {400, 422}:
        files.pop("json_prompt")
        files["text_prompt"] = (None, prompt)
        files["resolution"] = (None, "1728x2304")
        response = _request_with_retries(headers=headers, files=files)
        used_json_prompt = False
    else:
        used_json_prompt = True
    result = _download_result(
        response,
        raw_destination,
        used_json_prompt=used_json_prompt,
    )
    _normalize_full_poster(
        raw_destination,
        poster_destination,
        background_color=brand.palette.ink,
    )
    result.path = str(raw_destination)
    return result
