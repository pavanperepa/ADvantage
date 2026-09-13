"""Versioned HTTP boundary for the future owner-facing UI.

These models deliberately do not expose access tokens, raw Drive identifiers,
server filesystem paths, or executable Meta flags. They are transport models;
the application layer resolves safe ``source_ref`` values to internal assets.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..domain.models import CreativeFormat
from ..integrations.google_drive import AssetKind, IntakeStatus


API_CONTRACT_VERSION = "1.0"
SHA256_PATTERN = r"^[A-Fa-f0-9]{64}$"


class StrictModel(BaseModel):
    """Strict base model shared by public contracts and nested values."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ApiContract(StrictModel):
    """Version marker carried once by each top-level HTTP body."""

    schema_version: Literal["1.0"] = API_CONTRACT_VERSION


class CampaignState(str, Enum):
    DRAFT = "draft"
    NEEDS_FACTS = "needs_facts"
    READY = "ready"
    RENDERING = "rendering"
    NEEDS_REVIEW = "needs_review"
    APPROVED_FOR_PAUSED_CREATE = "approved_for_paused_create"
    CREATING_PAUSED = "creating_paused"
    PAUSED_VERIFIED = "paused_verified"
    BLOCKED = "blocked"
    FAILED = "failed"
    PARTIAL_EXTERNAL_RESULT = "partial_external_result"


class CameraAudioPolicy(str, Enum):
    MUTE = "mute"
    KEEP = "keep"
    DIALOGUE_PRIORITY = "dialogue_priority"


class ReviewLevel(str, Enum):
    FILE_INTEGRITY = "file_integrity"
    DETERMINISTIC = "deterministic"
    CREATIVE = "creative"
    HUMAN = "human"


class CampaignSchedule(StrictModel):
    starts_at: datetime
    ends_at: datetime
    timezone: str = Field(min_length=1, max_length=64)

    @field_validator("starts_at", "ends_at")
    @classmethod
    def require_timezone_aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("campaign timestamps must include a UTC offset")
        return value

    @field_validator("timezone")
    @classmethod
    def require_iana_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            # Windows does not ship the IANA database with Python. Keep the
            # transport contract usable in that environment while still
            # rejecting free-form abbreviations; deployments with tzdata
            # installed receive full ZoneInfo validation above.
            if value != "UTC" and not re.fullmatch(
                r"[A-Za-z_]+(?:/[A-Za-z0-9_+\-]+)+", value
            ):
                raise ValueError("timezone must be an IANA timezone name") from exc
        return value

    @model_validator(mode="after")
    def require_forward_range(self) -> "CampaignSchedule":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")
        return self


class CampaignBudget(StrictModel):
    total_amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    currency: Literal["USD"] = "USD"


class MediaPermissions(StrictModel):
    supplied_media_approved: bool
    likeness_use_approved: bool | None = None
    notes: str | None = Field(default=None, max_length=500)


class AssetSelection(StrictModel):
    """Client-safe selection of an asset from a server-held intake receipt."""

    source_ref: str = Field(min_length=8, max_length=128)
    kind: AssetKind
    sha256: str = Field(pattern=SHA256_PATTERN)


class DriveIntakeRequest(ApiContract):
    folder: str = Field(min_length=1, max_length=2048)
    max_files: int = Field(default=32, ge=1, le=200)
    max_videos: int = Field(default=6, ge=1, le=20)
    max_video_duration_seconds: float = Field(default=180.0, gt=0, le=900)


class DriveAssetView(StrictModel):
    source_ref: str
    kind: AssetKind
    mime_type: str
    byte_size: int | None = None
    duration_seconds: float | None = None
    sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    status: IntakeStatus
    reason: str | None = None
    trusted_for_planning: bool


class DriveIntakeView(ApiContract):
    intake_id: str
    folder_ref: str
    assets: list[DriveAssetView]
    questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CampaignDraftRequest(ApiContract):
    business_name: str = Field(min_length=1, max_length=100)
    brief_text: str = Field(min_length=1, max_length=4000)
    creative_format: CreativeFormat
    contact_phone: str | None = Field(default=None, max_length=40)
    destination_url: str | None = Field(default=None, max_length=2048)
    offer_text: str | None = Field(default=None, max_length=500)
    offer_expires_at: datetime | None = None
    audience: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=500)
    schedule: CampaignSchedule | None = None
    budget: CampaignBudget | None = None
    page_ref: str | None = Field(default=None, max_length=128)
    destination_form_ref: str | None = Field(default=None, max_length=128)
    camera_audio_policy: CameraAudioPolicy = CameraAudioPolicy.MUTE
    permissions: MediaPermissions
    assets: list[AssetSelection] = Field(default_factory=list)

    @field_validator("destination_url")
    @classmethod
    def require_http_destination(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("destination_url must be an absolute HTTP(S) URL")
        if parsed.hostname and parsed.hostname.endswith(".test"):
            raise ValueError("reserved .test destinations cannot be submitted")
        return value

    @field_validator("contact_phone")
    @classmethod
    def require_plausible_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(re.sub(r"\D", "", value)) < 10:
            raise ValueError("contact_phone must contain at least 10 digits")
        return value

    @field_validator("offer_expires_at")
    @classmethod
    def require_aware_offer_expiry(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("offer_expires_at must include a UTC offset")
        return value

    @model_validator(mode="after")
    def validate_material_relationships(self) -> "CampaignDraftRequest":
        if self.offer_text and self.offer_expires_at is None:
            raise ValueError("an offer requires offer_expires_at")
        if self.schedule and self.offer_expires_at and self.offer_expires_at < self.schedule.starts_at:
            raise ValueError("offer_expires_at cannot be earlier than the campaign start")

        selected_kinds = {asset.kind for asset in self.assets}
        if self.creative_format == CreativeFormat.REEL and AssetKind.VIDEO not in selected_kinds:
            raise ValueError("a reel requires at least one selected video asset")
        return self


class CampaignJobAccepted(ApiContract):
    run_id: str
    state: CampaignState
    status_url: str


class ArtifactView(StrictModel):
    format: CreativeFormat
    download_url: str
    sha256: str = Field(pattern=SHA256_PATTERN)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    duration_seconds: float | None = Field(default=None, gt=0)


class VerificationFinding(StrictModel):
    code: str
    message: str
    level: ReviewLevel
    blocking: bool


class VerificationView(StrictModel):
    passed: bool
    completed_levels: list[ReviewLevel]
    findings: list[VerificationFinding] = Field(default_factory=list)


class MetaPreviewView(StrictModel):
    payload_sha256: str = Field(pattern=SHA256_PATTERN)
    campaign_name: str
    objective: str
    total_budget: CampaignBudget
    schedule: CampaignSchedule
    audience: str
    location: str
    page_ref: str
    destination_url: str | None = None
    destination_form_ref: str | None = None
    primary_text: str
    headline: str
    call_to_action: str
    desired_status: Literal["PAUSED"] = "PAUSED"


class CampaignReviewView(ApiContract):
    run_id: str
    state: CampaignState
    manifest_sha256: str = Field(pattern=SHA256_PATTERN)
    artifacts: list[ArtifactView]
    verification: VerificationView
    meta_preview: MetaPreviewView | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ApprovalBinding(StrictModel):
    manifest_sha256: str = Field(pattern=SHA256_PATTERN)
    artifact_sha256: str = Field(pattern=SHA256_PATTERN)
    payload_sha256: str = Field(pattern=SHA256_PATTERN)
    approved_at: datetime
    approved_by: str = Field(min_length=1, max_length=200)

    @field_validator("approved_at")
    @classmethod
    def require_aware_approval_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("approved_at must include a UTC offset")
        return value


class PausedCampaignCreateRequest(ApiContract):
    run_id: str
    approval: ApprovalBinding
    confirmation: Literal["CREATE_PAUSED"]


class PausedCampaignView(ApiContract):
    run_id: str
    state: Literal[CampaignState.PAUSED_VERIFIED]
    campaign_id: str
    ad_set_id: str
    creative_id: str
    ad_id: str
    verified_status: Literal["PAUSED"] = "PAUSED"


class ApiError(ApiContract):
    code: str
    message: str
    field: str | None = None
    retryable: bool = False
