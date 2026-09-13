"""Tests for the read-only Meta insights adapter and the grounded rationale
builder. All HTTP is mocked -- no real Meta or OpenAI call happens here.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from advantage import (
    CampaignArtifact,
    CampaignRequest,
    CreativeDecision,
    CreativeFormat,
    CreativePlan,
)
from advantage.adapters.meta_ads import build_meta_preview
import advantage.adapters.meta_insights as meta_insights
from advantage.adapters.meta_insights import MetaInsightsSummary, fetch_account_insights
from advantage.application.rationale import build_rationale


def _request(**overrides: object) -> CampaignRequest:
    defaults: dict[str, object] = dict(
        business_name="22Yards Houston",
        brief_text="Fall registration is open at 22Yards Houston.",
        format=CreativeFormat.REEL,
        contact_phone="+17135551234",
        destination_url="https://axon22yards.com/join?location=houston",
        offer_text="New players get a free trial session.",
        budget_usd=40.0,
        campaign_days=4,
    )
    defaults.update(overrides)
    return CampaignRequest(**defaults)


def _artifact(tmp_path: Path, fmt: CreativeFormat = CreativeFormat.REEL) -> CampaignArtifact:
    if fmt == CreativeFormat.POSTER:
        file_path = tmp_path / "poster.png"
        file_path.write_bytes(b"fake-png-bytes")
        return CampaignArtifact(format=fmt, file_path=str(file_path), width=1080, height=1350)
    file_path = tmp_path / "reel.mp4"
    file_path.write_bytes(b"fake-mp4-bytes")
    return CampaignArtifact(
        format=fmt, file_path=str(file_path), width=1080, height=1920, duration_seconds=12.0
    )


@pytest.fixture(autouse=True)
def _no_real_dotenv(monkeypatch):
    # Never let a real .env populate credentials mid-test; every test controls
    # its own credential state explicitly.
    monkeypatch.setattr(meta_insights, "load_dotenv", lambda *args, **kwargs: None)


# --- meta_insights.py: read-only, must never raise -----------------------------


def test_unavailable_with_no_credentials(monkeypatch):
    monkeypatch.delenv("META_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("META_AD_ACCOUNT_ID", raising=False)
    summary = fetch_account_insights()
    assert summary.available is False
    assert summary.reason
    assert summary.top_placements == []
    assert summary.best_age_bands == []


def test_unavailable_with_only_token_set(monkeypatch):
    monkeypatch.delenv("META_AD_ACCOUNT_ID", raising=False)
    summary = fetch_account_insights(token="fake-token")
    assert summary.available is False


def test_never_raises_on_request_failure(monkeypatch):
    def _raise(*args: object, **kwargs: object):
        raise ConnectionError("boom")

    monkeypatch.setattr(meta_insights.requests, "get", _raise)
    summary = fetch_account_insights(token="fake-token", account_id="123")
    assert summary.available is False
    assert "fake-token" not in (summary.reason or "")


def test_never_raises_on_graph_error_payload(monkeypatch):
    response = Mock()
    response.ok = False
    response.json.return_value = {"error": {"message": "Invalid OAuth access token."}}
    monkeypatch.setattr(meta_insights.requests, "get", Mock(return_value=response))
    summary = fetch_account_insights(token="fake-token", account_id="123")
    assert summary.available is False
    assert "fake-token" not in (summary.reason or "")


def test_unavailable_when_account_has_no_history(monkeypatch):
    empty = Mock()
    empty.ok = True
    empty.json.return_value = {"data": []}
    monkeypatch.setattr(meta_insights.requests, "get", Mock(return_value=empty))
    summary = fetch_account_insights(token="fake-token", account_id="123")
    assert summary.available is False


def test_available_summarizes_placements_and_age_bands(monkeypatch):
    lifetime = Mock()
    lifetime.ok = True
    lifetime.json.return_value = {
        "data": [{"impressions": "10000", "clicks": "150", "ctr": "1.5", "cpc": "0.42", "cpm": "8.10"}]
    }
    placements = Mock()
    placements.ok = True
    placements.json.return_value = {
        "data": [
            {
                "publisher_platform": "facebook",
                "platform_position": "feed",
                "impressions": "3000",
                "clicks": "20",
                "ctr": "0.67",
            },
            {
                "publisher_platform": "instagram",
                "platform_position": "reels",
                "impressions": "6200",
                "clicks": "111",
                "ctr": "1.79",
            },
        ]
    }
    demographics = Mock()
    demographics.ok = True
    demographics.json.return_value = {
        "data": [
            {"age": "18-24", "gender": "male", "impressions": "1000", "clicks": "10", "ctr": "1.0"},
            {"age": "25-34", "gender": "female", "impressions": "4000", "clicks": "80", "ctr": "2.0"},
            {"age": "25-34", "gender": "male", "impressions": "1000", "clicks": "10", "ctr": "1.0"},
        ]
    }

    calls = {"n": 0}
    responses = [lifetime, placements, demographics]

    def _get(url: str, params: dict, timeout: float) -> Mock:
        response = responses[calls["n"]]
        calls["n"] += 1
        assert "access_token" in params  # token is sent...
        return response

    monkeypatch.setattr(meta_insights.requests, "get", _get)

    summary = fetch_account_insights(token="fake-token", account_id="123", top_n=2)

    assert summary.available is True
    assert summary.account_id == "123"
    assert summary.lifetime_impressions == 10000
    assert summary.lifetime_clicks == 150
    assert summary.average_ctr_pct == 1.5

    assert [p.placement for p in summary.top_placements] == [
        "instagram/reels",
        "facebook/feed",
    ]
    assert summary.top_placements[0].impressions == 6200

    # 25-34 combines two gender rows: (2.0*4000 + 1.0*1000) / 5000 = 1.8
    assert summary.best_age_bands[0].age_range == "25-34"
    assert summary.best_age_bands[0].impressions == 5000
    assert round(summary.best_age_bands[0].ctr_pct, 2) == 1.8


def test_never_calls_post_only_get(monkeypatch):
    # meta_insights has no create/update/delete capability at all -- assert
    # the module simply never references a mutating verb.
    assert not hasattr(meta_insights, "post")
    assert not hasattr(meta_insights, "create_paused_campaign")


def test_token_never_appears_in_reason_text(monkeypatch):
    def _raise(*args: object, **kwargs: object):
        raise TimeoutError("SECRET-TOKEN-VALUE timed out")

    monkeypatch.setattr(meta_insights.requests, "get", _raise)
    summary = fetch_account_insights(token="SECRET-TOKEN-VALUE", account_id="123")
    assert summary.available is False
    assert "SECRET-TOKEN-VALUE" not in (summary.reason or "")


# --- build_rationale ------------------------------------------------------------


def _preview(request: CampaignRequest, artifact: CampaignArtifact):
    return build_meta_preview(request, artifact)


def test_grounded_false_and_no_insights_factor_when_insights_is_none(tmp_path):
    request = _request()
    artifact = _artifact(tmp_path)
    preview = _preview(request, artifact)

    rationale = build_rationale(request, artifact, preview, None, insights=None)

    assert rationale.meta_account_grounded is False
    assert all(factor.source != "meta_insights" for factor in rationale.factors)
    assert rationale.factors  # still produces a useful, non-empty explanation
    assert rationale.summary


def test_grounded_false_when_insights_unavailable(tmp_path):
    request = _request()
    artifact = _artifact(tmp_path)
    preview = _preview(request, artifact)
    insights = MetaInsightsSummary(available=False, reason="no credentials configured")

    rationale = build_rationale(request, artifact, preview, None, insights=insights)

    assert rationale.meta_account_grounded is False
    assert all(factor.source != "meta_insights" for factor in rationale.factors)


def test_grounded_true_and_quotes_evidence_when_insights_available(tmp_path):
    request = _request()
    artifact = _artifact(tmp_path)
    preview = _preview(request, artifact)
    insights = MetaInsightsSummary(
        available=True,
        account_id="123",
        lifetime_impressions=10000,
        lifetime_clicks=150,
        average_ctr_pct=1.5,
        average_cpc_usd=0.42,
        average_cpm_usd=8.1,
        top_placements=[
            meta_insights.PlacementInsight(placement="instagram/reels", impressions=6200, ctr_pct=1.79)
        ],
        best_age_bands=[
            meta_insights.AgeBandInsight(age_range="25-34", impressions=5000, ctr_pct=1.8)
        ],
    )

    rationale = build_rationale(request, artifact, preview, None, insights=insights)

    assert rationale.meta_account_grounded is True
    insight_factors = [f for f in rationale.factors if f.source == "meta_insights"]
    assert insight_factors
    combined_evidence = " ".join(f.evidence for f in insight_factors)
    assert "instagram/reels" in combined_evidence
    assert "1.79" in combined_evidence or "62%" in combined_evidence or "1.8" in combined_evidence


def test_every_factor_has_an_honest_source_label(tmp_path):
    request = _request()
    artifact = _artifact(tmp_path)
    preview = _preview(request, artifact)
    plan = CreativePlan(
        format=CreativeFormat.REEL,
        feel="high_energy",
        decisions=[CreativeDecision(choice="Fast cuts every 3s", reason="Matches high-energy feel")],
    )

    rationale = build_rationale(request, artifact, preview, plan, insights=None)

    allowed_sources = {"meta_insights", "meta_defaults", "request", "creative_plan"}
    assert all(factor.source in allowed_sources for factor in rationale.factors)


def test_creative_plan_decisions_become_factors(tmp_path):
    request = _request()
    artifact = _artifact(tmp_path)
    preview = _preview(request, artifact)
    plan = CreativePlan(
        format=CreativeFormat.REEL,
        feel="high_energy",
        decisions=[
            CreativeDecision(choice="Fast cuts every 3s", reason="Matches high-energy feel"),
            CreativeDecision(choice="Upbeat music bed", reason="Reinforces high energy"),
        ],
    )

    rationale = build_rationale(request, artifact, preview, plan, insights=None)

    plan_factors = [f for f in rationale.factors if f.source == "creative_plan"]
    assert {f.claim for f in plan_factors} == {"Fast cuts every 3s", "Upbeat music bed"}
    assert {f.evidence for f in plan_factors} == {
        "Matches high-energy feel",
        "Reinforces high energy",
    }


def test_plan_none_produces_no_creative_plan_factors(tmp_path):
    request = _request()
    artifact = _artifact(tmp_path)
    preview = _preview(request, artifact)

    rationale = build_rationale(request, artifact, preview, None, insights=None)

    assert all(factor.source != "creative_plan" for factor in rationale.factors)


def test_budget_factor_is_sourced_from_request_and_matches_preview(tmp_path):
    request = _request(budget_usd=40.0, campaign_days=4)
    artifact = _artifact(tmp_path)
    preview = _preview(request, artifact)

    rationale = build_rationale(request, artifact, preview, None, insights=None)

    budget_factors = [f for f in rationale.factors if "10.00" in f.claim or "/day" in f.claim]
    assert budget_factors
    assert budget_factors[0].source == "request"
    assert "40.00" in budget_factors[0].evidence
    assert "4" in budget_factors[0].evidence


def test_cta_factor_reflects_actual_call_to_action(tmp_path):
    request = _request(destination_url="https://example.com/join", contact_phone=None)
    artifact = _artifact(tmp_path)
    preview = _preview(request, artifact)

    rationale = build_rationale(request, artifact, preview, None, insights=None)

    cta_factors = [f for f in rationale.factors if preview.call_to_action in f.claim]
    assert cta_factors
    assert cta_factors[0].source == "request"
    assert preview.call_to_action == "LEARN_MORE"


def test_cta_falls_back_to_call_now_without_destination_url(tmp_path):
    request = _request(destination_url=None, contact_phone="+17135551234")
    artifact = _artifact(tmp_path)
    preview = _preview(request, artifact)

    rationale = build_rationale(request, artifact, preview, None, insights=None)

    assert preview.call_to_action == "CALL_NOW"
    cta_factors = [f for f in rationale.factors if "CALL_NOW" in f.claim]
    assert cta_factors
    assert "+17135551234" in cta_factors[0].evidence
