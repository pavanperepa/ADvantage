"""Upload academy footage and render the introduction reel with Shotstack."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


INGEST_BASE = "https://api.shotstack.io/ingest/{environment}"
EDIT_BASE = "https://api.shotstack.io/edit/{environment}"
ASSET_FILES = [
    Path("vids/AP7A4296.MP4"),
    Path("vids/AP7A4298.MP4"),
    Path("vids/AP7A4309.MP4"),
    Path("vids/AP7A4318.MP4"),
    Path("vids/AP7A4314.MP4"),
    Path("vids/AP7A4281.MP4"),
    Path("assets/brand/22yards-houston.png"),
    Path("output/reel-lab/shotstack-final-frame.jpg"),
]


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def request_json(
    method: str,
    url: str,
    *,
    api_key: str | None = None,
    timeout: tuple[int, int] = (30, 120),
    **kwargs: Any,
) -> dict[str, Any]:
    headers = dict(kwargs.pop("headers", {}))
    headers.setdefault("Accept", "application/json")
    if api_key:
        headers["x-api-key"] = api_key
    for attempt in range(1, 6):
        try:
            response = requests.request(
                method, url, headers=headers, timeout=timeout, **kwargs
            )
            if not response.ok:
                raise RuntimeError(
                    f"{method} {url} failed ({response.status_code}): "
                    f"{response.text[:1000]}"
                )
            return response.json()
        except requests.RequestException:
            if attempt == 5:
                raise
            delay = attempt * 3
            print(
                f"Transient Shotstack connection error; retrying in {delay}s...",
                flush=True,
            )
            time.sleep(delay)
    raise AssertionError("unreachable")


def upload_asset(
    path: Path,
    *,
    api_key: str,
    environment: str,
    state: dict[str, Any],
    state_path: Path,
) -> str:
    key = path.as_posix()
    record = state.setdefault("assets", {}).setdefault(key, {})
    ingest_base = INGEST_BASE.format(environment=environment)

    if record.get("status") == "ready" and record.get("source"):
        print(f"Reusing {path.name}", flush=True)
        return str(record["source"])

    if not record.get("id"):
        upload = request_json(
            "POST",
            f"{ingest_base}/upload",
            api_key=api_key,
            headers={"Content-Type": "application/json"},
            json={"filename": path.name},
        )["data"]
        record.update(
            {
                "id": upload["id"],
                "status": "uploading",
                "size": path.stat().st_size,
            }
        )
        save_json(state_path, state)

        signed_url = upload["attributes"]["url"]
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        print(f"Uploading {path.name} ({path.stat().st_size / 1_000_000:.1f} MB)...", flush=True)
        with path.open("rb") as source_file:
            response = requests.put(
                signed_url,
                data=source_file,
                headers={"Content-Type": content_type},
                timeout=(30, 1200),
            )
        if not response.ok:
            record.pop("id", None)
            record["status"] = "upload_failed"
            save_json(state_path, state)
            raise RuntimeError(
                f"Upload for {path.name} failed ({response.status_code}): {response.text[:500]}"
            )
        record["status"] = "processing"
        save_json(state_path, state)

    source_id = record["id"]
    deadline = time.monotonic() + 1200
    while time.monotonic() < deadline:
        data = request_json(
            "GET", f"{ingest_base}/sources/{source_id}", api_key=api_key
        )["data"]["attributes"]
        status = data.get("status")
        record["status"] = status
        if data.get("source"):
            record["source"] = data["source"]
        save_json(state_path, state)
        if status == "ready":
            print(f"Ready: {path.name}", flush=True)
            return str(record["source"])
        if status in {"failed", "deleted"}:
            raise RuntimeError(f"Shotstack ingest failed for {path.name}: {data}")
        time.sleep(5)
    raise TimeoutError(f"Timed out waiting for Shotstack to ingest {path.name}")


def rich_text(
    text: str,
    *,
    start: float,
    length: float,
    size: int,
    offset_y: float,
    animation: str | None = "shift",
    effect: str | None = None,
    fade_out: bool = True,
) -> dict[str, Any]:
    asset: dict[str, Any] = {
        "type": "rich-text",
        "text": text,
        "font": {
            "family": "Montserrat",
            "size": size,
            "weight": 800,
            "color": "#FFFFFF",
        },
        "stroke": {"width": 2, "color": "#08152B", "opacity": 0.9},
    }
    if animation:
        asset["animation"] = {
            "preset": animation,
            "duration": min(0.65, length),
            "style": "word",
            "direction": "up",
        }
    clip: dict[str, Any] = {
        "asset": asset,
        "start": start,
        "length": length,
        "width": 1040,
        "height": 220,
        "position": "center",
        "offset": {"x": 0, "y": offset_y},
    }
    if effect:
        clip["effect"] = effect
    if fade_out:
        clip["transition"] = {"out": "fadeFast"}
    return clip


def recede_text(
    text: str,
    *,
    start: float,
    length: float,
    size: int,
    offset_y: float,
) -> list[dict[str, Any]]:
    entrance_length = min(0.70, length / 2)
    return [
        rich_text(
            text,
            start=start,
            length=entrance_length,
            size=size,
            offset_y=offset_y,
            animation="shift",
            effect="zoomOutFast",
            fade_out=False,
        ),
        rich_text(
            text,
            start=start + entrance_length,
            length=length - entrance_length,
            size=size,
            offset_y=offset_y,
            animation=None,
            effect=None,
        ),
    ]


def build_edit(sources: dict[str, str]) -> dict[str, Any]:
    video_specs = [
        ("vids/AP7A4296.MP4", 0.35, 2.85, 1.0, "zoomInSlow"),
        ("vids/AP7A4298.MP4", 0.15, 3.50, 1.0, "zoomInSlow"),
        ("vids/AP7A4309.MP4", 0.25, 4.20, 1.0, "slideLeftSlow"),
        ("vids/AP7A4318.MP4", 8.85, 4.80, 1.0, "zoomInSlow"),
        ("vids/AP7A4314.MP4", 3.75, 3.03, 0.90, "zoomInSlow"),
        ("vids/AP7A4281.MP4", 0.00, 1.96, 0.96, "zoomInSlow"),
    ]
    starts = [0.0, 2.85, 6.35, 10.55, 15.35, 18.38]
    background_clips: list[dict[str, Any]] = []
    for index, ((path, trim, length, speed, effect), start) in enumerate(
        zip(video_specs, starts, strict=True)
    ):
        clip: dict[str, Any] = {
            "asset": {
                "type": "video",
                "src": sources[path],
                "trim": trim,
                "speed": speed,
                "volume": 0.7,
                "transcode": True,
            },
            "start": start,
            "length": length,
            "fit": "crop",
            "position": "center",
            "effect": effect,
            "filter": "boost",
        }
        background_clips.append(clip)

    final_start = 20.34
    final_length = 1.55
    background_clips.append(
        {
            "asset": {
                "type": "image",
                "src": sources["output/reel-lab/shotstack-final-frame.jpg"],
            },
            "start": final_start,
            "length": final_length,
            "fit": "crop",
        }
    )

    titles = [
        *recede_text("WELCOME TO 22YARDS", start=0.25, length=2.30, size=56, offset_y=0.12),
        *recede_text("EXPERT COACHING", start=3.05, length=2.60, size=56, offset_y=0.12),
        *recede_text("CORRECT THE DETAILS", start=6.55, length=2.75, size=52, offset_y=0.12),
        *recede_text("WATCH. LEARN. APPLY.", start=10.75, length=2.85, size=54, offset_y=0.12),
        *recede_text(
            "BUILD SKILL. BUILD CONFIDENCE.",
            start=15.55,
            length=2.55,
            size=40,
            offset_y=0.12,
        ),
    ]

    dim_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" '
        'viewBox="0 0 1080 1920"><rect width="1080" height="1920" '
        'fill="#050A12" fill-opacity="0.60"/></svg>'
    )
    dim_clip = {
        "asset": {"type": "svg", "src": dim_svg},
        "start": 20.05,
        "length": 1.84,
        "transition": {"in": "fadeFast"},
    }
    logo_clip = {
        "asset": {
            "type": "image",
            "src": sources["assets/brand/22yards-houston.png"],
        },
        "start": 20.10,
        "length": 1.79,
        "width": 420,
        "height": 570,
        "fit": "contain",
        "position": "center",
        "offset": {"x": 0, "y": 0.18},
        "effect": "zoomOutSlow",
        "transition": {"in": "fadeFast"},
    }
    cta = rich_text(
        "CALL US FOR MORE INFO",
        start=20.20,
        length=1.69,
        size=46,
        offset_y=-0.17,
        animation="fadeIn",
        effect=None,
    )
    phone = rich_text(
        "(713) 570-9054",
        start=20.27,
        length=1.62,
        size=56,
        offset_y=-0.27,
        animation="fadeIn",
        effect=None,
    )

    return {
        "timeline": {
            "background": "#050A12",
            "tracks": [
                {"clips": [phone]},
                {"clips": [cta]},
                {"clips": [logo_clip]},
                {"clips": [dim_clip]},
                {"clips": titles},
                {"clips": background_clips},
            ],
            "cache": True,
        },
        "output": {
            "format": "mp4",
            "resolution": "hd",
            "aspectRatio": "9:16",
            "fps": 30,
            "quality": "high",
            "destinations": [{"provider": "shotstack"}],
        },
    }


def render(
    edit: dict[str, Any],
    *,
    api_key: str,
    environment: str,
    state: dict[str, Any],
    state_path: Path,
    payload_path: Path,
    output_path: Path,
) -> None:
    edit_base = EDIT_BASE.format(environment=environment)
    save_json(payload_path, edit)
    render_record = state.setdefault("render", {})
    if not render_record.get("id") or render_record.get("status") in {"failed", "done"}:
        response = request_json(
            "POST",
            f"{edit_base}/render",
            api_key=api_key,
            headers={"Content-Type": "application/json"},
            json=edit,
        )["response"]
        render_record.clear()
        render_record.update({"id": response["id"], "status": "queued"})
        save_json(state_path, state)
        print(f"Queued render {response['id']}", flush=True)

    render_id = render_record["id"]
    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        response = request_json(
            "GET", f"{edit_base}/render/{render_id}", api_key=api_key
        )["response"]
        status = response.get("status")
        render_record.update({"status": status})
        if response.get("url"):
            render_record["url"] = response["url"]
        save_json(state_path, state)
        print(f"Render status: {status}", flush=True)
        if status == "done":
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with requests.get(response["url"], stream=True, timeout=(30, 600)) as download:
                download.raise_for_status()
                with output_path.open("wb") as output_file:
                    for chunk in download.iter_content(chunk_size=1024 * 1024):
                        output_file.write(chunk)
            print(f"Downloaded {output_path}", flush=True)
            return
        if status == "failed":
            raise RuntimeError(f"Shotstack render failed: {response}")
        time.sleep(10)
    raise TimeoutError("Timed out waiting for Shotstack render")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", default="stage", choices=["stage", "v1"])
    parser.add_argument(
        "--state", type=Path, default=Path("output/reel-lab/shotstack-state.json")
    )
    parser.add_argument(
        "--payload", type=Path, default=Path("output/reel-lab/shotstack-edit.json")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/reel-lab/academy-intro-shotstack.mp4"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv()
    api_key = os.getenv("SHOTSTACK_API")
    if not api_key:
        raise RuntimeError("SHOTSTACK_API is missing from .env")
    missing = [str(path) for path in ASSET_FILES if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Shotstack inputs: {', '.join(missing)}")
    state = (
        json.loads(args.state.read_text(encoding="utf-8"))
        if args.state.exists()
        else {"environment": args.environment, "assets": {}}
    )
    if state.get("environment") != args.environment:
        raise RuntimeError("State environment does not match requested environment")
    sources: dict[str, str] = {}
    for path in ASSET_FILES:
        sources[path.as_posix()] = upload_asset(
            path,
            api_key=api_key,
            environment=args.environment,
            state=state,
            state_path=args.state,
        )
    render(
        build_edit(sources),
        api_key=api_key,
        environment=args.environment,
        state=state,
        state_path=args.state,
        payload_path=args.payload,
        output_path=args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
