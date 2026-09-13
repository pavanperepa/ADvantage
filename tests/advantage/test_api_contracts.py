from datetime import datetime

import pytest
from pydantic import ValidationError

from advantage.api import (
    ApprovalBinding,
    AssetSelection,
    CampaignBudget,
    CampaignDraftRequest,
    CampaignSchedule,
    MediaPermissions,
    PausedCampaignCreateRequest,
    export_contract_schema,
)
from advantage.domain.models import CampaignRequest, CreativeFormat
from advantage.integrations.google_drive import AssetKind, IntakeAsset, IntakeStatus


SHA = "A" * 64


def _schedule() -> CampaignSchedule:
    return CampaignSchedule(
        starts_at=datetime.fromisoformat("2026-09-20T09:00:00-05:00"),
        ends_at=datetime.fromisoformat("2026-10-01T23:59:00-05:00"),
        timezone="America/Chicago",
    )


def _permissions() -> MediaPermissions:
    return MediaPermissions(supplied_media_approved=True, likeness_use_approved=True)


def test_campaign_request_with_assets_round_trips_without_private_drive_fields():
    asset = IntakeAsset(
        source_id="raw-provider-id",
        source_name="private-name.mp4",
        source_ref="safe-ref-123",
        kind=AssetKind.VIDEO,
        mime_type="video/mp4",
        sha256=SHA,
        local_ref="output/intakes/safe-ref-123.mp4",
        status=IntakeStatus.IMPORTED,
    )
    request = CampaignRequest(
        business_name="Northstar Community Studio",
        brief_text="Create an open-house reel.",
        format=CreativeFormat.REEL,
        footage_assets=[asset],
    )

    serialized = request.model_dump_json()
    restored = CampaignRequest.model_validate_json(serialized)

    assert restored == request.model_copy(
        update={
            "footage_assets": [
                asset.model_copy(update={"source_id": "", "source_name": ""})
            ]
        }
    )
    assert "raw-provider-id" not in serialized
    assert "private-name.mp4" not in serialized


def test_public_campaign_contract_accepts_complete_reel_request():
    request = CampaignDraftRequest(
        business_name="Northstar Community Studio",
        brief_text="Promote registrations for our fall open house.",
        creative_format=CreativeFormat.REEL,
        contact_phone="+1 (202) 555-0147",
        destination_url="https://northstar.example/open-house",
        offer_text="One free introductory class",
        offer_expires_at=datetime.fromisoformat("2026-10-01T23:59:00-05:00"),
        audience="Adults 25-54 within 10 miles",
        location="Chicago, Illinois",
        schedule=_schedule(),
        budget=CampaignBudget(total_amount="100.00"),
        page_ref="page-safe-ref",
        destination_form_ref="form-safe-ref",
        permissions=_permissions(),
        assets=[AssetSelection(source_ref="safe-ref-123", kind=AssetKind.VIDEO, sha256=SHA)],
    )

    assert request.camera_audio_policy.value == "mute"
    assert request.budget and request.budget.currency == "USD"


def test_public_campaign_contract_rejects_reserved_demo_destination():
    with pytest.raises(ValidationError, match="reserved .test"):
        CampaignDraftRequest(
            business_name="Northstar",
            brief_text="Create a poster.",
            creative_format=CreativeFormat.POSTER,
            destination_url="https://example.test/not-live",
            permissions=_permissions(),
        )


def test_public_campaign_contract_requires_offer_expiry():
    with pytest.raises(ValidationError, match="offer_expires_at"):
        CampaignDraftRequest(
            business_name="Northstar",
            brief_text="Create a poster.",
            creative_format=CreativeFormat.POSTER,
            offer_text="One free class",
            permissions=_permissions(),
        )


def test_public_campaign_contract_requires_video_for_reel():
    with pytest.raises(ValidationError, match="video asset"):
        CampaignDraftRequest(
            business_name="Northstar",
            brief_text="Create a reel.",
            creative_format=CreativeFormat.REEL,
            permissions=_permissions(),
        )


def test_paused_create_contract_binds_exact_reviewed_hashes():
    payload = PausedCampaignCreateRequest(
        run_id="run-123",
        approval=ApprovalBinding(
            manifest_sha256=SHA,
            artifact_sha256="B" * 64,
            payload_sha256="C" * 64,
            approved_at=datetime.fromisoformat("2026-09-13T12:00:00-05:00"),
            approved_by="owner@example.com",
        ),
        confirmation="CREATE_PAUSED",
    )

    assert payload.confirmation == "CREATE_PAUSED"


def test_exported_public_schema_has_no_secret_or_filesystem_fields():
    schema = export_contract_schema()
    serialized = str(schema).lower()

    assert schema["contract_version"] == "1.0"
    assert "campaignDraftRequest".lower() in serialized
    assert "access_token" not in serialized
    assert "source_id" not in serialized
    assert "source_name" not in serialized
    assert "local_ref" not in serialized
