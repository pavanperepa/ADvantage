"""Turn a CampaignRequest's footage clips into a rendered Remotion reel.

This module is glue, not a new pipeline: it builds a minimal EditSpec (the
JSON contract `remotion/types.ts` and `remotion/AcademyIntro.tsx` already
know how to render), then shells out to the two CLI steps a human already
runs by hand for every other reel in this repo --
`scripts/media/prepare_remotion_media.py` followed by `remotion render` -- against
a generic Remotion composition (`GeneratedReel` in `remotion/Root.tsx`) that
derives its duration/canvas from the supplied spec via `calculateMetadata`
instead of a hardcoded fixture import.

Deliberately simple, per hackathon scope: one shot per footage asset, in the
order given, straight cuts between them. No shot-selection scoring, no
multi-take assembly, no per-request brand palette or logo (the existing
`prepare_remotion_media.py` always stamps the bundled 22Yards logo and fonts
-- see its `main()` -- which this adapter does not attempt to override).

The editorial decisions -- which Remotion theme, shot motion/transition
cycle, pacing, and which of `remotion/library`'s 16 overlay types tell this
reel's story -- all live in `adapters/reel_plan.py`, driven by
`CampaignRequest.reel_feel`. This module just resolves that plan against the
real, footage-derived shot timeline and assembles the EditSpec dict.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from ..domain.models import CampaignArtifact, CampaignRequest, CreativeFormat
from . import reel_plan
from .reel_plan import HERO_LINE2_MAX_CHARS, HERO_OVERLAY_MAX_SECONDS, ReelPlan, describe_plan, short_hook

__all__ = [
    "ReelAdapterError",
    "build_edit_spec",
    "produce_reel",
    "describe_plan",
    "HERO_LINE2_MAX_CHARS",
    "HERO_OVERLAY_MAX_SECONDS",
]

REPO_ROOT = Path(__file__).resolve().parents[3]
PREPARE_SCRIPT = REPO_ROOT / "scripts" / "media" / "prepare_remotion_media.py"
REMOTION_ENTRY = REPO_ROOT / "remotion" / "index.tsx"
REMOTION_CLI_ENTRY = REPO_ROOT / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"

# The generic composition added to remotion/Root.tsx for this adapter. Unlike
# AcademyIntro/PracticeMatchReel/ReelLibraryDemo/PracticeMatchLibraryReel (each
# locked to one statically-imported fixture), this composition uses Remotion's
# calculateMetadata to size itself from whatever `spec` arrives via --props.
REEL_COMPOSITION_ID = "GeneratedReel"

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
CANVAS_FPS = 30

MAX_TOTAL_SECONDS = 25.0

# Per-shot motion/transition cycle, shot pacing (min/max seconds), theme, and
# HERO_LINE2_MAX_CHARS/HERO_OVERLAY_MAX_SECONDS all come from reel_plan.py now
# (imported above) -- see its module docstring for the wrap-protection
# reasoning behind every text-length clamp used below.

# Same bundled, licensed bed used by the existing practice-match fixtures
# (reference/main/fixtures/reel-practice-match-v1.json). Reused as-is rather than accepting
# per-request music, which the CampaignRequest contract has no field for.
DEFAULT_MUSIC = {
    "source": "assets/music/mixkit-dirty-thinkin-989.mp3",
    "file": "music/dirty-thinkin.mp3",
    "title": "Dirty Thinkin'",
    "artist": "Michael Ramir C.",
    "sourceUrl": "https://mixkit.co/free-stock-music/",
    "license": "Mixkit Stock Music Free License",
    "baseVolume": 0.16,
    "duckVolume": 0.05,
    "duckStart": 0.0,
    "duckEnd": 0.0,
    "fadeIn": 0.8,
    "fadeOut": 1.15,
}

# No per-request brand palette in CampaignRequest yet; reuse the existing
# academy palette rather than inventing a new one.
DEFAULT_PRIMARY = "#2E7BFF"
DEFAULT_ACCENT = "#FFD100"
DEFAULT_INK = "#080D1F"

_SUBPROCESS_STDERR_TAIL = 4000


class ReelAdapterError(RuntimeError):
    """Raised when a reel cannot be built or rendered from a CampaignRequest."""


def build_edit_spec(request: CampaignRequest) -> dict[str, Any]:
    """Build a minimal EditSpec dict (see remotion/types.ts) from a request.

    Pure function: no subprocess calls, no filesystem writes. Raises
    ReelAdapterError for anything that would make rendering impossible.
    """
    if request.format != CreativeFormat.REEL:
        raise ReelAdapterError(
            "produce_reel requires CampaignRequest.format == CreativeFormat.REEL, "
            f"got {request.format.value!r}."
        )

    blockers = request.blockers()
    if blockers:
        raise ReelAdapterError("Cannot build a reel: " + " ".join(blockers))

    usable_assets = [asset for asset in request.footage_assets if asset.local_ref]
    if not usable_assets:
        raise ReelAdapterError(
            "None of the selected footage assets have a downloaded local file "
            "(IntakeAsset.local_ref is empty for all of them)."
        )

    slug = _slugify(request.business_name)
    plan: ReelPlan = reel_plan.plan_reel(request, shot_count=len(usable_assets))

    shots: list[dict[str, Any]] = []
    timeline = 0.0

    for index, asset in enumerate(usable_assets, start=1):
        if timeline >= MAX_TOTAL_SECONDS:
            break
        length = _shot_length(asset.duration_seconds, plan)
        length = min(length, MAX_TOTAL_SECONDS - timeline)
        if length <= 0:
            break
        shots.append(
            {
                "id": f"clip-{index:02d}",
                "source": asset.local_ref,
                "media": f"media/reel-adapter-{slug}/{index:02d}.mp4",
                "sourceStart": 0.0,
                "sourceEnd": round(length, 3),
                "speed": 1.0,
                "timelineStart": round(timeline, 3),
                "duration": round(length, 3),
                "focusX": 0.5,
                "motion": plan.shot_motions[index - 1],
                "transition": plan.shot_transitions[index - 1],
                "audio": 0.7,
            }
        )
        timeline += length

    if not shots:
        raise ReelAdapterError(
            "Could not build any shots from the supplied footage assets "
            "(all clips resolved to zero usable duration)."
        )

    # Nothing follows the last shot, so it has no transition to carry.
    shots[-1]["transition"] = "none"

    last_shot = shots[-1]
    headline = (request.offer_text or f"COME TRAIN WITH {request.business_name}").strip().upper()
    action = "TAP THE LINK TO SIGN UP" if request.destination_url else "TAP TO LEARN MORE"

    overlays: list[dict[str, Any]] = []
    if len(shots) > 1:
        # A single shot is too short to carry both a hook and a CTA without
        # them colliding on screen; only add the opening hook when there's a
        # later shot for the CTA to live on instead.
        first_shot = shots[0]
        overlays.append(
            {
                "type": "hero_title",
                "start": first_shot["timelineStart"],
                "duration": min(first_shot["duration"], HERO_OVERLAY_MAX_SECONDS),
                "eyebrow": (request.audience or "NEW THIS SEASON").upper(),
                "line1": request.business_name.upper(),
                "line2": short_hook(request.offer_text or request.brief_text),
            }
        )

    # Interior beats (checklist/quote/stat, badge/deadline, info_chips/
    # location) come from the plan, each pinned to its own interior shot so
    # none of them -- or the hero/closing above and below -- ever overlap in
    # time. A beat can point past the real last shot if MAX_TOTAL_SECONDS
    # trimmed the tail off the plan's assumed shot count; drop it rather than
    # let it collide with the closing card, which always owns the real last
    # shot.
    for beat in plan.interior_beats:
        if beat.shot_index >= len(shots) - 1:
            continue
        shot = shots[beat.shot_index]
        overlays.append(
            {
                "start": round(shot["timelineStart"] + beat.start_fraction * shot["duration"], 3),
                "duration": round(beat.duration_fraction * shot["duration"], 3),
                **beat.overlay,
            }
        )

    overlays.append(
        {
            "type": "closing",
            "start": last_shot["timelineStart"],
            "duration": last_shot["duration"],
            "headline": headline[:60],
            "action": action,
        }
    )
    overlays.sort(key=lambda overlay: overlay["start"])

    return {
        "name": f"reel-adapter-{slug}",
        "canvas": {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT, "fps": CANVAS_FPS},
        "style": {"theme": plan.theme, "defaultOverlayAnimation": plan.default_overlay_animation},
        "brand": {
            "academy": request.business_name.upper(),
            "location": "",
            "phone": request.contact_phone or "",
            "registrationUrl": request.destination_url or "",
            "primary": DEFAULT_PRIMARY,
            "accent": DEFAULT_ACCENT,
            "ink": DEFAULT_INK,
        },
        "music": dict(DEFAULT_MUSIC),
        "shots": shots,
        "overlays": overlays,
    }


def produce_reel(request: CampaignRequest, *, workdir: Path) -> CampaignArtifact:
    """Render `request`'s footage into a 1080x1920 MP4 reel under `workdir`.

    Reuses the existing CLI-only pipeline:
    1. Build an EditSpec from the ordered footage assets.
    2. `scripts/media/prepare_remotion_media.py` FFmpeg-prepares each shot's media
       into remotion/public/ (and copies brand/font/music assets).
    3. `remotion render` renders the `GeneratedReel` composition against
       that EditSpec, passed via `--props`.
    4. The output MP4 is verified (exists, non-empty, 1080x1920, duration>0)
       before being wrapped in a CampaignArtifact.
    """
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    edit_spec = build_edit_spec(request)

    editspec_path = workdir / "editspec.json"
    editspec_path.write_text(json.dumps(edit_spec, indent=2), encoding="utf-8")

    props_path = workdir / "props.json"
    props_path.write_text(json.dumps({"spec": edit_spec}, indent=2), encoding="utf-8")

    output_path = workdir / "reel.mp4"

    _run_prepare_media(editspec_path)
    _run_remotion_render(props_path, output_path)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ReelAdapterError(
            f"Remotion render reported success but {output_path} is missing or empty."
        )

    width, height, duration_seconds = _probe_video(output_path)
    if (width, height) != (CANVAS_WIDTH, CANVAS_HEIGHT):
        raise ReelAdapterError(
            f"Rendered reel is {width}x{height}, expected {CANVAS_WIDTH}x{CANVAS_HEIGHT}."
        )
    if duration_seconds <= 0:
        raise ReelAdapterError(f"Rendered reel at {output_path} has zero duration.")

    return CampaignArtifact(
        format=CreativeFormat.REEL,
        file_path=str(output_path),
        width=width,
        height=height,
        duration_seconds=duration_seconds,
    )


def _shot_length(duration_seconds: float | None, plan: ReelPlan) -> float:
    if not duration_seconds:
        return plan.default_shot_seconds
    length = min(duration_seconds, plan.max_shot_seconds)
    length = max(length, min(plan.min_shot_seconds, duration_seconds))
    return length


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "business"


def _run_prepare_media(spec_path: Path) -> None:
    command = [sys.executable, str(PREPARE_SCRIPT), str(spec_path), "--force"]
    result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise ReelAdapterError(
            "Preparing reel media failed "
            f"(scripts/media/prepare_remotion_media.py exited {result.returncode}):\n"
            f"{_tail(result.stderr)}"
        )


def _run_remotion_render(props_path: Path, output_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        raise ReelAdapterError(
            "Node.js was not found on PATH; it is required to run the Remotion CLI."
        )
    if not REMOTION_CLI_ENTRY.exists():
        raise ReelAdapterError(
            f"Remotion CLI entry not found at {REMOTION_CLI_ENTRY}; "
            "run `npm install` in the repo root before rendering reels."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        node,
        str(REMOTION_CLI_ENTRY),
        "render",
        str(REMOTION_ENTRY.relative_to(REPO_ROOT).as_posix()),
        REEL_COMPOSITION_ID,
        str(output_path),
        "--codec=h264",
        "--crf=17",
        f"--props={props_path}",
    ]
    result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise ReelAdapterError(
            f"Remotion render failed (exit {result.returncode}):\n{_tail(result.stderr)}"
        )


def _probe_video(path: Path) -> tuple[int, int, float]:
    """Read width, height, and duration (seconds) from ffmpeg's stderr banner.

    No ffprobe binary ships in this repo's environment (only imageio_ffmpeg's
    bundled ffmpeg -- see scripts/media/prepare_remotion_media.py and
    reference/main/scripts/render_reel_draft.py,
    which both call imageio_ffmpeg.get_ffmpeg_exe() and never ffprobe), so this
    parses `ffmpeg -i <file>` stream-info output instead of shelling to ffprobe.
    """
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    # `ffmpeg -i <file>` with no output always exits non-zero; the stream info
    # we want is printed to stderr regardless, so the return code is ignored.
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)], capture_output=True, text=True
    )
    stderr = result.stderr
    video_line = next((line for line in stderr.splitlines() if "Video:" in line), "")
    dims = re.search(r"(\d{2,5})x(\d{2,5})", video_line)
    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    if not dims or not duration_match:
        raise ReelAdapterError(
            f"Could not read dimensions/duration for {path} from ffmpeg output:\n"
            f"{_tail(stderr)}"
        )
    width, height = int(dims.group(1)), int(dims.group(2))
    hours, minutes, seconds = duration_match.groups()
    duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return width, height, duration


def _tail(text: str, limit: int = _SUBPROCESS_STDERR_TAIL) -> str:
    text = text or ""
    return text if len(text) <= limit else text[-limit:]
