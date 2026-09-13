"""Shared contract for the simplified poster-or-reel campaign flow.

Deliberately smaller than a fully versioned, provenance-tracked manifest: one
request in, one creative out, one Meta ad out. Per-fact provenance, schema
migration, and multi-revision approval binding are cut from this build; add
them back only if real usage shows they are needed.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from ..drive_intake import IntakeAsset


class CreativeFormat(str, Enum):
    POSTER = "poster"
    REEL = "reel"


class CampaignRequest(BaseModel):
    """One owner request: pick a format, supply facts and assets for it."""

    model_config = ConfigDict(extra="forbid")

    business_name: str = Field(min_length=1)
    brief_text: str = Field(min_length=1, description="Rough owner request/copy source")
    format: CreativeFormat

    contact_phone: str | None = None
    destination_url: str | None = None
    offer_text: str | None = None
    audience: str | None = None

    budget_usd: float | None = Field(default=None, ge=1)
    campaign_days: int = Field(default=4, ge=1, le=60)

    logo_asset: IntakeAsset | None = None
    photo_assets: list[IntakeAsset] = Field(default_factory=list)
    footage_assets: list[IntakeAsset] = Field(default_factory=list)

    def blockers(self) -> list[str]:
        """Human-readable reasons this request cannot produce its format yet."""
        problems: list[str] = []
        if self.format == CreativeFormat.REEL and not self.footage_assets:
            problems.append("Select at least one video clip for a reel.")
        return problems

    def warnings(self) -> list[str]:
        """Non-blocking notes worth surfacing before generation."""
        notes: list[str] = []
        if self.logo_asset is None:
            notes.append("No logo selected; the creative will render without one.")
        return notes


class CampaignArtifact(BaseModel):
    """The single produced creative for a request."""

    model_config = ConfigDict(extra="forbid")

    format: CreativeFormat
    file_path: str
    width: int
    height: int
    duration_seconds: float | None = None


class VerificationResult(BaseModel):
    """One verification pass over a produced artifact, before it reaches the owner."""

    model_config = ConfigDict(extra="forbid")

    passed: bool
    findings: list[str] = Field(default_factory=list)


class MetaAdPreview(BaseModel):
    """Read-only preview of the Meta payload this request would create."""

    model_config = ConfigDict(extra="forbid")

    campaign_name: str
    objective: str
    daily_budget_usd: float
    days: int
    primary_text: str
    headline: str
    call_to_action: str
    destination_url: str | None
    creative_format: CreativeFormat


class MetaAdResult(BaseModel):
    """Outcome of a dry-run or executed Meta creation call."""

    model_config = ConfigDict(extra="forbid")

    dry_run: bool
    campaign_id: str | None = None
    ad_set_id: str | None = None
    ad_id: str | None = None
    status: str
