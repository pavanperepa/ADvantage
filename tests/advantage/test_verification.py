"""Tests for the single verification pass (poster + reel).

Poster cases reuse a real, already-composed ComposeResult (via poster_adapter,
same as test_poster_adapter.py -- this pipeline is free/local, so there is no
reason to hand-build a fake ComposeResult's many nested dataclasses) and only
`dataclasses.replace()` the one field each case is about. Reel cases need no
real render at all: verify_reel reads a plain CampaignArtifact and a file on
disk, so a tiny fake file is enough.
"""

from __future__ import annotations

import dataclasses

import pytest

from advantage import CampaignRequest, CreativeFormat
from advantage.adapters.poster import produce_poster
from advantage.application.verification import verify_poster, verify_reel
from advantage.domain.models import CampaignArtifact
from cricket_posts.plates import PlateBank


def _request() -> CampaignRequest:
    return CampaignRequest(
        business_name="22Yards Houston",
        brief_text="Fall registration is open for junior cricket sessions.",
        format=CreativeFormat.POSTER,
        contact_phone="+1 (713) 498-2155",
        destination_url="https://axon22yards.com/join?location=houston",
        offer_text="New players get a free trial session.",
        audience="Parents of kids 5-13",
    )


@pytest.fixture(scope="module", autouse=True)
def _skip_if_no_plates() -> None:
    if not PlateBank.load().entries:
        pytest.skip("plate bank is empty; run `cricket-posts bank plates`")


@pytest.fixture(scope="module")
def clean_compose_result(tmp_path_factory):
    workdir = tmp_path_factory.mktemp("verify-poster")
    # These tests are about the compose path's audit data, so ask for it
    # explicitly rather than depending on IDEOGRAM_API_KEY being absent --
    # the Ideogram path returns no ComposeResult at all.
    _, compose_result = produce_poster(_request(), workdir=workdir, allow_ideogram=False)
    return compose_result


# --- poster ------------------------------------------------------------


def test_verify_poster_passes_for_a_clean_render(clean_compose_result):
    artifact = CampaignArtifact(format=CreativeFormat.POSTER, file_path="poster.png", width=1080, height=1350)

    result = verify_poster(artifact, clean_compose_result)

    assert result.passed is True
    assert result.findings == []


def test_verify_poster_flags_missing_copy(clean_compose_result):
    artifact = CampaignArtifact(format=CreativeFormat.POSTER, file_path="poster.png", width=1080, height=1350)
    broken = dataclasses.replace(clean_compose_result, missing_copy=["+1 (713) 498-2155"])

    result = verify_poster(artifact, broken)

    assert result.passed is False
    assert any("missing" in finding.lower() for finding in result.findings)


def test_verify_poster_flags_clipped_copy(clean_compose_result):
    artifact = CampaignArtifact(format=CreativeFormat.POSTER, file_path="poster.png", width=1080, height=1350)
    broken = dataclasses.replace(clean_compose_result, clipped_copy=["New players get a free trial session."])

    result = verify_poster(artifact, broken)

    assert result.passed is False
    assert any("clipped" in finding.lower() for finding in result.findings)


def test_verify_poster_flags_wrong_dimensions(clean_compose_result):
    artifact = CampaignArtifact(format=CreativeFormat.POSTER, file_path="poster.png", width=1080, height=1080)

    result = verify_poster(artifact, clean_compose_result)

    assert result.passed is False
    assert any("1080x1080" in finding for finding in result.findings)


# --- reel ----------------------------------------------------------------


def test_verify_reel_passes_for_a_valid_artifact(tmp_path):
    reel_path = tmp_path / "reel.mp4"
    reel_path.write_bytes(b"fake-mp4-bytes")
    artifact = CampaignArtifact(
        format=CreativeFormat.REEL, file_path=str(reel_path), width=1080, height=1920, duration_seconds=12.0
    )

    result = verify_reel(artifact)

    assert result.passed is True
    assert result.findings == []


def test_verify_reel_flags_missing_file(tmp_path):
    artifact = CampaignArtifact(
        format=CreativeFormat.REEL,
        file_path=str(tmp_path / "does-not-exist.mp4"),
        width=1080,
        height=1920,
        duration_seconds=12.0,
    )

    result = verify_reel(artifact)

    assert result.passed is False
    assert any("missing" in finding.lower() for finding in result.findings)


def test_verify_reel_flags_wrong_dimensions_and_bad_duration(tmp_path):
    reel_path = tmp_path / "reel.mp4"
    reel_path.write_bytes(b"fake-mp4-bytes")
    artifact = CampaignArtifact(
        format=CreativeFormat.REEL, file_path=str(reel_path), width=720, height=1280, duration_seconds=0.0
    )

    result = verify_reel(artifact)

    assert result.passed is False
    assert len(result.findings) == 2
