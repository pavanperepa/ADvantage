"""Server-side one-way Slack sharing for generated poster artifacts."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError, SlackClientError


class SlackSharingError(RuntimeError):
    """A safe, user-facing Slack integration failure."""


class SlackNotConfiguredError(SlackSharingError):
    """Raised when the server has no bot token."""


class SlackChannelUnavailableError(SlackSharingError):
    """Raised when a requested channel is not an eligible public channel."""


@dataclass(frozen=True, slots=True)
class SlackChannel:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class SlackShareReceipt:
    channel_id: str
    channel_name: str
    file_id: str | None = None


_SLACK_ERROR_MESSAGES = {
    "channel_not_found": "Slack could not find that public channel.",
    "invalid_auth": "Slack rejected the configured bot token. Reinstall or update the token.",
    "missing_scope": "The Slack app is missing a required permission.",
    "not_authed": "Slack sharing is not authenticated on the server.",
    "not_in_channel": "Invite the ADvantage Slack bot to that channel, then try again.",
    "ratelimited": "Slack is temporarily rate limiting requests. Try again shortly.",
    "token_revoked": "The configured Slack bot token has been revoked.",
}


class SlackSharingService:
    def __init__(self, client: WebClient) -> None:
        self.client = client

    @classmethod
    def from_env(cls) -> "SlackSharingService":
        token = os.getenv("SLACK_BOT_TOKEN", "").strip()
        if not token:
            raise SlackNotConfiguredError(
                "Slack sharing is not configured. Set SLACK_BOT_TOKEN on the backend."
            )
        return cls(WebClient(token=token))

    def list_public_channels(self) -> list[SlackChannel]:
        channels: dict[str, SlackChannel] = {}
        cursor: str | None = None
        while True:
            response = self._call(
                self.client.conversations_list,
                types="public_channel",
                exclude_archived=True,
                limit=200,
                cursor=cursor,
            )
            for item in response.get("channels", []):
                channel_id = item.get("id")
                name = item.get("name")
                if (
                    isinstance(channel_id, str)
                    and isinstance(name, str)
                    and not item.get("is_archived", False)
                    and not item.get("is_private", False)
                ):
                    channels[channel_id] = SlackChannel(id=channel_id, name=name)
            metadata = response.get("response_metadata") or {}
            next_cursor = metadata.get("next_cursor", "")
            cursor = next_cursor.strip() if isinstance(next_cursor, str) else ""
            if not cursor:
                break
        return sorted(channels.values(), key=lambda channel: channel.name.casefold())

    def share_poster(
        self,
        *,
        channel_id: str,
        message: str,
        poster_path: Path,
        title: str,
    ) -> SlackShareReceipt:
        if not message.strip():
            raise SlackSharingError("Add a message before sending to Slack.")
        if not poster_path.is_file():
            raise SlackSharingError("The generated poster is no longer available on the server.")

        channel = self._public_channel(channel_id)
        response = self._call(
            self.client.files_upload_v2,
            channel=channel_id,
            file=str(poster_path),
            filename=poster_path.name,
            title=title,
            alt_txt="Generated ADvantage poster",
            initial_comment=message.strip(),
        )
        files = response.get("files") or []
        first_file = files[0] if files and isinstance(files[0], dict) else {}
        name = channel.get("name")
        return SlackShareReceipt(
            channel_id=channel_id,
            channel_name=name if isinstance(name, str) else channel_id,
            file_id=first_file.get("id") if isinstance(first_file.get("id"), str) else None,
        )

    def _public_channel(self, channel_id: str) -> dict[str, Any]:
        info = self._call(self.client.conversations_info, channel=channel_id)
        channel = info.get("channel") or {}
        if (
            channel.get("id") != channel_id
            or channel.get("is_archived", False)
            or channel.get("is_private", False)
            or not channel.get("is_channel", False)
        ):
            raise SlackChannelUnavailableError("Choose an active public Slack channel.")
        return channel

    @staticmethod
    def _call(method: Any, **kwargs: Any) -> Any:
        try:
            return method(**kwargs)
        except SlackApiError as exc:
            code = exc.response.get("error", "slack_api_error")
            safe_message = _SLACK_ERROR_MESSAGES.get(
                code, f"Slack could not complete the request ({code})."
            )
            raise SlackSharingError(safe_message) from exc
        except SlackClientError as exc:
            raise SlackSharingError(
                "Could not reach Slack. Check the connection and try again."
            ) from exc
