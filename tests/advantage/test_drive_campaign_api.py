"""HTTP surface for browsing/importing Google Drive folders on the campaign API.

Mirrors the HTTP-surface tests in test_palette_and_regenerate.py: drives the
real FastAPI app, but every Drive call is mocked or short-circuited before it
would reach the network -- there is no real refresh token in this repo's
`.env`, and these tests must pass without one.
"""

from __future__ import annotations

import pytest

from advantage.integrations.google_drive import DriveFolderRef


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from cricket_posts.web import create_app

    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _no_drive_credentials(monkeypatch):
    """Match this repo's real state: OAuth client configured, no tokens yet."""
    monkeypatch.delenv("GOOGLE_DRIVE_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_ACCESS_TOKEN", raising=False)


def test_drive_folders_returns_503_not_500_without_credentials(client) -> None:
    response = client.get("/api/campaigns/drive/folders")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "google_drive_authorize.py" in detail
    # Never leak anything that looks like a real token value.
    assert "ya29" not in detail


def test_drive_import_returns_503_not_500_without_credentials(client) -> None:
    response = client.post("/api/campaigns/drive/import", json={"folder_id": "abc123folder"})

    assert response.status_code == 503
    assert "google_drive_authorize.py" in response.json()["detail"]


def test_drive_folders_route_is_not_shadowed_by_the_run_id_route(client) -> None:
    """A missing-credentials 503 (not a run-id 404) proves `/drive/folders`
    was matched as a literal route rather than falling through to
    `GET /{run_id}` with run_id="folders"."""
    response = client.get("/api/campaigns/drive/folders")

    assert response.status_code == 503
    assert response.status_code != 404


def test_drive_folders_endpoint_shape_when_authorized(client, monkeypatch) -> None:
    from cricket_posts import campaign_api

    monkeypatch.setattr(campaign_api, "_drive_client", lambda: object())
    monkeypatch.setattr(
        campaign_api,
        "list_campaign_folders",
        lambda client, *, parent_name: [
            DriveFolderRef(id="c1", name="Sept Campaign"),
            DriveFolderRef(id="c2", name="Diwali Push"),
        ],
    )

    response = client.get("/api/campaigns/drive/folders")

    assert response.status_code == 200
    body = response.json()
    assert body == [
        {"id": "c1", "name": "Social Media / Sept Campaign"},
        {"id": "c2", "name": "Social Media / Diwali Push"},
    ]
    # Client-safe: no token, no raw Drive query, no filesystem path.
    serialized = str(body)
    assert "token" not in serialized.lower()


def test_drive_import_endpoint_shape_when_authorized(client, monkeypatch, tmp_path) -> None:
    from advantage.integrations.google_drive import AssetKind, DriveIntakeReceipt, IntakeAsset, IntakeStatus
    from cricket_posts import campaign_api

    fake_receipt = DriveIntakeReceipt(
        folder_ref="ref123",
        assets=[
            IntakeAsset(
                source_id="raw-id-1",
                source_name="clip.mp4",
                source_ref="ref-clip",
                kind=AssetKind.VIDEO,
                mime_type="video/mp4",
                duration_seconds=12.0,
                local_ref=str(tmp_path / "clip.mp4"),
                status=IntakeStatus.IMPORTED,
            ),
            IntakeAsset(
                source_id="raw-id-2",
                source_name="huge.mp4",
                source_ref="ref-huge",
                kind=AssetKind.VIDEO,
                mime_type="video/mp4",
                status=IntakeStatus.SKIPPED,
                reason="file_too_large",
            ),
        ],
    )
    monkeypatch.setattr(campaign_api, "_drive_client", lambda: object())
    monkeypatch.setattr(
        campaign_api, "ingest_drive_folder", lambda client, folder_id, dest, config=None: fake_receipt
    )

    response = client.post("/api/campaigns/drive/import", json={"folder_id": "abc123folder"})

    assert response.status_code == 200
    body = response.json()
    assert body == [
        {
            "source_ref": "ref-clip",
            "name": "clip.mp4",
            "kind": "video",
            "mime_type": "video/mp4",
            "duration_seconds": 12.0,
            "status": "imported",
            "reason": None,
        },
        {
            "source_ref": "ref-huge",
            "name": "huge.mp4",
            "kind": "video",
            "mime_type": "video/mp4",
            "duration_seconds": None,
            "status": "skipped",
            "reason": "file_too_large",
        },
    ]
    serialized = str(body)
    assert str(tmp_path) not in serialized
    assert "raw-id" not in serialized


def test_create_campaign_uses_drive_folder_when_supplied(client, monkeypatch, tmp_path) -> None:
    from advantage.domain.models import CampaignArtifact, CampaignResult, VerificationResult
    from advantage.integrations.google_drive import AssetKind, DriveIntakeReceipt, IntakeAsset, IntakeStatus
    from cricket_posts import campaign_api

    logo_path = tmp_path / "logo.png"
    logo_path.write_bytes(b"logo-bytes")
    clip_path = tmp_path / "clip.mp4"
    clip_path.write_bytes(b"clip-bytes")

    fake_receipt = DriveIntakeReceipt(
        folder_ref="ref123",
        assets=[
            IntakeAsset(
                source_id="raw-logo",
                source_name="logo.png",
                source_ref="ref-logo",
                kind=AssetKind.LOGO,
                mime_type="image/png",
                local_ref=str(logo_path),
                status=IntakeStatus.IMPORTED,
            ),
            IntakeAsset(
                source_id="raw-clip",
                source_name="clip.mp4",
                source_ref="ref-clip",
                kind=AssetKind.VIDEO,
                mime_type="video/mp4",
                duration_seconds=9.0,
                local_ref=str(clip_path),
                status=IntakeStatus.IMPORTED,
            ),
        ],
    )
    monkeypatch.setattr(campaign_api, "_drive_client", lambda: object())
    monkeypatch.setattr(
        campaign_api, "ingest_drive_folder", lambda client, folder_id, dest, config=None: fake_receipt
    )

    captured: dict = {}

    def fake_run_campaign(request, *, workdir):
        captured["request"] = request
        return CampaignResult(
            request=request,
            artifact=CampaignArtifact(
                format=request.format, file_path="poster.png", width=1080, height=1350
            ),
            verification=VerificationResult(passed=True),
        )

    monkeypatch.setattr(campaign_api, "run_campaign", fake_run_campaign)

    response = client.post(
        "/api/campaigns",
        data={
            "business_name": "Northstar",
            "brief_text": "Open house next week.",
            "format": "poster",
            "drive_folder_id": "abc123folder",
        },
    )

    assert response.status_code == 201
    request = captured["request"]
    assert request.logo_asset is not None
    assert request.logo_asset.source_ref == "ref-logo"
    assert [a.source_ref for a in request.footage_assets] == ["ref-clip"]


def test_create_campaign_upload_path_still_works_without_drive_folder_id(
    client, monkeypatch
) -> None:
    """Regression guard: the plain upload path must be untouched."""
    from advantage.domain.models import CampaignArtifact, CampaignResult, VerificationResult
    from cricket_posts import campaign_api

    captured: dict = {}

    def fake_run_campaign(request, *, workdir):
        captured["request"] = request
        return CampaignResult(
            request=request,
            artifact=CampaignArtifact(
                format=request.format, file_path="poster.png", width=1080, height=1350
            ),
            verification=VerificationResult(passed=True),
        )

    monkeypatch.setattr(campaign_api, "run_campaign", fake_run_campaign)

    response = client.post(
        "/api/campaigns",
        data={
            "business_name": "Northstar",
            "brief_text": "Open house next week.",
            "format": "poster",
        },
    )

    assert response.status_code == 201
    request = captured["request"]
    assert request.logo_asset is None
    assert request.footage_assets == []
