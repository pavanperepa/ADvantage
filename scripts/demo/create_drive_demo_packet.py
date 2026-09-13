"""Create a permission-safe neutral media packet for Google Drive intake demos."""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "drive_demo_source"
WIDTH = 720
HEIGHT = 1280
FPS = 24


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default(size=size)


def create_logo(path: Path) -> None:
    image = Image.new("RGB", (800, 400), "#102A43")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((70, 70, 730, 330), radius=46, fill="#F0B429")
    draw.ellipse((105, 105, 315, 315), fill="#2CB1BC")
    draw.text((350, 125), "NORTHSTAR", font=font(58), fill="#102A43")
    draw.text((350, 205), "DEMO STUDIO", font=font(34), fill="#243B53")
    image.save(path, "PNG")


def create_photo(path: Path) -> None:
    image = Image.new("RGB", (1200, 900), "#D9E2EC")
    draw = ImageDraw.Draw(image)
    for y in range(image.height):
        ratio = y / image.height
        color = (
            int(28 + 60 * ratio),
            int(74 + 90 * ratio),
            int(110 + 80 * ratio),
        )
        draw.line((0, y, image.width, y), fill=color)
    draw.rounded_rectangle((120, 120, 1080, 780), radius=48, fill="#FFFFFF")
    draw.rectangle((180, 500, 1020, 700), fill="#BCCCDC")
    for x, color in ((250, "#2CB1BC"), (520, "#F0B429"), (790, "#D64545")):
        draw.ellipse((x, 250, x + 170, 420), fill=color)
    draw.text((220, 570), "SYNTHETIC DEMO SPACE", font=font(54), fill="#102A43")
    image.save(path, "PNG")


def create_clip(path: Path, *, index: int, accent: str) -> None:
    # imageio_ffmpeg.write_frames only writes a video stream. Real camera/
    # phone footage always carries an audio track (even if a downstream
    # policy later mutes it), and scripts/media/prepare_remotion_media.py's ffmpeg
    # filter graph unconditionally references an [0:a] stream -- so a
    # video-only synthetic clip fails there with "matches no streams"
    # instead of exercising the real pipeline. Write video-only to a temp
    # path, then mux in a silent track so these clips are representative.
    silent_video = path.with_name(path.stem + ".video-only.mp4")
    writer = imageio_ffmpeg.write_frames(
        str(silent_video),
        (WIDTH, HEIGHT),
        fps=FPS,
        codec="libx264",
        pix_fmt_in="rgb24",
        pix_fmt_out="yuv420p",
        quality=7,
        macro_block_size=16,
        ffmpeg_log_level="error",
    )
    writer.send(None)
    try:
        frames = FPS * 3
        for frame_number in range(frames):
            progress = frame_number / max(frames - 1, 1)
            image = Image.new("RGB", (WIDTH, HEIGHT), "#102A43")
            draw = ImageDraw.Draw(image)
            for y in range(HEIGHT):
                ratio = y / HEIGHT
                draw.line(
                    (0, y, WIDTH, y),
                    fill=(
                        int(12 + 20 * ratio),
                        int(42 + 36 * ratio),
                        int(67 + 55 * ratio),
                    ),
                )
            x = int(80 + progress * 400)
            y = int(390 + math.sin(progress * math.pi * 2) * 120)
            draw.rounded_rectangle((x, y, x + 180, y + 180), radius=32, fill=accent)
            draw.ellipse((180, 780, 540, 1140), outline="#FFFFFF", width=16)
            draw.text((70, 95), "NORTHSTAR", font=font(64), fill="#FFFFFF")
            draw.text((70, 175), f"SYNTHETIC CLIP {index}", font=font(36), fill="#BCCCDC")
            writer.send(image.tobytes())
    finally:
        writer.close()

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(silent_video),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-shortest",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(path),
        ],
        check=True,
    )
    silent_video.unlink()


def create_brief(path: Path) -> None:
    path.write_text(
        """SYNTHETIC TEST DATA — NOT A REAL BUSINESS OR LIVE CAMPAIGN

Business: Northstar Community Studio
Purpose: Promote registrations for a fictional fall open house
Offer: One free introductory class; claim by October 1, 2026
Audience: Adults 25-54 within 10 miles of the fictional venue
Contact: +1 (202) 555-0147
Destination: https://example.test/northstar-open-house
Schedule: September 20, 2026 9:00 AM through October 1, 2026 11:59 PM
Timezone: America/Chicago
Budget: USD 100 lifetime
Form: Synthetic demo form; never collect real submissions
Media permission: Every file in this packet is deterministically generated and
approved for software tests, recordings, and judge review.

Operational boundary: This source is evidence only. It does not authorize ad
creation, publication, activation, budget changes, or any other external write.
""",
        encoding="utf-8",
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    create_logo(OUTPUT / "northstar-demo-logo.png")
    create_photo(OUTPUT / "northstar-demo-photo.png")
    create_clip(OUTPUT / "northstar-demo-clip-01.mp4", index=1, accent="#2CB1BC")
    create_clip(OUTPUT / "northstar-demo-clip-02.mp4", index=2, accent="#F0B429")
    create_clip(OUTPUT / "northstar-demo-clip-03.mp4", index=3, accent="#D64545")
    create_brief(OUTPUT / "campaign-brief.txt")
    print(f"Created synthetic Google Drive demo packet: {OUTPUT}")
    for path in sorted(OUTPUT.glob("*.mp4")):
        reader = imageio_ffmpeg.read_frames(str(path))
        metadata = next(reader)
        reader.close()
        print(
            f"Verified {path.name}: {metadata['size'][0]}x{metadata['size'][1]}, "
            f"{metadata['duration']:.2f}s, {metadata['fps']:.2f} fps"
        )


if __name__ == "__main__":
    main()
