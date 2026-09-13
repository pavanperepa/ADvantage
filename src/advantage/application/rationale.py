"""Build the owner-facing explanation of why this campaign was set up this way.

``build_rationale`` explains the concrete choices ``adapters/meta_ads.py``
actually made for this request -- objective, budget split, audience,
call-to-action, and creative/placement fit -- plus the decisions the creative
planner made (``CreativePlan.decisions``), each with honest, source-tagged
evidence:

* ``"meta_insights"`` -- only when a real account read produced the number,
  and the evidence text quotes it.
* ``"meta_defaults"`` -- documented platform/account-adapter behaviour with
  no account read behind it in this run.
* ``"request"`` -- what the owner supplied on the request itself.
* ``"creative_plan"`` -- a decision the poster/reel planner made.

``meta_account_grounded`` is set True only when at least one factor's source
is genuinely ``"meta_insights"`` -- this is what stops the UI from implying
account evidence that was never actually fetched. Must produce a useful
rationale with ``insights=None`` (no Meta credentials) too.
"""

from __future__ import annotations

from ..adapters.meta_insights import MetaInsightsSummary
from ..domain.models import (
    CampaignArtifact,
    CampaignRationale,
    CampaignRequest,
    CreativeFormat,
    CreativePlan,
    MetaAdPreview,
    RationaleFactor,
)


def _objective_factor(preview: MetaAdPreview) -> RationaleFactor:
    return RationaleFactor(
        claim=f"Campaign objective: {preview.objective}.",
        evidence=(
            "OUTCOME_LEADS is this account's configured default objective for "
            "lead-generation style campaigns -- a platform/account-adapter default, "
            "not derived from a live insights read in this run."
        ),
        source="meta_defaults",
    )


def _budget_factor(request: CampaignRequest, preview: MetaAdPreview) -> RationaleFactor:
    return RationaleFactor(
        claim=f"${preview.daily_budget_usd:.2f}/day for {preview.days} day(s).",
        evidence=(
            f"You supplied a total budget of ${request.budget_usd:.2f} over "
            f"{request.campaign_days} day(s); the daily budget is that total divided "
            "evenly across the campaign's days."
        ),
        source="request",
    )


def _audience_factors(insights: MetaInsightsSummary | None) -> list[RationaleFactor]:
    factors = [
        RationaleFactor(
            claim="Broad US audience (age 18-65) with Advantage+ audience targeting on, no interest stacking.",
            evidence=(
                "This account's Meta ad adapter defaults to broad, non-interest-stacked "
                "targeting -- a documented platform/account default, not derived from a "
                "live insights read in this run."
            ),
            source="meta_defaults",
        )
    ]
    if insights is not None and insights.available and insights.best_age_bands:
        top = insights.best_age_bands[0]
        factors.append(
            RationaleFactor(
                claim=f"Age band {top.age_range} has historically driven the strongest engagement.",
                evidence=(
                    f"Across this account's lifetime delivery, age {top.age_range} shows a "
                    f"{top.ctr_pct:.2f}% CTR across {top.impressions:,} impressions -- the "
                    "highest of any age band on file. Broad targeting keeps this band in the "
                    "eligible audience rather than narrowing it out."
                ),
                source="meta_insights",
            )
        )
    return factors


def _cta_factor(request: CampaignRequest, preview: MetaAdPreview) -> RationaleFactor:
    if request.destination_url:
        evidence = (
            f"You supplied a destination URL ({request.destination_url}); when one is present "
            "the ad adapter uses LEARN_MORE to send clicks there."
        )
    elif request.contact_phone:
        evidence = (
            f"You supplied a contact phone number ({request.contact_phone}) with no destination "
            "URL, so the ad adapter uses CALL_NOW instead of a link-click CTA."
        )
    else:
        evidence = "No destination URL or phone number was supplied, so the ad adapter falls back to LEARN_MORE."
    return RationaleFactor(
        claim=f"Call to action: {preview.call_to_action}.",
        evidence=evidence,
        source="request",
    )


def _format_placement_factors(
    artifact: CampaignArtifact, insights: MetaInsightsSummary | None
) -> list[RationaleFactor]:
    format_label = "Reel (vertical video)" if artifact.format == CreativeFormat.REEL else "Poster (static image)"
    factors = [
        RationaleFactor(
            claim=f"Creative format: {format_label}, {artifact.width}x{artifact.height}.",
            evidence=(
                "Vertical 9:16 video (Reels/Stories) is Meta's primary short-form placement "
                "inventory; 4:5 feed images are the standard static-image placement -- a "
                "platform default, not derived from a live insights read in this run."
            ),
            source="meta_defaults",
        )
    ]
    if insights is not None and insights.available and insights.top_placements:
        top = insights.top_placements[0]
        share_pct = (
            100.0 * top.impressions / insights.lifetime_impressions
            if insights.lifetime_impressions
            else 0.0
        )
        factors.append(
            RationaleFactor(
                claim=f"{top.placement} is this account's strongest placement historically.",
                evidence=(
                    f"{top.placement} drove {share_pct:.0f}% of this account's lifetime "
                    f"impressions at a {top.ctr_pct:.2f}% CTR, the best of any placement on file "
                    f"-- supporting the {format_label.split(' ')[0].lower()} format's placement fit."
                ),
                source="meta_insights",
            )
        )
    return factors


def _creative_plan_factors(plan: CreativePlan | None) -> list[RationaleFactor]:
    if plan is None:
        return []
    return [
        RationaleFactor(claim=decision.choice, evidence=decision.reason, source="creative_plan")
        for decision in plan.decisions
    ]


def build_rationale(
    request: CampaignRequest,
    artifact: CampaignArtifact,
    preview: MetaAdPreview,
    plan: CreativePlan | None,
    *,
    insights: MetaInsightsSummary | None = None,
) -> CampaignRationale:
    """Explain why this campaign was set up this way.

    Works with ``insights=None`` (or an ``available=False`` summary) and
    still produces a useful, honest explanation grounded in the request and
    documented platform defaults -- it just never claims account evidence it
    doesn't have. ``meta_account_grounded`` is True only when at least one
    factor actually came from a real Meta account read.
    """
    factors: list[RationaleFactor] = [
        _objective_factor(preview),
        _budget_factor(request, preview),
        *_audience_factors(insights),
        _cta_factor(request, preview),
        *_format_placement_factors(artifact, insights),
        *_creative_plan_factors(plan),
    ]

    meta_account_grounded = any(factor.source == "meta_insights" for factor in factors)

    grounding_note = (
        "grounded in this account's own performance history plus your inputs"
        if meta_account_grounded
        else "based on Meta platform defaults and your own inputs (no account history was available for this run)"
    )
    summary = (
        f"This {artifact.format.value} campaign for {request.business_name} runs "
        f"{preview.objective} at ${preview.daily_budget_usd:.2f}/day for {preview.days} day(s), "
        f"{grounding_note}."
    )

    return CampaignRationale(
        summary=summary,
        factors=factors,
        meta_account_grounded=meta_account_grounded,
    )
