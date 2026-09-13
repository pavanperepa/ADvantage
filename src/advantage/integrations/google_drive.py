from __future__ import annotations

import hashlib
import re
import time
from collections.abc import Iterable
from enum import Enum
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qs, urlparse

import requests
from pydantic import BaseModel, ConfigDict, Field


DRIVE_API_ROOT = "https://www.googleapis.com/drive/v3"
DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"
DRIVE_DOCUMENT_MIME = "application/vnd.google-apps.document"


class DriveIntakeError(RuntimeError):
    """Base error for a read-only Drive intake attempt."""


class DriveAuthenticationError(DriveIntakeError):
    pass


class DriveAccessError(DriveIntakeError):
    pass


class DriveProtocolError(DriveIntakeError):
    pass


class AssetKind(str, Enum):
    LOGO = "logo"
    PHOTO = "photo"
    VIDEO = "video"
    BRIEF = "brief"
    UNSUPPORTED = "unsupported"


class IntakeStatus(str, Enum):
    IMPORTED = "imported"
    SKIPPED = "skipped"
    QUARANTINED = "quarantined"


class DriveRemoteFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    mime_type: str = Field(min_length=1)
    size: int | None = Field(default=None, ge=0)
    modified_time: str | None = None
    md5_checksum: str | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    can_download: bool = True


class DriveClient(Protocol):
    def get_metadata(self, file_id: str) -> DriveRemoteFile: ...

    def list_children(self, folder_id: str) -> list[DriveRemoteFile]: ...

    def download(self, item: DriveRemoteFile, *, max_bytes: int) -> bytes: ...


class DriveIntakeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_files: int = Field(default=32, ge=1, le=200)
    max_image_bytes: int = Field(default=15 * 1024 * 1024, ge=1)
    max_video_bytes: int = Field(default=250 * 1024 * 1024, ge=1)
    max_brief_bytes: int = Field(default=1024 * 1024, ge=1)
    max_video_duration_seconds: float = Field(default=180.0, gt=0)
    max_videos: int = Field(default=6, ge=1, le=20)
    min_videos: int = Field(default=1, ge=0, le=20)
    require_logo: bool = True


class IntakeAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Raw Drive identifiers and names are useful during the owner session but
    # deliberately excluded from serialized receipts and logs.
    # Optional after serialization: raw provider values are intentionally
    # excluded, while the sanitized source_ref is sufficient to restore a
    # receipt or campaign job from disk.
    source_id: str = Field(default="", exclude=True, repr=False)
    source_name: str = Field(default="", exclude=True, repr=False)
    source_ref: str
    kind: AssetKind
    mime_type: str
    declared_size: int | None = None
    byte_size: int | None = None
    duration_seconds: float | None = None
    sha256: str | None = None
    local_ref: str | None = None
    status: IntakeStatus
    reason: str | None = None
    trusted_for_planning: bool = True
    duplicate_of: str | None = None


class DriveIntakeReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    provider: str = "google_drive"
    operation: str = "list_and_download_selected_folder"
    folder_ref: str
    assets: list[IntakeAsset]
    questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def imported(self) -> list[IntakeAsset]:
        return [asset for asset in self.assets if asset.status == IntakeStatus.IMPORTED]

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return path


class GoogleDriveClient:
    """Minimal read-only Drive v3 client using an injected OAuth access token."""

    def __init__(
        self,
        access_token: str,
        *,
        session: requests.Session | None = None,
        attempts: int = 3,
        timeout: int = 60,
    ) -> None:
        if not access_token.strip():
            raise DriveAuthenticationError("A Google Drive OAuth access token is required.")
        self._session = session or requests.Session()
        self._headers = {"Authorization": f"Bearer {access_token}"}
        self._attempts = attempts
        self._timeout = timeout

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        response: requests.Response | None = None
        for attempt in range(self._attempts):
            try:
                response = self._session.request(
                    method,
                    url,
                    headers=self._headers,
                    timeout=self._timeout,
                    **kwargs,
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                if attempt == self._attempts - 1:
                    raise DriveAccessError("Google Drive could not be reached.") from exc
                time.sleep(0.25 * (attempt + 1))
                continue
            if response.status_code in {429, 500, 502, 503, 504}:
                if attempt == self._attempts - 1:
                    raise DriveAccessError(
                        f"Google Drive remained unavailable (HTTP {response.status_code})."
                    )
                time.sleep(0.25 * (attempt + 1))
                continue
            if response.status_code == 401:
                raise DriveAuthenticationError("Google Drive authorization expired or is invalid.")
            if response.status_code in {403, 404}:
                raise DriveAccessError("The selected Google Drive item is not accessible.")
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                raise DriveProtocolError(
                    f"Google Drive returned HTTP {response.status_code}."
                ) from exc
            return response
        raise DriveAccessError("Google Drive request failed without a response.")

    def get_metadata(self, file_id: str) -> DriveRemoteFile:
        response = self._request(
            "GET",
            f"{DRIVE_API_ROOT}/files/{file_id}",
            params={
                "fields": (
                    "id,name,mimeType,size,modifiedTime,md5Checksum,"
                    "capabilities(canDownload),videoMediaMetadata(durationMillis)"
                ),
                "supportsAllDrives": "true",
            },
        )
        return _remote_file(response.json())

    def list_children(self, folder_id: str) -> list[DriveRemoteFile]:
        items: list[DriveRemoteFile] = []
        page_token: str | None = None
        while True:
            params = {
                "q": f"'{folder_id}' in parents and trashed = false",
                "pageSize": "100",
                "orderBy": "name_natural",
                "fields": (
                    "nextPageToken,files(id,name,mimeType,size,modifiedTime,"
                    "md5Checksum,capabilities(canDownload),"
                    "videoMediaMetadata(durationMillis))"
                ),
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            }
            if page_token:
                params["pageToken"] = page_token
            response = self._request("GET", f"{DRIVE_API_ROOT}/files", params=params)
            payload = response.json()
            items.extend(_remote_file(item) for item in payload.get("files", []))
            page_token = payload.get("nextPageToken")
            if not page_token:
                return items

    def download(self, item: DriveRemoteFile, *, max_bytes: int) -> bytes:
        if not item.can_download:
            raise DriveAccessError("The selected Drive file cannot be downloaded.")
        if item.mime_type == DRIVE_DOCUMENT_MIME:
            response = self._request(
                "GET",
                f"{DRIVE_API_ROOT}/files/{item.id}/export",
                params={"mimeType": "text/plain"},
                stream=True,
            )
        else:
            response = self._request(
                "GET",
                f"{DRIVE_API_ROOT}/files/{item.id}",
                params={"alt": "media", "supportsAllDrives": "true"},
                stream=True,
            )
        return _bounded_bytes(response.iter_content(chunk_size=1024 * 1024), max_bytes)


def parse_drive_folder_id(value: str) -> str:
    candidate = value.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{10,}", candidate):
        return candidate
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {
        "drive.google.com",
        "docs.google.com",
    }:
        raise ValueError("Provide a Google Drive folder URL or folder ID.")
    match = re.search(r"/folders/([A-Za-z0-9_-]+)", parsed.path)
    if match:
        return match.group(1)
    query_id = parse_qs(parsed.query).get("id", [""])[0]
    if re.fullmatch(r"[A-Za-z0-9_-]{10,}", query_id):
        return query_id
    raise ValueError("The Google Drive URL does not contain a folder ID.")


def source_ref(source_id: str) -> str:
    return hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:16]


def ingest_drive_folder(
    client: DriveClient,
    folder: str,
    destination: Path,
    *,
    config: DriveIntakeConfig | None = None,
) -> DriveIntakeReceipt:
    config = config or DriveIntakeConfig()
    folder_id = parse_drive_folder_id(folder)
    metadata = client.get_metadata(folder_id)
    if metadata.mime_type != DRIVE_FOLDER_MIME:
        raise DriveProtocolError("The selected Drive item is not a folder.")

    listed = client.list_children(folder_id)
    warnings: list[str] = []
    if len(listed) > config.max_files:
        warnings.append(
            f"Folder contains {len(listed)} items; only the first {config.max_files} were inspected."
        )
        listed = listed[: config.max_files]

    destination.mkdir(parents=True, exist_ok=True)
    assets: list[IntakeAsset] = []
    seen_hashes: dict[str, str] = {}
    brief_texts: list[str] = []
    imported_video_count = 0

    for item in listed:
        kind = classify_asset(item)
        ref = source_ref(item.id)
        base = IntakeAsset(
            source_id=item.id,
            source_name=item.name,
            source_ref=ref,
            kind=kind,
            mime_type=item.mime_type,
            declared_size=item.size,
            duration_seconds=item.duration_seconds,
            status=IntakeStatus.SKIPPED,
        )
        if kind == AssetKind.UNSUPPORTED:
            assets.append(base.model_copy(update={"reason": "unsupported_type"}))
            continue
        if not item.can_download:
            assets.append(base.model_copy(update={"reason": "download_not_permitted"}))
            continue
        if kind == AssetKind.VIDEO and imported_video_count >= config.max_videos:
            assets.append(base.model_copy(update={"reason": "video_limit_reached"}))
            continue

        limit = _byte_limit(kind, config)
        if item.size is not None and item.size > limit:
            assets.append(base.model_copy(update={"reason": "file_too_large"}))
            continue
        if kind == AssetKind.VIDEO:
            if item.duration_seconds is None:
                assets.append(base.model_copy(update={"reason": "video_duration_unavailable"}))
                continue
            if item.duration_seconds > config.max_video_duration_seconds:
                assets.append(base.model_copy(update={"reason": "video_too_long"}))
                continue

        try:
            content = client.download(item, max_bytes=limit)
        except DriveIntakeError as exc:
            assets.append(base.model_copy(update={"reason": _safe_error_reason(exc)}))
            continue
        except ValueError:
            assets.append(base.model_copy(update={"reason": "download_exceeded_limit"}))
            continue

        digest = hashlib.sha256(content).hexdigest().upper()
        if digest in seen_hashes:
            assets.append(
                base.model_copy(
                    update={
                        "byte_size": len(content),
                        "sha256": digest,
                        "reason": "duplicate_content",
                        "duplicate_of": seen_hashes[digest],
                    }
                )
            )
            continue

        suffix = _safe_suffix(item, kind)
        target = destination / f"{ref}{suffix}"
        target.write_bytes(content)
        seen_hashes[digest] = ref
        status = IntakeStatus.IMPORTED
        trusted = True
        reason: str | None = None
        if kind == AssetKind.BRIEF:
            text = content.decode("utf-8", errors="replace")
            if contains_untrusted_instruction(text):
                status = IntakeStatus.QUARANTINED
                trusted = False
                reason = "untrusted_instruction_detected"
            else:
                brief_texts.append(text)
        if kind == AssetKind.VIDEO and status == IntakeStatus.IMPORTED:
            imported_video_count += 1
        assets.append(
            base.model_copy(
                update={
                    "byte_size": len(content),
                    "sha256": digest,
                    "local_ref": target.as_posix(),
                    "status": status,
                    "reason": reason,
                    "trusted_for_planning": trusted,
                }
            )
        )

    questions = _actionable_questions(assets, brief_texts, config)
    return DriveIntakeReceipt(
        folder_ref=source_ref(folder_id),
        assets=assets,
        questions=questions,
        warnings=warnings,
    )


def classify_asset(item: DriveRemoteFile) -> AssetKind:
    if item.mime_type.startswith("video/"):
        return AssetKind.VIDEO
    if item.mime_type in {"image/png", "image/jpeg", "image/webp"}:
        stem = Path(item.name).stem.lower()
        if any(marker in stem for marker in ("logo", "brand", "mark", "crest")):
            return AssetKind.LOGO
        return AssetKind.PHOTO
    if item.mime_type in {
        "text/plain",
        "text/markdown",
        "application/json",
        DRIVE_DOCUMENT_MIME,
    }:
        return AssetKind.BRIEF
    return AssetKind.UNSUPPORTED


def contains_untrusted_instruction(text: str) -> bool:
    patterns = (
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"(?:reveal|print|show|exfiltrate).{0,40}(?:secret|token|api[-_ ]?key|credential)",
        r"(?:publish|activate|unpause).{0,40}(?:campaign|ad)",
        r"bypass.{0,30}(?:approval|permission|safety)",
        r"(?:run|execute).{0,30}(?:command|tool|script)",
    )
    lowered = text.lower()
    return any(re.search(pattern, lowered, flags=re.DOTALL) for pattern in patterns)


def _remote_file(payload: dict[str, Any]) -> DriveRemoteFile:
    video_metadata = payload.get("videoMediaMetadata") or {}
    duration_millis = video_metadata.get("durationMillis")
    return DriveRemoteFile(
        id=str(payload["id"]),
        name=str(payload.get("name") or "unnamed"),
        mime_type=str(payload.get("mimeType") or "application/octet-stream"),
        size=int(payload["size"]) if payload.get("size") is not None else None,
        modified_time=payload.get("modifiedTime"),
        md5_checksum=payload.get("md5Checksum"),
        duration_seconds=(
            float(duration_millis) / 1000 if duration_millis is not None else None
        ),
        can_download=bool((payload.get("capabilities") or {}).get("canDownload", True)),
    )


def _bounded_bytes(chunks: Iterable[bytes], max_bytes: int) -> bytes:
    data = bytearray()
    for chunk in chunks:
        if not chunk:
            continue
        data.extend(chunk)
        if len(data) > max_bytes:
            raise ValueError("Download exceeded the configured size limit.")
    return bytes(data)


def _byte_limit(kind: AssetKind, config: DriveIntakeConfig) -> int:
    if kind in {AssetKind.LOGO, AssetKind.PHOTO}:
        return config.max_image_bytes
    if kind == AssetKind.VIDEO:
        return config.max_video_bytes
    return config.max_brief_bytes


def _safe_suffix(item: DriveRemoteFile, kind: AssetKind) -> str:
    suffix_by_mime = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
        "video/quicktime": ".mov",
        "video/webm": ".webm",
        "text/plain": ".txt",
        "text/markdown": ".md",
        "application/json": ".json",
        DRIVE_DOCUMENT_MIME: ".txt",
    }
    suffix = suffix_by_mime.get(item.mime_type)
    if suffix:
        return suffix
    return ".mp4" if kind == AssetKind.VIDEO else ".bin"


def _safe_error_reason(error: DriveIntakeError) -> str:
    if isinstance(error, DriveAuthenticationError):
        return "authorization_failed"
    if isinstance(error, DriveAccessError):
        return "download_not_accessible"
    return "provider_error"


def _actionable_questions(
    assets: list[IntakeAsset],
    brief_texts: list[str],
    config: DriveIntakeConfig,
) -> list[str]:
    questions: list[str] = []
    imported = [asset for asset in assets if asset.status == IntakeStatus.IMPORTED]
    if config.require_logo and not any(asset.kind == AssetKind.LOGO for asset in imported):
        questions.append("Add or identify one downloadable logo image in the selected folder.")
    videos = [asset for asset in imported if asset.kind == AssetKind.VIDEO]
    if len(videos) < config.min_videos:
        questions.append(
            "Add at least one downloadable short video within the configured size and duration limits."
        )
    if any(asset.status == IntakeStatus.QUARANTINED for asset in assets):
        questions.append(
            "Review the quarantined brief; imported instructions cannot authorize tools, publishing, or secret access."
        )
    phones = _fact_candidates(brief_texts, r"(?:\+?\d[\d .()\-]{8,}\d)")
    urls = _fact_candidates(brief_texts, r"https?://[^\s<>\]\[\)\(]+")
    if len(phones) > 1:
        questions.append("Resolve the conflicting phone numbers found in the imported briefs.")
    if len(urls) > 1:
        questions.append("Resolve the conflicting destination URLs found in the imported briefs.")
    return questions


def _fact_candidates(texts: list[str], pattern: str) -> set[str]:
    values: set[str] = set()
    for text in texts:
        values.update(match.strip().rstrip(".,;") for match in re.findall(pattern, text))
    return values
