"""Tests for run_campaign(), the single entry point tying the adapters together.

The poster path runs for real (free/local, same reasoning as
test_poster_adapter.py). The reel path is monkeypatched at the orchestrator's
own imported names -- reel_adapter.produce_reel already has its own mocked
subprocess tests; here we only need to prove run_campaign *dispatches*
correctly and assembles the result, not re-test reel rendering.
"""

from __future__ import annotations

import pytest

from advantage import CampaignRequest, CreativeFormat
from advantage.application.orchestrator import OrchestratorError, run_campaign
from advantage.domain.models import CampaignArtifact
from advantage.integrations.google_drive import AssetKind, IntakeAsset, IntakeStatus
from cricket_posts.plates import PlateBank


def _poster_request(**overrides: object) -> CampaignRequest:
    defaults: dict[str, object] = dict(
        business_name="22Yards Houston",
        brief_text="Fall registration is open for junior cricket sessions.",
        format=CreativeFormat.POSTER,
        contact_phone="+1 (713) 498-2155",
        destination_url="https://axon22yards.com/join?location=houston",
        offer_text="New players get a free trial session.",
        audience="Parents of kids 5-13",
        budget_usd=40.0,
        campaign_days=4,
    )
    defaults.update(overrides)
    return CampaignRequest(**defaults)


@pytest.fixture(scope="module", autouse=True)
def _skip_if_no_plates() -> None:
    if not PlateBank.load().entries:
        pytest.skip("plate bank is empty; run `cricket-posts bank plates`")


def test_run_campaign_poster_happy_path(tmp_path):
    request = _poster_request()

    result = run_campaign(request, workdir=tmp_path)

    assert result.artifact.format == CreativeFormat.POSTER
    assert result.verification.passed is True
    assert result.meta_preview is not None
    assert result.meta_preview.creative_format == CreativeFormat.POSTER


def test_run_campaign_without_budget_has_no_meta_preview(tmp_path):
    request = _poster_request(budget_usd=None)

    result = run_campaign(request, workdir=tmp_path)

    assert result.meta_preview is None


def test_run_campaign_reel_without_footage_raises_before_producing_anything(tmp_path):
    request = _poster_request(format=CreativeFormat.REEL, footage_assets=[])

    with pytest.raises(OrchestratorError, match="video clip"):
        run_campaign(request, workdir=tmp_path)


def test_run_campaign_dispatches_reel_requests_to_the_reel_adapter(tmp_path, monkeypatch):
    asset = IntakeAsset(
        source_id="drive-file",
        source_name="clip.mp4",
        source_ref="deadbeef",
        kind=AssetKind.VIDEO,
        mime_type="video/mp4",
        duration_seconds=4.0,
        local_ref="clips/one.mp4",
        status=IntakeStatus.IMPORTED,
    )
    request = _poster_request(format=CreativeFormat.REEL, footage_assets=[asset])

    calls: list[str] = []

    def fake_produce_reel(req, *, workdir):
        calls.append("produce_reel")
        reel_path = workdir / "reel.mp4"
        reel_path.write_bytes(b"fake-mp4-bytes")
        return CampaignArtifact(
            format=CreativeFormat.REEL, file_path=str(reel_path), width=1080, height=1920, duration_seconds=10.0
        )

    def fake_verify_reel(artifact):
        calls.append("verify_reel")
        from advantage.domain.models import VerificationResult

        return VerificationResult(passed=True, findings=[])

    monkeypatch.setattr("advantage.application.orchestrator.produce_reel", fake_produce_reel)
    monkeypatch.setattr("advantage.application.orchestrator.verify_reel", fake_verify_reel)

    result = run_campaign(request, workdir=tmp_path)

    assert calls == ["produce_reel", "verify_reel"]
    assert result.artifact.format == CreativeFormat.REEL
    assert result.verification.passed is True
    assert result.meta_preview is not None
    assert result.meta_preview.creative_format == CreativeFormat.REEL
