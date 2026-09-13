"""The creative critique pass: measured defects, and the honesty rules around them."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from advantage.application.critique import (
    UNIFORM_TOTAL_LIMIT,
    ImageMeasurements,
    _VisionReview,
    deterministic_findings,
    measure_poster,
    review_creative,
)
from advantage.domain.models import (
    CampaignArtifact,
    CampaignRequest,
    CreativeFormat,
    VerificationResult,
)


def _request() -> CampaignRequest:
    return CampaignRequest(
        business_name="Northstar Cricket Studio",
        brief_text="Youth cricket coaching for ages 5-13.",
        format=CreativeFormat.POSTER,
    )


def _artifact(path: Path) -> CampaignArtifact:
    return CampaignArtifact(
        format=CreativeFormat.POSTER, file_path=str(path), width=1080, height=1350
    )


@pytest.fixture
def empty_poster(tmp_path: Path) -> Path:
    """The reported failure: a photo strip, a flat body band, a flat footer."""
    image = Image.new("RGB", (1080, 1350), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    for x in range(0, 1080, 7):
        draw.rectangle([x, 0, x + 4, 760], fill=(60 + (x // 9) % 150, 90 + (x // 5) % 120, 40))
    draw.rectangle([0, 1000, 1080, 1350], fill="#123C6E")
    path = tmp_path / "empty.png"
    image.save(path)
    return path


@pytest.fixture
def dense_poster(tmp_path: Path) -> Path:
    image = Image.new("RGB", (1080, 1350), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    for y in range(0, 1350, 9):
        for x in range(0, 1080, 9):
            draw.rectangle([x, y, x + 7, y + 7], fill=((x * 3) % 255, (y * 5) % 255, (x + y) % 255))
    path = tmp_path / "dense.png"
    image.save(path)
    return path


class _FakeResponse:
    def __init__(self, parsed):
        self.output_parsed = parsed


class _FakeClient:
    """Minimal stand-in for the OpenAI client's `responses.parse` surface."""

    def __init__(self, parsed):
        self._parsed = parsed
        self.responses = self

    def parse(self, **_kwargs):
        return _FakeResponse(self._parsed)


class _RaisingClient:
    def __init__(self):
        self.responses = self

    def parse(self, **_kwargs):
        raise RuntimeError("upstream exploded")


def test_measures_an_empty_poster_as_mostly_flat_blocks(empty_poster: Path) -> None:
    measurements = measure_poster(empty_poster)

    assert measurements.readable is True
    # The point of `uniform_share`: no single colour dominates this poster, so
    # a "biggest flat colour" metric alone would miss it entirely.
    assert measurements.flat_share < UNIFORM_TOTAL_LIMIT
    assert measurements.uniform_share >= UNIFORM_TOTAL_LIMIT


def test_flags_the_empty_poster_with_the_measured_number(empty_poster: Path) -> None:
    findings = deterministic_findings(_artifact(empty_poster), measure_poster(empty_poster))

    assert findings, "an obviously empty poster must produce a finding"
    assert any("%" in finding for finding in findings), "findings must quote what was measured"


def test_does_not_flag_a_dense_poster(dense_poster: Path) -> None:
    assert deterministic_findings(_artifact(dense_poster), measure_poster(dense_poster)) == []


def test_unreadable_artifact_still_returns_a_critique(tmp_path: Path) -> None:
    missing = tmp_path / "not-here.png"

    critique = review_creative(_artifact(missing), _request())

    assert critique.model_reviewed is False
    assert critique.struggled, "an unreadable poster is itself worth reporting"


def test_model_cannot_suppress_a_measured_defect(empty_poster: Path) -> None:
    """The load-bearing honesty rule: the pixels outrank the model's opinion."""
    flattering = _VisionReview(
        summary="Looks great.", did=["Used a photo"], why=["It suits the brief"], struggled=[]
    )

    critique = review_creative(
        _artifact(empty_poster), _request(), client=_FakeClient(flattering)
    )

    assert critique.model_reviewed is True
    assert critique.struggled, "the measured emptiness must survive a flattering review"


def test_malformed_model_output_falls_back_to_measurements(empty_poster: Path) -> None:
    critique = review_creative(
        _artifact(empty_poster), _request(), client=_FakeClient("not a review object")
    )

    assert critique.model_reviewed is False
    assert critique.struggled


def test_model_failure_never_raises(empty_poster: Path) -> None:
    critique = review_creative(_artifact(empty_poster), _request(), client=_RaisingClient())

    assert critique.model_reviewed is False
    assert critique.struggled


def test_failed_verification_is_carried_into_the_critique(dense_poster: Path) -> None:
    verification = VerificationResult(passed=False, findings=["Poster is 900x900, expected 1080x1350."])

    critique = review_creative(_artifact(dense_poster), _request(), None, verification)

    assert any("900x900" in item for item in critique.struggled)


def test_reel_critique_admits_it_did_not_watch_the_video(tmp_path: Path) -> None:
    reel = CampaignArtifact(
        format=CreativeFormat.REEL,
        file_path=str(tmp_path / "reel.mp4"),
        width=1080,
        height=1920,
        duration_seconds=12.0,
    )

    critique = review_creative(reel, _request())

    assert critique.model_reviewed is False
    assert any("did not" in item.lower() for item in critique.struggled)


def test_reel_gets_no_pixel_findings() -> None:
    reel = CampaignArtifact(
        format=CreativeFormat.REEL, file_path="whatever.mp4", width=1080, height=1920
    )

    assert deterministic_findings(reel, ImageMeasurements(readable=False)) == []


def test_information_lists_what_actually_reached_the_poster(tmp_path: Path) -> None:
    """The owner's "did it use what I gave it?" check.

    Sourced from the renderer's own stamped-copy record, so a field the
    renderer silently dropped cannot show up here as if it had been used.
    """
    from advantage.adapters.poster_ideogram import _stamp

    artwork = tmp_path / "art.png"
    Image.new("RGB", (1080, 1350), "#888888").save(artwork)
    request = CampaignRequest(
        business_name="22 yards",
        brief_text="We are starting our new under 13 academy today",
        format=CreativeFormat.POSTER,
        offer_text="free trial classes ending sept 30",
        contact_phone="5715388147",
        key_benefits=["Small groups", "Build fundamentals", "Play matches when ready"],
        proof_point="Coaches certified by the state association",
    )

    stamped = _stamp(request, artwork, tmp_path / "poster.png")
    critique = review_creative(stamped.artifact, request)

    # Every benefit the owner supplied must be reported as included -- this is
    # the regression that made the earlier poster silently drop all three.
    for benefit in request.key_benefits:
        assert any(benefit in item for item in critique.information)
    assert any("certified" in item for item in critique.information)
