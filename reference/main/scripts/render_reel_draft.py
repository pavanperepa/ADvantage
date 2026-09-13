"""Render a deterministic vertical reel from a JSON edit decision list."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import imageio_ffmpeg


def escape_filter_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


def atempo_chain(speed: float) -> list[str]:
    """Return legal FFmpeg atempo stages for any positive speed."""
    if speed <= 0:
        raise ValueError("Clip speed must be greater than zero")
    filters: list[str] = []
    remaining = speed
    while remaining > 2:
        filters.append("atempo=2")
        remaining /= 2
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining}")
    return filters


def build_command(plan: dict[str, Any], output: Path) -> list[str]:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    width = int(plan.get("width", 1080))
    height = int(plan.get("height", 1920))
    fps = int(plan.get("fps", 30))
    clips = plan["clips"]
    clip_durations = [
        (float(clip["end"]) - float(clip["start"])) / float(clip.get("speed", 1))
        + float(clip.get("freeze_duration", 0))
        for clip in clips
    ]
    transitions = plan.get("transitions", [])
    transition_duration = sum(float(item["duration"]) for item in transitions)
    duration = sum(clip_durations) - transition_duration
    grade = plan.get("grade", {})
    contrast = float(grade.get("contrast", 1))
    saturation = float(grade.get("saturation", 1))
    brightness = float(grade.get("brightness", 0))

    command = [ffmpeg, "-y", "-hide_banner"]
    for clip in clips:
        command.extend(["-i", str(Path(clip["file"]))])
    logo = plan.get("logo")
    if logo:
        command.extend(
            ["-loop", "1", "-framerate", str(fps), "-i", str(Path(logo["file"]))]
        )

    graph: list[str] = []
    concat_inputs: list[str] = []
    for index, clip in enumerate(clips):
        start = float(clip["start"])
        end = float(clip["end"])
        speed = float(clip.get("speed", 1))
        video_filters = [
            f"trim=start={start}:end={end}",
            f"setpts=(PTS-STARTPTS)/{speed}",
        ]
        if clip.get("interpolate_slowmo") and speed < 1:
            interpolation_mode = clip.get("interpolation_mode", "blend")
            if interpolation_mode == "motion":
                video_filters.append(
                    "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:"
                    "me_mode=bidir:vsbmc=1"
                )
            else:
                video_filters.append("minterpolate=fps=60:mi_mode=blend")
        crop_x = clip.get("crop_x", "(iw-ow)/2")
        crop_y = clip.get("crop_y", "(ih-oh)/2")
        video_filters.extend(
            [
                f"fps={fps}",
                f"scale={width}:{height}:force_original_aspect_ratio=increase",
                f"crop={width}:{height}:x='{crop_x}':y='{crop_y}'",
                f"eq=contrast={contrast}:saturation={saturation}:brightness={brightness}",
                "unsharp=5:5:0.35:5:5:0",
                "setsar=1",
            ]
        )
        motion = clip.get("motion")
        if clip.get("push_in") or motion == "push_in":
            video_filters.append(
                f"zoompan=z='min(max(zoom,pzoom)+0.00075,1.05)':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d=1:s={width}x{height}:fps={fps}"
            )
        elif motion == "punch":
            video_filters.append(
                f"zoompan=z='if(lt(on,5),1.10-on*0.01,1.05)':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d=1:s={width}x{height}:fps={fps}"
            )
        elif motion in {"drift_left", "drift_right"}:
            direction = "1" if motion == "drift_left" else "-1"
            video_filters.append(
                f"zoompan=z=1.055:x='iw/2-(iw/zoom/2)+({direction})*"
                f"min(on*0.35,20)':y='ih/2-(ih/zoom/2)':"
                f"d=1:s={width}x{height}:fps={fps}"
            )
        freeze_duration = float(clip.get("freeze_duration", 0))
        if freeze_duration:
            video_filters.append(
                f"tpad=stop_mode=clone:stop_duration={freeze_duration}"
            )
        graph.append(f"[{index}:v]" + ",".join(video_filters) + f"[v{index}]")
        audio_filters = [
            f"atrim=start={start}:end={end}",
            "asetpts=PTS-STARTPTS",
            *atempo_chain(speed),
            "aresample=48000",
        ]
        if freeze_duration:
            audio_filters.extend(
                [
                    f"apad=pad_dur={freeze_duration}",
                    f"atrim=duration={clip_durations[index]}",
                ]
            )
        graph.append(f"[{index}:a]" + ",".join(audio_filters) + f"[a{index}]")
        concat_inputs.append(f"[v{index}][a{index}]")

    if transitions:
        if len(transitions) != len(clips) - 1:
            raise ValueError("A transition must be provided for every clip boundary")
        current_video = "v0"
        current_audio = "a0"
        running_duration = clip_durations[0]
        for index, transition in enumerate(transitions, start=1):
            transition_time = float(transition["duration"])
            transition_type = transition.get("type", "fade")
            offset = running_duration - transition_time
            video_out = f"xv{index}"
            audio_out = f"xa{index}"
            graph.append(
                f"[{current_video}][v{index}]xfade=transition={transition_type}:"
                f"duration={transition_time}:offset={offset}[{video_out}]"
            )
            graph.append(
                f"[{current_audio}][a{index}]acrossfade=d={transition_time}:"
                f"c1=tri:c2=tri[{audio_out}]"
            )
            running_duration += clip_durations[index] - transition_time
            current_video = video_out
            current_audio = audio_out
        graph.append(f"[{current_video}]null[basev]")
        graph.append(f"[{current_audio}]anull[basea]")
    else:
        graph.append(
            "".join(concat_inputs)
            + f"concat=n={len(clips)}:v=1:a=1[basev][basea]"
        )

    current_video = "basev"
    end_card = plan.get("end_card")
    if end_card:
        end_start = float(end_card["start"])
        end_end = float(end_card.get("end", duration))
        dim = float(end_card.get("dim", 0.5))
        graph.append(
            f"[{current_video}]drawbox=x=0:y=0:w=iw:h=ih:color=black@{dim}:"
            f"t=fill:enable='between(t,{end_start},{end_end})'[endcard]"
        )
        current_video = "endcard"

    if logo:
        logo_index = len(clips)
        logo_start = float(logo["start"])
        logo_end = float(logo.get("end", duration))
        logo_duration = logo_end - logo_start
        logo_width = int(logo.get("width", 420))
        logo_y = logo.get("y", "(H-h)/2")
        logo_fade = float(logo.get("fade", 0.3))
        graph.append(
            f"[{logo_index}:v]trim=duration={logo_duration},setpts=PTS-STARTPTS,"
            f"scale={logo_width}:-1,format=rgba,"
            f"fade=t=in:st=0:d={logo_fade}:alpha=1,"
            f"setpts=PTS+{logo_start}/TB[logov]"
        )
        graph.append(
            f"[{current_video}][logov]overlay=x=(W-w)/2:y='{logo_y}':"
            f"enable='between(t,{logo_start},{logo_end})':eof_action=pass[withlogo]"
        )
        current_video = "withlogo"

    for index, flash in enumerate(plan.get("flashes", [])):
        start = float(flash["time"])
        flash_duration = float(flash.get("duration", 0.07))
        opacity = float(flash.get("opacity", 0.55))
        out_label = f"flash{index}"
        graph.append(
            f"[{current_video}]drawbox=x=0:y=0:w=iw:h=ih:color=white@{opacity}:"
            f"t=fill:enable='between(t,{start},{start + flash_duration})'[{out_label}]"
        )
        current_video = out_label

    font_path = "C\\:/Windows/Fonts/arialbd.ttf"
    for index, title in enumerate(plan.get("titles", [])):
        start = float(title["start"])
        end = float(title["end"])
        text = escape_filter_text(str(title["text"]))
        size = int(title.get("size", 54))
        out_label = f"title{index}"
        style = title.get("style", "banner")
        fade_duration = min(float(title.get("fade", 0.24)), (end - start) / 3)
        alpha = (
            f"if(lt(t,{start + fade_duration}),(t-{start})/{fade_duration},"
            f"if(lt(t,{end - fade_duration}),1,({end}-t)/{fade_duration}))"
        )
        if style == "recede":
            motion_duration = float(title.get("motion_duration", 0.65))
            motion_end = start + motion_duration
            start_size = int(title.get("start_size", round(size * 1.55)))
            final_y = int(title.get("y", 760))
            start_y = int(title.get("start_y", final_y + 90))
            font_size = (
                f"if(lt(t,{motion_end}),{start_size}-({start_size - size})*"
                f"(t-{start})/{motion_duration},{size})"
            )
            y_position = (
                f"if(lt(t,{motion_end}),{start_y}+({final_y - start_y})*"
                f"(t-{start})/{motion_duration},{final_y})"
            )
            graph.append(
                f"[{current_video}]drawtext=fontfile='{font_path}':text='{text}':"
                f"fontcolor=white:fontsize='{font_size}':x=(w-text_w)/2:"
                f"y='{y_position}':borderw=2:bordercolor=black@0.65:"
                f"shadowcolor=black@0.9:shadowx=4:shadowy=5:alpha='{alpha}':"
                f"enable='between(t,{start},{end})'[{out_label}]"
            )
        else:
            text_y = int(title.get("y", 200))
            box_y = int(title.get("box_y", text_y - 50))
            box_height = int(title.get("box_height", 160))
            box_opacity = float(title.get("box_opacity", 0.58))
            underline_y = int(title.get("underline_y", box_y + box_height))
            graph.append(
                f"[{current_video}]drawbox=x=60:y={box_y}:w={width - 120}:h={box_height}:"
                f"color=black@{box_opacity}:t=fill:enable='between(t,{start},{end})',"
                f"drawbox=x=60:y={underline_y}:w=190:h=10:color=#f6d32d@0.95:t=fill:"
                f"enable='between(t,{start},{end})',"
                f"drawtext=fontfile='{font_path}':text='{text}':fontcolor=white:"
                f"fontsize={size}:x=(w-text_w)/2:y={text_y}:"
                f"shadowcolor=black@0.8:shadowx=3:shadowy=3:alpha='{alpha}':"
                f"enable='between(t,{start},{end})'[{out_label}]"
            )
        current_video = out_label

    fade_out_start = max(duration - 0.25, 0)
    graph.append(
        f"[{current_video}]fade=t=in:st=0:d=0.12,"
        f"fade=t=out:st={fade_out_start}:d=0.25[outv]"
    )
    graph.append(
        f"[basea]loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.12,"
        f"afade=t=out:st={fade_out_start}:d=0.25[outa]"
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    command.extend(
        [
            "-filter_complex",
            ";".join(graph),
            "-map",
            "[outv]",
            "-map",
            "[outa]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path, default=Path("output/reel-lab/coaching-probe.mp4"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    command = build_command(plan, args.output)
    print(f"Rendering {args.output}...", flush=True)
    subprocess.run(command, check=True)
    print(f"Rendered {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
