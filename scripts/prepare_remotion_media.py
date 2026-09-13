"""Prepare short, browser-friendly media segments for the Remotion prototype."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import imageio_ffmpeg


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "remotion" / "public"


def atempo_chain(speed: float) -> str:
    if not 0.5 <= speed <= 2.0:
        raise ValueError("Prototype clip speeds must stay between 0.5 and 2.0")
    return f"atempo={speed:.6f}"


def prepare_shot(ffmpeg: str, shot: dict[str, Any]) -> None:
    source = ROOT / shot["source"]
    output = PUBLIC / shot["media"]
    output.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        raise FileNotFoundError(source)

    start = float(shot["sourceStart"])
    source_duration = float(shot["sourceEnd"]) - start
    speed = float(shot.get("speed", 1.0))
    freeze = float(shot.get("freeze", 0.0))
    expected = source_duration / speed + freeze
    focus_x = float(shot.get("focusX", 0.5))

    vf = []
    if shot.get("interpolateSlowmo") and speed < 1:
        vf.append("minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1")
    vf.extend([
        f"setpts=(PTS-STARTPTS)/{speed:.6f}",
        "fps=30",
        "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos",
        f"crop=1080:1920:x='(iw-ow)*{focus_x:.4f}':y='(ih-oh)/2'",
        "eq=contrast=1.03:saturation=1.16:brightness=0.025:gamma=1.06:gamma_weight=0.86",
        "unsharp=5:5:0.28:5:5:0",
    ])
    if freeze:
        vf.append(f"tpad=stop_mode=clone:stop_duration={freeze:.6f}")
    vf.append("format=yuv420p")

    af = [
        "asetpts=PTS-STARTPTS",
        atempo_chain(speed),
        f"apad=pad_dur={freeze:.6f}",
        f"atrim=duration={expected:.6f}",
        "afade=t=in:st=0:d=0.04",
        f"afade=t=out:st={max(0.0, expected - 0.08):.6f}:d=0.08",
    ]

    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-ss",
        f"{start:.6f}",
        "-t",
        f"{source_duration:.6f}",
        "-i",
        str(source),
        "-filter_complex",
        f"[0:v]{','.join(vf)}[v];[0:a]{','.join(af)}[a]",
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        "-metadata:s:v:0",
        "rotate=0",
        str(output),
    ]
    print(f"Preparing {shot['id']}: {source.name} -> {output.name}")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--shot", help="Prepare only the shot with this id")
    args = parser.parse_args()
    spec_path = args.spec if args.spec.is_absolute() else ROOT / args.spec
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    shots = [shot for shot in spec["shots"] if not args.shot or shot["id"] == args.shot]
    if args.shot and not shots:
        raise ValueError(f"No shot named {args.shot!r} exists in the EditSpec")
    for shot in shots:
        target = PUBLIC / shot["media"]
        if target.exists() and not args.force:
            print(f"Keeping cached {target.name}")
            continue
        prepare_shot(ffmpeg, shot)

    brand_dir = PUBLIC / "brand"
    font_dir = PUBLIC / "fonts"
    music_dir = PUBLIC / "music"
    brand_dir.mkdir(parents=True, exist_ok=True)
    font_dir.mkdir(parents=True, exist_ok=True)
    music_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "assets" / "brand" / "22yards-houston.png", brand_dir / "logo.png")
    shutil.copy2(ROOT / "assets" / "fonts" / "archivo-black-400.woff2", font_dir / "display.woff2")
    shutil.copy2(ROOT / "assets" / "fonts" / "inter-600.woff2", font_dir / "body.woff2")
    music_source = ROOT / spec["music"]["source"]
    music_target = PUBLIC / spec["music"]["file"]
    shutil.copy2(music_source, music_target)
    print(f"Prepared {len(shots)} shot(s), brand assets, and music in {PUBLIC}")


if __name__ == "__main__":
    main()
