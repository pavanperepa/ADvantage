"""Upload academy clips to TwelveLabs, index them, and run retrieval probes."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


API_BASE = "https://api.twelvelabs.io/v1.3"
DEFAULT_INDEX_NAME = "academy-reel-test"
DEFAULT_STATE = Path("output/reel-lab/twelvelabs-state.json")
DEFAULT_RESULTS = Path("output/reel-lab/search-results.json")

SEARCHES: dict[str, dict[str, Any]] = {
    "clean_batting_shot": {
        "query_text": "A cricket batter plays a clean, powerful shot with good contact",
        "search_options": ["visual"],
    },
    "ball_hits_stumps": {
        "query_text": "A cricket ball hits the stumps or a wicket is taken",
        "search_options": ["visual", "audio"],
    },
    "bowling_action": {
        "query_text": "A cricket bowler runs up and delivers the ball",
        "search_options": ["visual"],
    },
    "coach_instruction": {
        "query_text": "A coach gives cricket technique instruction to a player",
        "search_options": ["visual", "transcription"],
    },
    "celebration_or_reaction": {
        "query_text": "Players celebrate or react excitedly after a cricket play",
        "search_options": ["visual", "audio"],
    },
    "practice_atmosphere": {
        "query_text": "An energetic youth cricket practice session in indoor nets",
        "search_options": ["visual", "audio"],
    },
    "dramatic_sports_moment": {
        "query_text": "A dramatic, visually exciting sports action moment suitable for a highlight reel",
        "search_options": ["visual", "audio"],
    },
    "coach_player_interaction": {
        "query_text": "A close interaction between a cricket coach and player",
        "search_options": ["visual", "transcription"],
    },
}


class TwelveLabsError(RuntimeError):
    pass


def load_state(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"index": {}, "clips": {}}


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    timeout: float = 60,
    **kwargs: Any,
) -> dict[str, Any]:
    response = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
    if response.status_code == 429:
        retry_after = min(float(response.headers.get("Retry-After", "5")), 30)
        print(f"Rate limited; retrying in {retry_after:.0f}s...", flush=True)
        time.sleep(retry_after)
        response = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
    if not response.ok:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text[:500]
        raise TwelveLabsError(f"{method} {url} returned {response.status_code}: {detail}")
    return response.json()


def ensure_index(headers: dict[str, str], state: dict[str, Any], index_name: str) -> str:
    existing_id = state.get("index", {}).get("id")
    if existing_id:
        print(f"Reusing index {index_name}: {existing_id}", flush=True)
        return existing_id

    page = request_json("GET", f"{API_BASE}/indexes", headers=headers)
    indexes = page.get("data", page if isinstance(page, list) else [])
    for index in indexes:
        if index.get("index_name") == index_name:
            index_id = index.get("_id")
            if index_id:
                state["index"] = {"id": index_id, "name": index_name}
                print(f"Found existing index {index_name}: {index_id}", flush=True)
                return index_id

    payload = {
        "index_name": index_name,
        "models": [
            {
                "model_name": "marengo3.0",
                "model_options": ["visual", "audio"],
            }
        ],
        "addons": ["thumbnail"],
    }
    created = request_json(
        "POST",
        f"{API_BASE}/indexes",
        headers={**headers, "Content-Type": "application/json"},
        json=payload,
    )
    index_id = created["_id"]
    state["index"] = {"id": index_id, "name": index_name}
    print(f"Created index {index_name}: {index_id}", flush=True)
    return index_id


def upload_clips(
    headers: dict[str, str], state: dict[str, Any], state_path: Path, clips: list[Path]
) -> None:
    for clip in clips:
        record = state["clips"].setdefault(clip.name, {})
        if record.get("asset_id"):
            print(f"Reusing uploaded asset for {clip.name}", flush=True)
            continue
        print(f"Uploading {clip.name} ({clip.stat().st_size / 1024 / 1024:.1f} MB)...", flush=True)
        with clip.open("rb") as video:
            result = request_json(
                "POST",
                f"{API_BASE}/assets",
                headers=headers,
                timeout=300,
                data={
                    "method": "direct",
                    "enable_thumbnail": "true",
                    "user_metadata": json.dumps({"source_filename": clip.name, "collection": "academy-reel-test"}),
                },
                files={"file": (clip.name, video, "video/mp4")},
            )
        record["asset_id"] = result["_id"]
        record["asset_status"] = result.get("status")
        save_json(state_path, state)
        print(f"Uploaded {clip.name}: {record['asset_id']}", flush=True)


def wait_for_assets(
    headers: dict[str, str], state: dict[str, Any], state_path: Path, timeout: float
) -> None:
    deadline = time.monotonic() + timeout
    pending = set(state["clips"])
    last_snapshot: tuple[tuple[str, str], ...] | None = None
    while pending:
        snapshot: list[tuple[str, str]] = []
        for filename in list(pending):
            record = state["clips"][filename]
            asset = request_json(
                "GET", f"{API_BASE}/assets/{record['asset_id']}", headers=headers
            )
            status = asset.get("status", "unknown")
            record["asset_status"] = status
            if asset.get("technical_metadata"):
                record["technical_metadata"] = asset["technical_metadata"]
            snapshot.append((filename, status))
            if status == "ready":
                pending.remove(filename)
            elif status == "failed":
                raise TwelveLabsError(f"Asset processing failed for {filename}: {asset.get('error')}")
        current = tuple(sorted(snapshot))
        if current != last_snapshot:
            print("Asset status: " + ", ".join(f"{n}={s}" for n, s in current), flush=True)
            last_snapshot = current
            save_json(state_path, state)
        if pending:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for assets: {sorted(pending)}")
            time.sleep(5)


def start_indexing(
    headers: dict[str, str], state: dict[str, Any], state_path: Path, index_id: str
) -> None:
    for filename, record in state["clips"].items():
        if record.get("indexed_asset_id"):
            print(f"Reusing indexing job for {filename}", flush=True)
            continue
        result = request_json(
            "POST",
            f"{API_BASE}/indexes/{index_id}/indexed-assets",
            headers={**headers, "Content-Type": "application/json"},
            json={"asset_id": record["asset_id"]},
        )
        record["indexed_asset_id"] = result["_id"]
        record["index_status"] = result.get("status", "queued")
        save_json(state_path, state)
        print(f"Started indexing {filename}: {record['indexed_asset_id']}", flush=True)


def wait_for_indexing(
    headers: dict[str, str], state: dict[str, Any], state_path: Path, index_id: str, timeout: float
) -> None:
    deadline = time.monotonic() + timeout
    pending = set(state["clips"])
    last_snapshot: tuple[tuple[str, str], ...] | None = None
    while pending:
        snapshot: list[tuple[str, str]] = []
        for filename in list(pending):
            record = state["clips"][filename]
            indexed = request_json(
                "GET",
                f"{API_BASE}/indexes/{index_id}/indexed-assets/{record['indexed_asset_id']}",
                headers=headers,
            )
            status = indexed.get("status", "unknown")
            record["index_status"] = status
            if indexed.get("system_metadata"):
                record["system_metadata"] = indexed["system_metadata"]
            snapshot.append((filename, status))
            if status == "ready":
                pending.remove(filename)
            elif status == "failed":
                raise TwelveLabsError(f"Indexing failed for {filename}: {indexed}")
        current = tuple(sorted(snapshot))
        if current != last_snapshot:
            print("Index status: " + ", ".join(f"{n}={s}" for n, s in current), flush=True)
            last_snapshot = current
            save_json(state_path, state)
        if pending:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for indexing: {sorted(pending)}")
            time.sleep(8)


def run_searches(headers: dict[str, str], state: dict[str, Any], index_id: str) -> dict[str, Any]:
    id_to_filename = {
        record["indexed_asset_id"]: filename for filename, record in state["clips"].items()
    }
    output: dict[str, Any] = {"index_id": index_id, "queries": {}}
    for label, spec in SEARCHES.items():
        form: list[tuple[str, str]] = [
            ("query_text", spec["query_text"]),
            ("index_id", index_id),
            ("group_by", "clip"),
            ("operator", "or"),
            ("page_limit", "12"),
        ]
        form.extend(("search_options", option) for option in spec["search_options"])
        multipart_form = [(key, (None, value)) for key, value in form]
        result = request_json(
            "POST", f"{API_BASE}/search", headers=headers, files=multipart_form
        )
        matches = result.get("data", [])
        for match in matches:
            match["filename"] = id_to_filename.get(match.get("video_id"), "unknown")
        output["queries"][label] = {"request": spec, "matches": matches}
        preview = ", ".join(
            f"{m.get('filename')} {m.get('start', 0):.2f}-{m.get('end', 0):.2f}s"
            for m in matches[:3]
        )
        print(f"Search {label}: {preview or 'no matches'}", flush=True)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("vids"))
    parser.add_argument("--index-name", default=DEFAULT_INDEX_NAME)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--timeout", type=float, default=900)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv()
    api_key = os.getenv("TWELVELABS_API_KEY")
    if not api_key:
        print("TWELVELABS_API_KEY is not configured", file=sys.stderr)
        return 2
    clips = sorted(path for path in args.input.iterdir() if path.suffix.lower() == ".mp4")
    if not clips:
        print(f"No MP4 clips found in {args.input}", file=sys.stderr)
        return 2

    headers = {"x-api-key": api_key}
    state = load_state(args.state)
    index_id = ensure_index(headers, state, args.index_name)
    save_json(args.state, state)
    upload_clips(headers, state, args.state, clips)
    wait_for_assets(headers, state, args.state, args.timeout)
    start_indexing(headers, state, args.state, index_id)
    wait_for_indexing(headers, state, args.state, index_id, args.timeout)
    results = run_searches(headers, state, index_id)
    save_json(args.results, results)
    print(f"Saved state to {args.state}", flush=True)
    print(f"Saved search results to {args.results}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
