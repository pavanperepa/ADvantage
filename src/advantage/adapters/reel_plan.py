"""The feel-driven edit planner for reels.

`adapters/reel.py` is glue: it shells out to `prepare_remotion_media.py` and
the Remotion CLI. This module is the actual editorial brain -- it turns one
`CampaignRequest.reel_feel` choice into a full edit plan (Remotion theme,
shot motion/transition cycle, shot pacing, and which of
`remotion/library`'s overlay types tell this reel's story) using only facts
the request itself carries. It never invents copy: every overlay field below
traces back to a real `CampaignRequest` field, or is generic UI chrome (e.g.
"BUILT FOR", "OFFER ENDS") in the same spirit as the pre-existing "TAP THE
LINK TO SIGN UP" action text.

Two rules drove every choice of text-field length limits below:
1. `remotion/library/overlays.tsx` components size big display text by
   character-count brackets (e.g. `HookTitle.line2` jumps from 82px to 120px
   under 20 chars) with no line-count cap -- so an unexpectedly long string
   doesn't wrap politely, it blows past its region into whatever renders
   next. See docs/P1_PROGRESS.md bug #2, the reason `HERO_LINE2_MAX_CHARS`
   exists at all.
2. Several fields (`Badge.text`, `LowerThird.title`, `StatCards` value/label)
   sit in flex layouts with no `maxWidth`, so the same risk applies to them
   even though no one has hit it yet. Every field fed from request text below
   is clipped at a real word boundary (never fabricated) for exactly this
   reason -- see `_clip_words`.

Overlays never overlap in time: `plan_reel` pins each optional interior beat
to its own interior shot index (never shot 0, which the hero owns, or the
last shot, which the closing card owns), so no two beats can ever share a
timeline window. `_assert_no_overlap` re-checks this by construction rather
than trusting the invariant silently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..domain.models import CampaignRequest, CreativeDecision, CreativeFormat, CreativePlan, ReelFeel

# --- text-safety clamps -----------------------------------------------------
# See the module docstring for why these exist. All values are conservative
# guesses at "stays on one comfortable line for this component", not measured
# pixel budgets -- band-aid insurance, not a layout engine.
HERO_LINE2_MAX_CHARS = 20
BADGE_TEXT_MAX_CHARS = 18
LOWER_THIRD_TITLE_MAX_CHARS = 28
CHECKLIST_ITEM_MAX_CHARS = 42
CHECKLIST_MAX_ITEMS = 4
STAT_VALUE_MAX_CHARS = 12
STAT_LABEL_MAX_CHARS = 28
QUOTE_MAX_CHARS = 160
DEADLINE_LABEL_MAX_CHARS = 24
DEADLINE_DATE_MAX_CHARS = 24
CONTACT_VALUE_MAX_CHARS = 40

HERO_OVERLAY_MAX_SECONDS = 3.0

DEFAULT_FEEL = ReelFeel.HIGH_ENERGY


def _clip_words(text: str, max_chars: int) -> str:
    """Clip to a real word boundary within max_chars.

    Never fabricates a phrase -- always less of the business's own supplied
    text, same contract as the pre-existing hero-line2 clamp this generalizes.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0]
    return truncated or text[:max_chars]


def short_hook(text: str) -> str:
    """The opening hook's punch line: real supplied text, clipped to
    HERO_LINE2_MAX_CHARS -- see docs/P1_PROGRESS.md bug #2."""
    return _clip_words(text.strip().upper(), HERO_LINE2_MAX_CHARS)


# --- per-feel profile --------------------------------------------------------


@dataclass(frozen=True)
class FeelProfile:
    """The fixed choices one `ReelFeel` makes across the library.

    `motion_cycle`/`transition_cycle` are ordered cycles (see
    `remotion/library/catalog.ts`), not a scoring algorithm -- same spirit as
    the flat cycle `reel.py` used before this, just one per feel instead of
    one for everybody.
    """

    theme: str
    motion_cycle: tuple[str, ...]
    transition_cycle: tuple[str, ...]
    default_overlay_animation: str
    min_shot_seconds: float
    max_shot_seconds: float
    default_shot_seconds: float
    prefers_stat: bool
    lean_on_offer: bool


FEEL_PROFILES: dict[ReelFeel, FeelProfile] = {
    ReelFeel.HIGH_ENERGY: FeelProfile(
        theme="kinetic",
        motion_cycle=("hero_push", "handheld", "zoom_out"),
        transition_cycle=("impact_cut", "flash", "glitch"),
        default_overlay_animation="pop",
        min_shot_seconds=1.8,
        max_shot_seconds=2.8,
        default_shot_seconds=2.2,
        prefers_stat=True,
        lean_on_offer=False,
    ),
    ReelFeel.CINEMATIC: FeelProfile(
        theme="cinematic",
        motion_cycle=("slow_push", "gentle_drift_left", "pan_up"),
        transition_cycle=("soft_dissolve", "wipe_down", "iris"),
        default_overlay_animation="fade",
        min_shot_seconds=4.0,
        max_shot_seconds=6.0,
        default_shot_seconds=5.0,
        prefers_stat=False,
        lean_on_offer=False,
    ),
    ReelFeel.WARM_TESTIMONIAL: FeelProfile(
        theme="testimonial",
        motion_cycle=("slow_push", "gentle_drift_right", "pan_down"),
        transition_cycle=("soft_dissolve", "wipe_left", "soft_dissolve"),
        default_overlay_animation="blur",
        min_shot_seconds=3.5,
        max_shot_seconds=5.0,
        default_shot_seconds=4.2,
        prefers_stat=False,
        lean_on_offer=False,
    ),
    ReelFeel.URGENT_OFFER: FeelProfile(
        theme="match_day",
        motion_cycle=("hero_push", "zoom_out", "handheld"),
        transition_cycle=("flash", "impact_cut", "shutter"),
        default_overlay_animation="impact",
        min_shot_seconds=2.0,
        max_shot_seconds=3.2,
        default_shot_seconds=2.5,
        prefers_stat=True,
        lean_on_offer=True,
    ),
    ReelFeel.CLEAN_EXPLAINER: FeelProfile(
        theme="minimal",
        motion_cycle=("none", "slow_push", "none"),
        transition_cycle=("soft_dissolve", "wipe_right", "soft_dissolve"),
        default_overlay_animation="fade",
        min_shot_seconds=3.0,
        max_shot_seconds=4.5,
        default_shot_seconds=3.6,
        prefers_stat=False,
        lean_on_offer=False,
    ),
}


# --- plan shape --------------------------------------------------------------


@dataclass(frozen=True)
class OverlayBeat:
    """One optional interior overlay.

    `shot_index` is always an *interior* shot (never the first shot, which
    the hero owns, or the last, which the closing card owns) so no two beats
    -- and no beat and the hero/closing -- can ever occupy the same window.
    `start_fraction`/`duration_fraction` describe where within that shot's
    own timeline the overlay sits (fractions, not seconds, since the planner
    doesn't know real per-shot durations -- `reel.py` resolves them against
    the actual computed shot timeline).
    """

    shot_index: int
    start_fraction: float
    duration_fraction: float
    overlay: dict[str, Any]
    reason: str


@dataclass(frozen=True)
class ReelPlan:
    feel: ReelFeel
    theme: str
    default_overlay_animation: str
    min_shot_seconds: float
    max_shot_seconds: float
    default_shot_seconds: float
    shot_motions: list[str]
    shot_transitions: list[str]
    include_hero: bool
    hero_reason: str
    interior_beats: list[OverlayBeat]
    skipped: list[tuple[str, str]]


def plan_reel(request: CampaignRequest, shot_count: int) -> ReelPlan:
    """Pure function: no I/O, no subprocess calls. Builds the per-shot
    motion/transition cycle and the overlay arc for `shot_count` shots.

    `shot_count` should be the number of usable footage assets `reel.py` is
    about to lay out (it may end up building fewer real shots than this if
    MAX_TOTAL_SECONDS trims the tail -- `reel.py` drops any interior beat
    that lands past the real last shot rather than let it collide with the
    closing card).
    """
    if shot_count < 1:
        raise ValueError("plan_reel requires at least one shot")

    feel = request.reel_feel or DEFAULT_FEEL
    profile = FEEL_PROFILES[feel]

    shot_motions = [profile.motion_cycle[i % len(profile.motion_cycle)] for i in range(shot_count)]
    shot_transitions = [profile.transition_cycle[i % len(profile.transition_cycle)] for i in range(shot_count)]

    include_hero = shot_count > 1
    hero_reason = (
        "Only one shot -- it's too short to carry both a hook and the closing "
        "CTA without them colliding, so the CTA wins the only slot."
        if not include_hero
        else "Opening shot carries the hero hook so the promise lands before the first cut."
    )

    # Never shot 0 (hero) or the last shot (closing) -- see OverlayBeat docstring.
    interior_indices = list(range(1, shot_count - 1)) if shot_count > 2 else []

    skipped: list[tuple[str, str]] = []
    candidates: list[tuple[str, dict[str, Any], str]] = []

    # --- mid-reel narrative beat ---
    if request.key_benefits:
        items = [_clip_words(b, CHECKLIST_ITEM_MAX_CHARS) for b in request.key_benefits[:CHECKLIST_MAX_ITEMS]]
        candidates.append((
            "narrative:checklist",
            {"type": "checklist", "title": "WHAT YOU GET", "items": items},
            f"request.key_benefits has {len(request.key_benefits)} item(s); shown as a checklist beat.",
        ))
    elif request.proof_point:
        proof = request.proof_point.strip()
        stat_match = re.match(r"^([\d][\w+%./-]*)\s*(.*)$", proof) if profile.prefers_stat else None
        if stat_match and stat_match.group(1):
            value = _clip_words(stat_match.group(1), STAT_VALUE_MAX_CHARS)
            label = _clip_words(stat_match.group(2) or proof, STAT_LABEL_MAX_CHARS)
            candidates.append((
                "narrative:stat",
                {"type": "stat", "value": value, "label": label},
                "proof_point starts with a number and this feel favours punchy stat cards over a quote.",
            ))
        else:
            candidates.append((
                "narrative:quote",
                {"type": "quote", "quote": _clip_words(proof, QUOTE_MAX_CHARS)},
                "proof_point read as a testimonial/quote, not a number.",
            ))
    elif request.audience:
        candidates.append((
            "narrative:lower_third",
            {
                "type": "lower_third",
                "eyebrow": "BUILT FOR",
                "title": _clip_words(request.audience.upper(), LOWER_THIRD_TITLE_MAX_CHARS),
            },
            "No key_benefits or proof_point supplied; fell back to the request's own audience field.",
        ))
    else:
        skipped.append((
            "narrative beat",
            "Request has no key_benefits, proof_point, or audience -- nothing to show without inventing copy.",
        ))

    # --- offer beat ---
    if request.offer_expires_at is not None:
        candidates.append((
            "offer:deadline",
            {
                "type": "deadline",
                "label": _clip_words("OFFER ENDS", DEADLINE_LABEL_MAX_CHARS),
                "date": _clip_words(request.offer_expires_at.strftime("%b %d"), DEADLINE_DATE_MAX_CHARS),
            },
            "offer_expires_at is set, so the deadline earns its own beat.",
        ))
    elif request.offer_text:
        candidates.append((
            "offer:badge",
            {"type": "badge", "text": _clip_words(request.offer_text.upper(), BADGE_TEXT_MAX_CHARS)},
            "offer_text is set; a badge flags the offer apart from the closing card's headline.",
        ))
    else:
        skipped.append(("offer beat", "No offer_text or offer_expires_at on the request."))

    # --- contact beat ---
    contact_items: list[dict[str, str]] = []
    if request.location:
        contact_items.append({"label": "Location", "value": _clip_words(request.location, CONTACT_VALUE_MAX_CHARS)})
    if request.contact_phone:
        contact_items.append({"label": "Call", "value": _clip_words(request.contact_phone, CONTACT_VALUE_MAX_CHARS)})
    if len(contact_items) == 1 and contact_items[0]["label"] == "Location":
        candidates.append((
            "contact:location",
            {"type": "location", "location": contact_items[0]["value"]},
            "location is set; a compact location card reinforces it beyond the closing card.",
        ))
    elif contact_items:
        candidates.append((
            "contact:info_chips",
            {"type": "info_chips", "items": contact_items},
            "contact_phone/location are set; chips reinforce them beyond the closing card.",
        ))
    else:
        skipped.append(("contact beat", "No contact_phone or location on the request."))

    if profile.lean_on_offer:
        candidates.sort(key=lambda item: 0 if item[0].startswith("offer:") else 1)

    interior_beats: list[OverlayBeat] = []
    for position, (label, overlay, reason) in enumerate(candidates):
        if position >= len(interior_indices):
            skipped.append((
                label,
                "Chosen, but there was no free interior shot left to carry it without overlapping another beat.",
            ))
            continue
        interior_beats.append(
            OverlayBeat(
                shot_index=interior_indices[position],
                start_fraction=0.0,
                duration_fraction=1.0,
                overlay=overlay,
                reason=reason,
            )
        )

    _assert_no_overlap(interior_beats)

    return ReelPlan(
        feel=feel,
        theme=profile.theme,
        default_overlay_animation=profile.default_overlay_animation,
        min_shot_seconds=profile.min_shot_seconds,
        max_shot_seconds=profile.max_shot_seconds,
        default_shot_seconds=profile.default_shot_seconds,
        shot_motions=shot_motions,
        shot_transitions=shot_transitions,
        include_hero=include_hero,
        hero_reason=hero_reason,
        interior_beats=interior_beats,
        skipped=skipped,
    )


def _assert_no_overlap(beats: list[OverlayBeat]) -> None:
    """Each beat is pinned to its own interior shot index by construction, so
    this can never fire -- it exists so a future change to the assignment
    logic above fails loudly instead of silently producing a colliding edit."""
    by_shot: dict[int, list[OverlayBeat]] = {}
    for beat in beats:
        by_shot.setdefault(beat.shot_index, []).append(beat)
    for shot_index, shot_beats in by_shot.items():
        ordered = sorted(shot_beats, key=lambda b: b.start_fraction)
        for earlier, later in zip(ordered, ordered[1:]):
            earlier_end = earlier.start_fraction + earlier.duration_fraction
            assert later.start_fraction >= earlier_end - 1e-9, (
                f"Overlay beats on shot {shot_index} overlap: "
                f"{earlier.overlay['type']} [{earlier.start_fraction}, {earlier_end}) vs "
                f"{later.overlay['type']} [{later.start_fraction}, {later.start_fraction + later.duration_fraction})"
            )


def describe_plan(request: CampaignRequest, shot_count: int) -> CreativePlan:
    """The same decisions `plan_reel` made, in the shape the UI shows the
    owner: one `CreativeDecision` per real choice, including the ones the
    planner considered and left out (and why)."""
    plan = plan_reel(request, shot_count)

    decisions: list[CreativeDecision] = [
        CreativeDecision(
            choice=f"Theme: {plan.theme}",
            reason=f"reel_feel={plan.feel.value} maps to the '{plan.theme}' Remotion theme.",
        ),
        CreativeDecision(
            choice=f"Pacing: {plan.min_shot_seconds:.1f}-{plan.max_shot_seconds:.1f}s per shot",
            reason=f"'{plan.feel.value}' cuts shots on this band instead of one fixed length for every feel.",
        ),
        CreativeDecision(
            choice=f"Transition cycle: {', '.join(dict.fromkeys(plan.shot_transitions))}",
            reason="Cycled across shots (remotion/library/catalog.ts) instead of one flat transition.",
        ),
        CreativeDecision(
            choice="Opening hook (hero_title)" if plan.include_hero else "No opening hook",
            reason=plan.hero_reason,
        ),
    ]
    for beat in plan.interior_beats:
        decisions.append(CreativeDecision(choice=f"Overlay: {beat.overlay['type']}", reason=beat.reason))
    for label, reason in plan.skipped:
        decisions.append(CreativeDecision(choice=f"Skipped: {label}", reason=reason))
    decisions.append(
        CreativeDecision(
            choice="Closing CTA (closing)",
            reason="Always present -- carries the offer headline and action, and wraps cleanly at any length.",
        )
    )

    return CreativePlan(format=CreativeFormat.REEL, feel=plan.feel.value, decisions=decisions)
