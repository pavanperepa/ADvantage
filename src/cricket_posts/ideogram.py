from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel, ConfigDict

from .models import DesignSpec


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
    timeout: int = 180,
) -> requests.Response:
    response: requests.Response | None = None
    failure: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                files=files,
                timeout=timeout,
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            # A dropped connection is as transient as a 503 and arrives far more
            # often on the larger endpoints, where the upload is megabytes. The
            # status-code check never sees it, so retry here too.
            failure = exc
            if attempt == attempts - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
            continue
        if response.status_code not in {429, 500, 502, 503, 504}:
            return response
        if attempt < attempts - 1:
            time.sleep(1.5 * (attempt + 1))
    if response is None and failure is not None:  # pragma: no cover - defensive
        raise failure
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
