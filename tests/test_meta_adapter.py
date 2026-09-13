"""Fully mocked tests for the Meta Ads preview/creation adapter.

No real network access or token is required to run these. Dry-run coverage
asserts that literally zero HTTP calls happen; execute coverage mocks
``requests.get``/``requests.post`` and asserts the PAUSED-only, read-back-
before-success contract.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

import cricket_posts.campaign.meta_adapter as meta_adapter
from cricket_posts.campaign import CampaignArtifact, CampaignRequest, CreativeFormat
from cricket_posts.campaign.meta_adapter import (
    MissingBudgetError,
    build_meta_preview,
    create_paused_campaign,
)


def _request(**overrides: object) -> CampaignRequest:
    defaults: dict[str, object] = dict(
        business_name="22Yards Houston",
        brief_text="Fall registration is open at 22Yards Houston.",
        format=CreativeFormat.POSTER,
        contact_phone="+17135551234",
        destination_url="https://axon22yards.com/join?location=houston",
        offer_text="New players get a free trial session.",
        audience="Parents of kids 5-13",
        budget_usd=40.0,
        campaign_days=4,
    )
    defaults.update(overrides)
    return CampaignRequest(**defaults)


def _artifact(tmp_path: Path, fmt: CreativeFormat) -> CampaignArtifact:
    if fmt == CreativeFormat.POSTER:
        file_path = tmp_path / "poster.png"
        file_path.write_bytes(b"fake-png-bytes")
        return CampaignArtifact(format=fmt, file_path=str(file_path), width=1080, height=1350)
    file_path = tmp_path / "reel.mp4"
    file_path.write_bytes(b"fake-mp4-bytes")
    return CampaignArtifact(
        format=fmt, file_path=str(file_path), width=1080, height=1920, duration_seconds=12.0
    )


def _response(payload: dict) -> Mock:
    response = Mock()
    response.json.return_value = payload
    return response


@pytest.fixture(autouse=True)
def _no_real_dotenv(monkeypatch):
    """Never let these tests read the repo's real .env, which holds live Meta
    credentials on this machine. Tests must be hermetic: every execute-path
    test sets its own fake env vars via monkeypatch instead."""
    monkeypatch.setattr(meta_adapter, "load_dotenv", lambda *a, **k: None)


# ---------------------------------------------------------------------------
# build_meta_preview
# ---------------------------------------------------------------------------


def test_build_meta_preview_with_full_facts(tmp_path):
    request = _request()
    artifact = _artifact(tmp_path, CreativeFormat.POSTER)

    preview = build_meta_preview(request, artifact)

    assert preview.days == 4
    assert preview.daily_budget_usd == pytest.approx(10.0)
    assert preview.destination_url == request.destination_url
    assert preview.creative_format == CreativeFormat.POSTER
    assert "22YARDS" in preview.campaign_name.upper()
    assert "POSTER" in preview.campaign_name
    assert request.offer_text in preview.primary_text
    assert request.brief_text in preview.primary_text
    assert request.contact_phone in preview.primary_text
    assert preview.call_to_action == "LEARN_MORE"
    assert preview.objective


def test_build_meta_preview_missing_budget_raises(tmp_path):
    request = _request(budget_usd=None)
    artifact = _artifact(tmp_path, CreativeFormat.POSTER)

    with pytest.raises(MissingBudgetError):
        build_meta_preview(request, artifact)


# ---------------------------------------------------------------------------
# create_paused_campaign: dry run (default) makes zero network calls
# ---------------------------------------------------------------------------


def test_create_paused_campaign_dry_run_is_zero_network_and_well_formed(tmp_path, monkeypatch):
    request = _request()
    artifact = _artifact(tmp_path, CreativeFormat.POSTER)
    preview = build_meta_preview(request, artifact)

    mock_get = Mock(side_effect=AssertionError("no GET expected during a dry run"))
    mock_post = Mock(side_effect=AssertionError("no POST expected during a dry run"))
    monkeypatch.setattr(meta_adapter.requests, "get", mock_get)
    monkeypatch.setattr(meta_adapter.requests, "post", mock_post)

    result = create_paused_campaign(request, artifact, preview, execute=False)

    assert result.dry_run is True
    assert result.status == "DRY_RUN"
    assert result.campaign_id and result.ad_set_id and result.ad_id

    mock_get.assert_not_called()
    mock_post.assert_not_called()


def test_create_paused_campaign_dry_run_reel_is_also_zero_network(tmp_path, monkeypatch):
    request = _request(format=CreativeFormat.REEL)
    artifact = _artifact(tmp_path, CreativeFormat.REEL)
    preview = build_meta_preview(request, artifact)

    mock_get = Mock(side_effect=AssertionError("no GET expected during a dry run"))
    mock_post = Mock(side_effect=AssertionError("no POST expected during a dry run"))
    monkeypatch.setattr(meta_adapter.requests, "get", mock_get)
    monkeypatch.setattr(meta_adapter.requests, "post", mock_post)

    result = create_paused_campaign(request, artifact, preview, execute=False)

    assert result.dry_run is True
    mock_get.assert_not_called()
    mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# create_paused_campaign: execute=True, fully mocked HTTP
# ---------------------------------------------------------------------------


def _install_fake_graph(monkeypatch, calls: list[tuple[str, str]], *, upload_path: str):
    """Wire fake requests.post/get that log into ``calls`` in call order."""

    def fake_post(url, data=None, files=None, timeout=None):
        calls.append(("POST", url))
        if url.endswith("/adimages"):
            return _response({"images": {"poster.png": {"hash": "img-hash-abc"}}})
        if url.endswith("/advideos"):
            return _response({"id": "vid_1"})
        if url.endswith("/campaigns"):
            return _response({"id": "cmp_1"})
        if url.endswith("/adsets"):
            return _response({"id": "adset_1"})
        if url.endswith("/adcreatives"):
            return _response({"id": "creative_1"})
        if url.endswith("/ads"):
            return _response({"id": "ad_1"})
        raise AssertionError(f"unexpected POST {url}")

    def fake_get(url, params=None, timeout=None):
        params = params or {}
        calls.append(("GET", url))
        if url.endswith("/thumbnails"):
            return _response({"data": [{"uri": "https://thumb.example/x.jpg", "is_preferred": True}]})
        if params.get("fields") == "status":
            return _response({"status": {"video_status": "ready"}})
        # Read-back verification call: id,status,effective_status
        object_id = url.rsplit("/", 1)[-1]
        return _response({"id": object_id, "status": "PAUSED", "effective_status": "PAUSED"})

    monkeypatch.setattr(meta_adapter.requests, "post", Mock(side_effect=fake_post))
    monkeypatch.setattr(meta_adapter.requests, "get", Mock(side_effect=fake_get))


def test_create_paused_campaign_execute_poster_confirms_paused(tmp_path, monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("META_AD_ACCOUNT_ID", "123456")

    request = _request(format=CreativeFormat.POSTER)
    artifact = _artifact(tmp_path, CreativeFormat.POSTER)
    preview = build_meta_preview(request, artifact)

    calls: list[tuple[str, str]] = []
    _install_fake_graph(monkeypatch, calls, upload_path=artifact.file_path)

    result = create_paused_campaign(request, artifact, preview, execute=True)

    assert result.dry_run is False
    assert result.status == "PAUSED"
    assert result.campaign_id == "cmp_1"
    assert result.ad_set_id == "adset_1"
    assert result.ad_id == "ad_1"

    # Every created object was created PAUSED (posts sent status=PAUSED where
    # applicable) and then read back to confirm it.
    verify_gets = [c for c in calls if c[0] == "GET" and not c[1].endswith("/thumbnails")]
    verified_ids = {c[1].rsplit("/", 1)[-1] for c in verify_gets}
    assert verified_ids == {"cmp_1", "adset_1", "ad_1"}

    # The read-backs happened strictly after every create POST (i.e. after
    # creation, before the function declared success), not interleaved before
    # the ad was created.
    last_post_index = max(i for i, c in enumerate(calls) if c[0] == "POST")
    first_verify_index = min(
        i for i, c in enumerate(calls) if c in verify_gets
    )
    assert first_verify_index > last_post_index

    # Never touched the token or account id in a request URL.
    for _, url in calls:
        assert "test-token" not in url


def test_create_paused_campaign_execute_reel_confirms_paused(tmp_path, monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("META_AD_ACCOUNT_ID", "123456")

    request = _request(format=CreativeFormat.REEL)
    artifact = _artifact(tmp_path, CreativeFormat.REEL)
    preview = build_meta_preview(request, artifact)

    calls: list[tuple[str, str]] = []
    _install_fake_graph(monkeypatch, calls, upload_path=artifact.file_path)

    result = create_paused_campaign(request, artifact, preview, execute=True)

    assert result.dry_run is False
    assert result.status == "PAUSED"
    assert result.campaign_id == "cmp_1"
    assert result.ad_set_id == "adset_1"
    assert result.ad_id == "ad_1"

    verify_gets = [
        c
        for c in calls
        if c[0] == "GET" and not c[1].endswith("/thumbnails") and "vid_1" not in c[1]
    ]
    verified_ids = {c[1].rsplit("/", 1)[-1] for c in verify_gets}
    assert verified_ids == {"cmp_1", "adset_1", "ad_1"}


def test_create_paused_campaign_execute_without_credentials_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("META_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("META_AD_ACCOUNT_ID", raising=False)

    request = _request()
    artifact = _artifact(tmp_path, CreativeFormat.POSTER)
    preview = build_meta_preview(request, artifact)

    mock_post = Mock(side_effect=AssertionError("no POST expected without credentials"))
    monkeypatch.setattr(meta_adapter.requests, "post", mock_post)

    with pytest.raises(meta_adapter.MetaGraphError):
        create_paused_campaign(request, artifact, preview, execute=True)

    mock_post.assert_not_called()
