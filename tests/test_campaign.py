import pytest
from pydantic import ValidationError

from cricket_posts.campaign import CampaignRequest, CreativeFormat
from cricket_posts.drive_intake import AssetKind, IntakeAsset, IntakeStatus


def _asset(kind: AssetKind) -> IntakeAsset:
    return IntakeAsset(
        source_id="file-1",
        source_name="clip.mp4",
        source_ref="abc123",
        kind=kind,
        mime_type="video/mp4" if kind == AssetKind.VIDEO else "image/png",
        status=IntakeStatus.IMPORTED,
    )


def test_poster_request_without_logo_warns_but_is_not_blocked():
    request = CampaignRequest(
        business_name="22Yards Houston",
        brief_text="Fall registration is open, first session free.",
        format=CreativeFormat.POSTER,
    )
    assert request.blockers() == []
    assert "logo" in request.warnings()[0].lower()


def test_reel_request_without_footage_is_blocked():
    request = CampaignRequest(
        business_name="22Yards Houston",
        brief_text="Show a practice match clip.",
        format=CreativeFormat.REEL,
    )
    assert request.blockers() == ["Select at least one video clip for a reel."]


def test_reel_request_with_footage_has_no_blockers():
    request = CampaignRequest(
        business_name="22Yards Houston",
        brief_text="Show a practice match clip.",
        format=CreativeFormat.REEL,
        footage_assets=[_asset(AssetKind.VIDEO)],
    )
    assert request.blockers() == []


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        CampaignRequest(
            business_name="22Yards Houston",
            brief_text="brief",
            format=CreativeFormat.POSTER,
            unexpected_field="nope",
        )


def test_round_trip_serialization():
    request = CampaignRequest(
        business_name="22Yards Houston",
        brief_text="Fall registration is open.",
        format=CreativeFormat.POSTER,
        budget_usd=25.0,
        campaign_days=14,
    )
    restored = CampaignRequest.model_validate_json(request.model_dump_json())
    assert restored == request
