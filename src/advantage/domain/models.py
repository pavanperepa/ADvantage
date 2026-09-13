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


class BrandPalette(str, Enum):
    """Named colour scheme for a creative.

    Every creative path (Ideogram stamping, the offline compose pipeline, and
    the reel's EditSpec ``brand`` block) previously hardcoded the same academy
    blue/yellow. This is the one knob that recolours all three, so a business
    that is not blue-and-yellow is not forced to look like one.
    """

    ACADEMY_BLUE = "academy_blue"
    SUNSET_WARM = "sunset_warm"
    FOREST_GREEN = "forest_green"
    CRIMSON_SPORT = "crimson_sport"
    ROYAL_PURPLE = "royal_purple"
    MONO_SLATE = "mono_slate"


class PaletteSwatch(BaseModel):
    """The concrete colours one :class:`BrandPalette` resolves to."""

    model_config = ConfigDict(extra="forbid")

    label: str
    primary: str
    accent: str
    ink: str


#: The single source of truth for what each palette actually looks like.
#: ``primary`` carries panels and fills, ``accent`` is the highlight/rule
#: colour, ``ink`` is the darkest value used behind light text.
PALETTE_SWATCHES: dict[BrandPalette, PaletteSwatch] = {
    BrandPalette.ACADEMY_BLUE: PaletteSwatch(
        label="Academy blue", primary="#2E7BFF", accent="#FFD100", ink="#080D1F"
    ),
    BrandPalette.SUNSET_WARM: PaletteSwatch(
        label="Sunset warm", primary="#F2683C", accent="#FFC24B", ink="#2A1207"
    ),
    BrandPalette.FOREST_GREEN: PaletteSwatch(
        label="Forest green", primary="#1F8A5B", accent="#E7C948", ink="#07200F"
    ),
    BrandPalette.CRIMSON_SPORT: PaletteSwatch(
        label="Crimson sport", primary="#C8102E", accent="#F4B41A", ink="#1A0407"
    ),
    BrandPalette.ROYAL_PURPLE: PaletteSwatch(
        label="Royal purple", primary="#5B3FD6", accent="#FFD166", ink="#100A2B"
    ),
    BrandPalette.MONO_SLATE: PaletteSwatch(
        label="Mono slate", primary="#3F4A5A", accent="#9FB3C8", ink="#0B1016"
    ),
}

#: Used wherever a request carries no explicit palette, so behaviour is
#: unchanged for callers that never set one.
DEFAULT_PALETTE = BrandPalette.ACADEMY_BLUE


def resolve_palette(palette: "BrandPalette | None") -> PaletteSwatch:
    """The swatch for ``palette``, falling back to the academy default."""
    return PALETTE_SWATCHES[palette or DEFAULT_PALETTE]


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
    palette: BrandPalette | None = Field(
        default=None, description="Named colour scheme; None means the academy default"
    )
    refinement_notes: str | None = Field(
        default=None,
        description="Free-text 'make it more X' instructions from a regenerate request",
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


class ActivityStep(BaseModel):
    """One step the system took while producing a creative.

    Exists purely for owner-facing visibility: the generate call is otherwise
    an opaque wait, and a small business owner has no way to tell a slow
    render from a silent fallback.
    """

    model_config = ConfigDict(extra="forbid")

    label: str
    detail: str = ""
    status: Literal["done", "skipped", "failed"] = "done"
    seconds: float | None = None


class CreativeCritique(BaseModel):
    """An independent review pass over the finished creative.

    Separate from ``VerificationResult``, which answers "is this file
    structurally correct". This answers "is this any good, and what went
    wrong" -- including, deliberately, where the system struggled. Honest
    weaknesses are the point; an empty ``struggled`` list on a visibly poor
    poster is a failure of this step, not a pass.
    """

    model_config = ConfigDict(extra="forbid")

    summary: str
    did: list[str] = Field(default_factory=list)
    why: list[str] = Field(default_factory=list)
    #: Every piece of the owner's own information that actually reached the
    #: creative -- the answer to "did it use what I gave it?". Read from the
    #: renderer's stamped-copy record, not re-derived from the request, so it
    #: reflects what is really on the artwork.
    information: list[str] = Field(default_factory=list)
    #: Kept for internal use (it drives regeneration hints and shows up in
    #: logs), but deliberately NOT surfaced to the owner: the review panel is
    #: there to explain the creative, not to argue with it.
    struggled: list[str] = Field(default_factory=list)
    #: False when no vision model reviewed the pixels, so the UI never implies
    #: the artwork was actually looked at when it was not.
    model_reviewed: bool = False


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
    critique: CreativeCritique | None = None
    activity: list[ActivityStep] = Field(default_factory=list)
