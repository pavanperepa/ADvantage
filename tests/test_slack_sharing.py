from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cricket_posts import campaign_api
from cricket_posts.campaign import (
    CampaignArtifact,
    CampaignRequest,
    CampaignResult,
    CreativeFormat,
    VerificationResult,
)
from cricket_posts.slack_sharing import (
    SlackChannel,
    SlackNotConfiguredError,
    SlackShareReceipt,
    SlackSharingService,
)
from cricket_posts.studio import PosterStudio
from cricket_posts.web import create_app


class FakeSlackClient:
    def __init__(self) -> None:
        self.list_calls: list[dict] = []
        self.upload_call: dict | None = None

    def conversations_list(self, **kwargs):
        self.list_calls.append(kwargs)
        if kwargs["cursor"] is None:
            return {
                "channels": [
                    {"id": "C2", "name": "team", "is_channel": True},
                    {"id": "C9", "name": "old", "is_archived": True},
                ],
                "response_metadata": {"next_cursor": "page-two"},
            }
        return {
            "channels": [
                {"id": "C1", "name": "announcements", "is_channel": True},
                {"id": "G1", "name": "private", "is_private": True},
            ],
            "response_metadata": {"next_cursor": ""},
        }

    def conversations_info(self, **kwargs):
        return {
            "channel": {
                "id": kwargs["channel"],
                "name": "team",
                "is_channel": True,
                "is_archived": False,
                "is_private": False,
            }
        }

    def files_upload_v2(self, **kwargs):
        self.upload_call = kwargs
        return {"files": [{"id": "F123"}]}


def test_channel_listing_paginates_and_returns_only_active_public_channels():
    client = FakeSlackClient()
    service = SlackSharingService(client)  # type: ignore[arg-type]

    assert service.list_public_channels() == [
        SlackChannel(id="C1", name="announcements"),
        SlackChannel(id="C2", name="team"),
    ]
    assert len(client.list_calls) == 2


def test_share_uploads_poster_and_message_directly_to_channel(tmp_path):
    poster = tmp_path / "generated-poster.png"
    poster.write_bytes(b"poster bytes")
    client = FakeSlackClient()
    service = SlackSharingService(client)  # type: ignore[arg-type]

    receipt = service.share_poster(
        channel_id="C2",
        message="A simple Slack message",
        poster_path=poster,
        title="Example — ADvantage poster",
    )

    assert receipt == SlackShareReceipt("C2", "team", "F123")
    assert client.upload_call == {
        "channel": "C2",
        "file": str(poster),
        "filename": "generated-poster.png",
        "title": "Example — ADvantage poster",
        "alt_txt": "Generated ADvantage poster",
        "initial_comment": "A simple Slack message",
    }


def test_service_requires_server_side_token(monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    with pytest.raises(SlackNotConfiguredError, match="SLACK_BOT_TOKEN"):
        SlackSharingService.from_env()


def test_campaign_slack_endpoints_send_without_exposing_token(tmp_path, monkeypatch):
    poster = tmp_path / "poster.png"
    poster.write_bytes(b"poster bytes")
    run_id = "slack-test-run"
    campaign_api._RUNS[run_id] = CampaignResult(
        request=CampaignRequest(
            business_name="Example Academy",
            brief_text="Create a poster",
            format=CreativeFormat.POSTER,
        ),
        artifact=CampaignArtifact(
            format=CreativeFormat.POSTER,
            file_path=str(poster),
            width=1080,
            height=1350,
        ),
        verification=VerificationResult(passed=True),
    )

    class FakeService:
        def list_public_channels(self):
            return [SlackChannel(id="C123", name="announcements")]

        def share_poster(self, **kwargs):
            assert kwargs["poster_path"] == poster
            assert kwargs["message"] == "Shared from the UI"
            return SlackShareReceipt("C123", "announcements", "F456")

    monkeypatch.setattr(campaign_api, "_slack_service", lambda: FakeService())
    studio = PosterStudio(database_path=tmp_path / "studio.db", output_root=tmp_path / "projects")
    client = TestClient(create_app(studio))

    try:
        channels = client.get(f"/api/campaigns/{run_id}/slack/channels")
        shared = client.post(
            f"/api/campaigns/{run_id}/slack",
            json={"channel_id": "C123", "message": "Shared from the UI"},
        )
    finally:
        campaign_api._RUNS.pop(run_id, None)

    assert channels.status_code == 200
    assert shared.status_code == 200
    assert shared.json() == {
        "status": "sent",
        "channel_id": "C123",
        "channel_name": "announcements",
        "file_id": "F456",
    }
    assert "SLACK_BOT_TOKEN" not in shared.text
