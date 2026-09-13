"""Read-only browsing of "Shared with me" folders, and the campaign-folder picker."""

from __future__ import annotations

import pytest

from advantage.integrations.google_drive import (
    DRIVE_FOLDER_MIME,
    DriveFolderNotSharedError,
    DriveRemoteFile,
    GoogleDriveClient,
    find_shared_folder,
    list_campaign_folders,
)


class FakeSharedDrive:
    """A minimal DriveClient double exposing only `list_shared_folders`/`list_children`."""

    def __init__(
        self,
        shared_folders: list[DriveRemoteFile],
        children_by_folder_id: dict[str, list[DriveRemoteFile]] | None = None,
    ) -> None:
        self.shared_folders = shared_folders
        self.children_by_folder_id = children_by_folder_id or {}
        self.list_children_calls: list[str] = []

    def list_shared_folders(self) -> list[DriveRemoteFile]:
        return self.shared_folders

    def list_children(self, folder_id: str) -> list[DriveRemoteFile]:
        self.list_children_calls.append(folder_id)
        return self.children_by_folder_id.get(folder_id, [])


def folder(file_id: str, name: str) -> DriveRemoteFile:
    return DriveRemoteFile(id=file_id, name=name, mime_type=DRIVE_FOLDER_MIME)


def image(file_id: str, name: str) -> DriveRemoteFile:
    return DriveRemoteFile(id=file_id, name=name, mime_type="image/png")


# --- find_shared_folder ------------------------------------------------------


def test_find_shared_folder_is_case_insensitive():
    client = FakeSharedDrive([folder("f1", "Social Media"), folder("f2", "Brand Assets")])

    found = find_shared_folder(client, "social media")

    assert found is not None
    assert found.id == "f1"


def test_find_shared_folder_returns_none_when_absent():
    client = FakeSharedDrive([folder("f1", "Brand Assets")])

    assert find_shared_folder(client, "Social Media") is None


def test_find_shared_folder_matches_exact_name_not_substring():
    client = FakeSharedDrive([folder("f1", "Social Media Archive")])

    assert find_shared_folder(client, "Social Media") is None


# --- list_campaign_folders ----------------------------------------------------


def test_list_campaign_folders_returns_only_subfolders():
    client = FakeSharedDrive(
        [folder("parent", "Social Media")],
        {
            "parent": [
                folder("c1", "Sept Campaign"),
                folder("c2", "Diwali Push"),
                image("f-logo", "not-a-folder.png"),
            ]
        },
    )

    folders = list_campaign_folders(client)

    assert {f.name for f in folders} == {"Sept Campaign", "Diwali Push"}
    assert all(f.id in {"c1", "c2"} for f in folders)
    assert client.list_children_calls == ["parent"]


def test_list_campaign_folders_is_case_insensitive_on_parent_name():
    client = FakeSharedDrive(
        [folder("parent", "social media")],
        {"parent": [folder("c1", "Sept Campaign")]},
    )

    folders = list_campaign_folders(client, parent_name="Social Media")

    assert [f.name for f in folders] == ["Sept Campaign"]


def test_list_campaign_folders_raises_clear_error_when_parent_not_shared():
    client = FakeSharedDrive([folder("f1", "Brand Assets")])

    with pytest.raises(DriveFolderNotSharedError, match="Social Media"):
        list_campaign_folders(client)


def test_list_campaign_folders_names_a_custom_parent_in_the_error():
    client = FakeSharedDrive([])

    with pytest.raises(DriveFolderNotSharedError, match="Client Uploads"):
        list_campaign_folders(client, parent_name="Client Uploads")


# --- GoogleDriveClient.list_shared_folders builds the right query -----------


class RecordingSession:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.requests: list[dict] = []

    def request(self, method: str, url: str, **kwargs):
        self.requests.append({"method": method, "url": url, **kwargs})
        return StubResponse(self.payload)


class StubResponse:
    status_code = 200

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_list_shared_folders_builds_the_sharedwithme_query():
    session = RecordingSession(
        {"files": [{"id": "f1", "name": "Social Media", "mimeType": DRIVE_FOLDER_MIME}]}
    )
    client = GoogleDriveClient("test-token", session=session)

    folders = client.list_shared_folders()

    assert len(folders) == 1
    assert folders[0].id == "f1"
    request = session.requests[0]
    assert request["method"] == "GET"
    query = request["params"]["q"]
    assert "sharedWithMe = true" in query
    assert f"mimeType = '{DRIVE_FOLDER_MIME}'" in query
    assert "trashed = false" in query
    assert request["headers"] == {"Authorization": "Bearer test-token"}


def test_list_shared_folders_paginates():
    session = RecordingSession({})
    calls = {"n": 0}

    def request(method: str, url: str, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return StubResponse(
                {
                    "files": [{"id": "f1", "name": "Social Media", "mimeType": DRIVE_FOLDER_MIME}],
                    "nextPageToken": "page2",
                }
            )
        return StubResponse(
            {"files": [{"id": "f2", "name": "Brand Assets", "mimeType": DRIVE_FOLDER_MIME}]}
        )

    session.request = request
    client = GoogleDriveClient("test-token", session=session)

    folders = client.list_shared_folders()

    assert {f.id for f in folders} == {"f1", "f2"}
    assert calls["n"] == 2
