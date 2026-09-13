"""Shared contract for the simplified poster-or-reel campaign flow.

Deliberately smaller than a fully versioned, provenance-tracked manifest: one
request in, one creative out, one Meta ad out. Per-fact provenance, schema
migration, and multi-revision approval binding are cut from this build; add
them back only if real usage shows they are needed.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..integrations.google_drive import IntakeAsset


class CreativeFormat(str, Enum):
    POSTER = "poster"
    REEL = "reel"


class ReelFeel(str, Enum):
    """The requested *feel* of a reel, chosen by the owner in one question.

    This is the single input that drives the whole edit plan (theme, shot
    motion, transitions, and which of `remotion/library`'s 16 overlay types
    appear). See `adapters/reel_plan.py` for the mapping.
    """

    HIGH_ENERGY = "high_energy"
    CINEMATIC = "cinematic"
    WARM_TESTIMONIAL = "warm_testimonial"
    URGENT_OFFER = "urgent_offer"
    CLEAN_EXPLAINER = "clean_explainer"


class PosterStyle(str, Enum):
    """Art direction for the Ideogram artwork behind a poster.

    Ideogram renders the *scene only* (text-free, per AGENTS.md); exact
    business copy is always stamped deterministically on top.
    """

    PHOTOREAL = "photoreal"
    BOLD_GRAPHIC = "bold_graphic"
    WARM_LIFESTYLE = "warm_lifestyle"
    PREMIUM_MINIMAL = "premium_minimal"


class CampaignRequest(BaseModel):
    """One owner request: pick a format, supply facts and assets for it."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    business_name: str = Field(min_length=1)
    brief_text: str = Field(min_length=1, description="Rough owner request/copy source")
    format: CreativeFormat

    contact_phone: str | None = None
    destination_url: str | None = None
    offer_text: str | None = None
    offer_expires_at: datetime | None = None
    audience: str | None = None
    location: str | None = None

    budget_usd: float | None = Field(default=None, ge=1)
    campaign_days: int = Field(default=4, ge=1, le=60)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = None
    currency: Literal["USD"] = "USD"
    page_ref: str | None = None
    destination_form_ref: str | None = None
    camera_audio_policy: Literal["mute", "keep", "dialogue_priority"] = "mute"

    # Creative direction, normally supplied by the interview (see
    # application/interview.py) rather than typed by hand.
    reel_feel: ReelFeel | None = None
    poster_style: PosterStyle | None = None
    art_direction_notes: str | None = Field(
        default=None, description="Owner's description of the scene/subject for the artwork"
    )
    key_benefits: list[str] = Field(
        default_factory=list, description="Short benefit phrases; feed checklist/ticker overlays"
    )
    proof_point: str | None = Field(
        default=None, description="One verifiable fact or quote the owner supplied"
    )
    supplied_media_approved: bool = False
    likeness_use_approved: bool | None = None

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
    creative_id: str | None = None
    ad_id: str | None = None
    status: str


class CreativeDecision(BaseModel):
    """One choice the creative planner made, and the reason for it.

    Exists so the UI can show *why* a reel or poster looks the way it does
    instead of presenting the render as an unexplained black box.
    """

    model_config = ConfigDict(extra="forbid")

    choice: str
    reason: str


class CreativePlan(BaseModel):
    """The planner's decisions for one creative, surfaced to the owner."""

    model_config = ConfigDict(extra="forbid")

    format: CreativeFormat
    feel: str
    decisions: list[CreativeDecision] = Field(default_factory=list)


class RationaleFactor(BaseModel):
    """One grounded claim behind the Meta ad setup."""

    model_config = ConfigDict(extra="forbid")

    claim: str
    evidence: str
    source: Literal["meta_insights", "meta_defaults", "request", "creative_plan"]


class CampaignRationale(BaseModel):
    """Why this campaign was built this way, for the owner to read.

    ``meta_account_grounded`` is False when no Meta read succeeded, so the UI
    never implies account evidence that was not actually fetched.
    """

    model_config = ConfigDict(extra="forbid")

    summary: str
    factors: list[RationaleFactor] = Field(default_factory=list)
    meta_account_grounded: bool = False


class CampaignResult(BaseModel):
    """The bundle `orchestrator.run_campaign()` returns: one request's worth
    of generate + verify + (budget permitting) suggest, nothing published."""

    model_config = ConfigDict(extra="forbid")

    request: CampaignRequest
    artifact: CampaignArtifact
    verification: VerificationResult
    meta_preview: MetaAdPreview | None = None
    plan: CreativePlan | None = None
    rationale: CampaignRationale | None = None
