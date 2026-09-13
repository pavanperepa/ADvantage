"""Basic tests for src/cricket_posts/reel_adapter.py.

Nothing here touches a real subprocess, Node.js, ffmpeg, or a live API --
`subprocess.run` (and the ffmpeg-based dimension/duration probe) are always
monkeypatched.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cricket_posts import reel_adapter
from cricket_posts.campaign import CampaignRequest, CreativeFormat, CampaignArtifact
from cricket_posts.drive_intake import AssetKind, IntakeAsset, IntakeStatus


def _asset(local_ref: str | None = "clips/one.mp4", duration_seconds: float | None = 4.0) -> IntakeAsset:
    return IntakeAsset(
        source_id="drive-file-id",
        source_name="clip.mp4",
        source_ref="deadbeefcafef00d",
        kind=AssetKind.VIDEO,
        mime_type="video/mp4",
        duration_seconds=duration_seconds,
        local_ref=local_ref,
        status=IntakeStatus.IMPORTED,
    )


def _request(**overrides) -> CampaignRequest:
    fields = {
        "business_name": "22 Yards Cricket Academy",
        "brief_text": "Turn our practice footage into a reel",
        "format": CreativeFormat.REEL,
        "contact_phone": "+1 (713) 498-2155",
        "destination_url": "https://axon22yards.com/join?location=houston",
        "offer_text": "Free trial class",
        "footage_assets": [_asset()],
    }
    fields.update(overrides)
    return CampaignRequest(**fields)


# --- build_edit_spec: pure EditSpec-building logic -------------------------


def test_build_edit_spec_single_clip():
    request = _request(footage_assets=[_asset(local_ref="clips/one.mp4", duration_seconds=5.0)])

    spec = reel_adapter.build_edit_spec(request)

    assert spec["canvas"] == {"width": 1080, "height": 1920, "fps": 30}
    assert len(spec["shots"]) == 1
    shot = spec["shots"][0]
    assert shot["source"] == "clips/one.mp4"
    assert shot["timelineStart"] == 0.0
    assert shot["duration"] == 5.0  # within the 3-6s band, so left as-is
    assert shot["media"].startswith("media/reel-adapter-22-yards-cricket-academy/")

    assert spec["brand"]["academy"] == "22 YARDS CRICKET ACADEMY"
    assert spec["brand"]["phone"] == "+1 (713) 498-2155"
    assert spec["brand"]["registrationUrl"] == "https://axon22yards.com/join?location=houston"

    assert len(spec["overlays"]) == 1
    overlay = spec["overlays"][0]
    assert overlay["type"] == "closing"
    assert overlay["headline"] == "FREE TRIAL CLASS"
    # Overlay rides over the (only, so also last) shot.
    assert overlay["start"] == shot["timelineStart"]
    assert overlay["duration"] == shot["duration"]


def test_build_edit_spec_multiple_clips_are_straight_cut_and_clamped():
    request = _request(
        footage_assets=[
            _asset(local_ref="clips/short.mp4", duration_seconds=2.0),  # below MIN -> kept as-is
            _asset(local_ref="clips/long.mp4", duration_seconds=10.0),  # above MAX -> clamped to 6s
            _asset(local_ref="clips/unknown.mp4", duration_seconds=None),  # falls back to default
        ]
    )

    spec = reel_adapter.build_edit_spec(request)

    assert len(spec["shots"]) == 3
    durations = [shot["duration"] for shot in spec["shots"]]
    assert durations == [2.0, 6.0, 4.0]

    # Straight cuts: each shot starts exactly where the previous one ends, no overlap.
    starts = [shot["timelineStart"] for shot in spec["shots"]]
    assert starts == [0.0, 2.0, 8.0]
    for shot in spec["shots"]:
        assert shot["motion"] == "none"
        assert shot["transition"] == "none"

    # Media paths are unique per shot.
    media_paths = [shot["media"] for shot in spec["shots"]]
    assert len(set(media_paths)) == 3

    # Closing overlay rides over the last shot only.
    last_shot = spec["shots"][-1]
    overlay = spec["overlays"][0]
    assert overlay["start"] == last_shot["timelineStart"]
    assert overlay["duration"] == last_shot["duration"]


def test_build_edit_spec_empty_footage_raises_clear_blocker():
    request = _request(footage_assets=[])

    with pytest.raises(reel_adapter.ReelAdapterError, match="video clip"):
        reel_adapter.build_edit_spec(request)


def test_build_edit_spec_wrong_format_raises():
    request = _request(format=CreativeFormat.POSTER, footage_assets=[])

    with pytest.raises(reel_adapter.ReelAdapterError, match="REEL"):
        reel_adapter.build_edit_spec(request)


# --- produce_reel: subprocess orchestration (all subprocesses mocked) ------


def test_produce_reel_runs_expected_subprocesses_in_order(tmp_path, monkeypatch):
    request = _request(
        footage_assets=[
            _asset(local_ref="clips/one.mp4", duration_seconds=4.0),
            _asset(local_ref="clips/two.mp4", duration_seconds=4.0),
        ]
    )

    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append([str(part) for part in command])
        if "prepare_remotion_media.py" in str(command[1]):
            return subprocess.CompletedProcess(command, 0, stdout="prepared", stderr="")
        # Remotion render call: simulate the renderer writing the output file.
        output_path = Path(command[5])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-mp4-bytes")
        return subprocess.CompletedProcess(command, 0, stdout="rendered", stderr="")

    monkeypatch.setattr(reel_adapter.subprocess, "run", fake_run)
    monkeypatch.setattr(reel_adapter, "_probe_video", lambda path: (1080, 1920, 12.5))
    monkeypatch.setattr(reel_adapter.shutil, "which", lambda name: "C:/nodejs/node.exe")

    artifact = reel_adapter.produce_reel(request, workdir=tmp_path)

    assert isinstance(artifact, CampaignArtifact)
    assert artifact.format == CreativeFormat.REEL
    assert artifact.width == 1080
    assert artifact.height == 1920
    assert artifact.duration_seconds == 12.5
    assert Path(artifact.file_path).exists()

    # Exactly two subprocess calls, in the documented order.
    assert len(calls) == 2
    prepare_call, render_call = calls
    assert "prepare_remotion_media.py" in prepare_call[1]
    assert prepare_call[2].endswith("editspec.json")
    assert "--force" in prepare_call

    assert render_call[0] == "C:/nodejs/node.exe"
    assert "remotion-cli.js" in render_call[1]
    assert render_call[2] == "render"
    assert render_call[4] == reel_adapter.REEL_COMPOSITION_ID
    assert render_call[5].endswith("reel.mp4")
    assert any(part.startswith("--props=") and part.endswith("props.json") for part in render_call)

    # The EditSpec and Remotion props files were both written under workdir.
    assert (tmp_path / "editspec.json").exists()
    assert (tmp_path / "props.json").exists()


def test_produce_reel_raises_on_subprocess_failure(tmp_path, monkeypatch):
    request = _request()

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command, 1, stdout="", stderr="ffmpeg: No such filter: 'bogus'"
        )

    monkeypatch.setattr(reel_adapter.subprocess, "run", fake_run)

    with pytest.raises(reel_adapter.ReelAdapterError, match="ffmpeg: No such filter"):
        reel_adapter.produce_reel(request, workdir=tmp_path)
