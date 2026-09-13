"""Tests for src/advantage/adapters/reel_plan.py, the feel-driven edit planner.

Two things matter most here (see reel_plan.py's module docstring):
1. Every string the planner emits (theme/motion/transition/overlay type/
   overlay animation) must be a real member of remotion/library/catalog.ts
   and remotion/types.ts's vocabularies -- a typo there would silently
   render nothing. The catalogs are hard-coded below rather than parsed out
   of the .ts files, since this module must never touch a .tsx/.ts file.
2. Overlays must never overlap in time -- that's the main visual failure
   mode a richer overlay arc introduces.

Nothing here renders for real; `build_edit_spec` is a pure function (no
subprocess calls), which is all these tests exercise.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from advantage.adapters import reel as reel_adapter
from advantage.adapters import reel_plan
from advantage.domain.models import CampaignRequest, CreativeFormat, ReelFeel
from advantage.integrations.google_drive import AssetKind, IntakeAsset, IntakeStatus

# --- remotion/library/catalog.ts + remotion/types.ts vocabularies, hard-coded ---

THEME_CATALOG = {
    "classic", "cinematic", "match_day", "kinetic", "minimal", "youth_energy", "premium", "testimonial",
}
MOTION_CATALOG = {
    "none", "slow_push", "hero_push", "zoom_out", "gentle_drift_left", "gentle_drift_right",
    "pan_up", "pan_down", "handheld",
}
TRANSITION_CATALOG = {
    "none", "soft_dissolve", "brand_wipe", "impact_cut", "wipe_left", "wipe_right", "wipe_up", "wipe_down",
    "slide_left", "slide_right", "push_left", "push_right", "zoom", "flash", "glitch", "shutter", "bars", "iris",
}
OVERLAY_TYPE_CATALOG = {
    "hero_title", "chapter", "lower_third", "stat", "quote", "checklist", "split_headline", "info_chips",
    "location", "badge", "caption", "matchup", "scoreboard", "deadline", "ticker", "closing",
}
OVERLAY_ANIMATION_CATALOG = {
    "fade", "slide_up", "slide_left", "slide_right", "pop", "spring", "mask", "blur", "impact",
}


def _request(**overrides) -> CampaignRequest:
    fields = {
        "business_name": "22 Yards Cricket Academy",
        "brief_text": "Turn our practice footage into a reel",
        "format": CreativeFormat.REEL,
    }
    fields.update(overrides)
    return CampaignRequest(**fields)


def _asset(index: int, duration: float | None = 4.0) -> IntakeAsset:
    return IntakeAsset(
        source_id=f"drive-{index}",
        source_name=f"clip{index}.mp4",
        source_ref="deadbeefcafef00d",
        kind=AssetKind.VIDEO,
        mime_type="video/mp4",
        duration_seconds=duration,
        local_ref=f"clips/{index}.mp4",
        status=IntakeStatus.IMPORTED,
    )


# --- FEEL_PROFILES: every feel maps to real catalog vocabulary -------------


@pytest.mark.parametrize("feel", list(ReelFeel))
def test_every_feel_profile_uses_catalog_vocabulary(feel):
    profile = reel_plan.FEEL_PROFILES[feel]
    assert profile.theme in THEME_CATALOG
    assert profile.default_overlay_animation in OVERLAY_ANIMATION_CATALOG
    assert profile.motion_cycle and set(profile.motion_cycle) <= MOTION_CATALOG
    assert profile.transition_cycle and set(profile.transition_cycle) <= TRANSITION_CATALOG
    assert 0 < profile.min_shot_seconds <= profile.default_shot_seconds <= profile.max_shot_seconds


def test_every_reel_feel_has_a_profile():
    assert set(reel_plan.FEEL_PROFILES) == set(ReelFeel)


# --- plan_reel: pure planning logic -----------------------------------------


def test_plan_reel_rejects_zero_shots():
    with pytest.raises(ValueError):
        reel_plan.plan_reel(_request(), shot_count=0)


@pytest.mark.parametrize("feel", list(ReelFeel))
@pytest.mark.parametrize("shot_count", [1, 2, 3, 4, 6])
def test_plan_reel_produces_a_valid_plan_for_every_feel_and_shot_count(feel, shot_count):
    request = _request(
        reel_feel=feel,
        contact_phone="+1 555 0100",
        location="Houston, TX",
        offer_text="Free trial class",
        key_benefits=["Certified coaches", "Small groups"],
        proof_point="500+ athletes trained since 2019",
        audience="Ages 8-14",
    )

    plan = reel_plan.plan_reel(request, shot_count)

    assert plan.theme in THEME_CATALOG
    assert plan.default_overlay_animation in OVERLAY_ANIMATION_CATALOG
    assert len(plan.shot_motions) == shot_count
    assert len(plan.shot_transitions) == shot_count
    assert set(plan.shot_motions) <= MOTION_CATALOG
    assert set(plan.shot_transitions) <= TRANSITION_CATALOG

    # Every interior beat is pinned to an interior shot -- never shot 0 (the
    # hero's) or the last shot (the closing card's).
    for beat in plan.interior_beats:
        assert beat.overlay["type"] in OVERLAY_TYPE_CATALOG
        assert 0 < beat.shot_index < shot_count - 1


@pytest.mark.parametrize("feel", list(ReelFeel))
@pytest.mark.parametrize("shot_count", [1, 2, 3, 4, 5, 6, 8])
def test_interior_beats_never_overlap_within_a_shot(feel, shot_count):
    # A request that qualifies for every optional beat, to stress the
    # assignment logic as hard as possible.
    request = _request(
        reel_feel=feel,
        contact_phone="+1 555 0100",
        location="Houston, TX",
        offer_text="Free trial class",
        offer_expires_at=datetime(2026, 10, 1),
        key_benefits=["Certified coaches", "Small groups"],
        proof_point="500+ athletes trained",
        audience="Ages 8-14",
    )
    plan = reel_plan.plan_reel(request, shot_count)
    by_shot: dict[int, list] = {}
    for beat in plan.interior_beats:
        by_shot.setdefault(beat.shot_index, []).append(beat)
    for beats in by_shot.values():
        ordered = sorted(beats, key=lambda b: b.start_fraction)
        for earlier, later in zip(ordered, ordered[1:]):
            assert later.start_fraction >= earlier.start_fraction + earlier.duration_fraction


# --- overlay content: routed from real request facts, never invented -------


def test_key_benefits_alone_produce_a_checklist_beat_capped_at_four_items():
    request = _request(
        key_benefits=[
            "Certified coaches", "Small group training", "Match-day experience",
            "Video breakdowns", "A fifth benefit that should be dropped",
        ],
        footage_assets=[_asset(0), _asset(1), _asset(2)],
    )

    spec = reel_adapter.build_edit_spec(request)

    checklist = next(o for o in spec["overlays"] if o["type"] == "checklist")
    assert checklist["items"] == [
        "Certified coaches", "Small group training", "Match-day experience", "Video breakdowns",
    ]


def test_numeric_proof_point_becomes_stat_for_a_stat_preferring_feel():
    request = _request(
        reel_feel=ReelFeel.HIGH_ENERGY,
        proof_point="500+ athletes trained since 2019",
        footage_assets=[_asset(0), _asset(1), _asset(2)],
    )

    spec = reel_adapter.build_edit_spec(request)

    stat = next(o for o in spec["overlays"] if o["type"] == "stat")
    assert stat["value"] == "500+"


def test_proof_point_becomes_a_quote_for_a_quote_preferring_feel():
    request = _request(
        reel_feel=ReelFeel.WARM_TESTIMONIAL,
        proof_point="Coach Sam changed how my son sees the game.",
        footage_assets=[_asset(0), _asset(1), _asset(2)],
    )

    spec = reel_adapter.build_edit_spec(request)

    quote = next(o for o in spec["overlays"] if o["type"] == "quote")
    assert quote["quote"].startswith("Coach Sam")


def test_audience_only_fallback_produces_a_lower_third_beat():
    request = _request(
        audience="Ages 8-14",
        footage_assets=[_asset(0), _asset(1), _asset(2)],
    )

    spec = reel_adapter.build_edit_spec(request)

    lower_third = next(o for o in spec["overlays"] if o["type"] == "lower_third")
    assert lower_third["title"] == "AGES 8-14"


def test_offer_expires_at_produces_a_deadline_beat():
    request = _request(
        offer_expires_at=datetime(2026, 10, 1),
        footage_assets=[_asset(0), _asset(1), _asset(2)],
    )

    spec = reel_adapter.build_edit_spec(request)

    deadline = next(o for o in spec["overlays"] if o["type"] == "deadline")
    assert deadline["date"] == "Oct 01"


def test_offer_text_without_a_deadline_produces_a_badge_beat():
    request = _request(
        offer_text="Free trial class",
        footage_assets=[_asset(0), _asset(1), _asset(2)],
    )

    spec = reel_adapter.build_edit_spec(request)

    badge = next(o for o in spec["overlays"] if o["type"] == "badge")
    assert badge["text"] == "FREE TRIAL CLASS"


def test_location_only_produces_a_location_beat():
    request = _request(
        location="Houston, TX",
        footage_assets=[_asset(0), _asset(1), _asset(2)],
    )

    spec = reel_adapter.build_edit_spec(request)

    location_overlay = next(o for o in spec["overlays"] if o["type"] == "location")
    assert location_overlay["location"] == "Houston, TX"


def test_phone_and_location_together_produce_an_info_chips_beat():
    request = _request(
        location="Houston, TX",
        contact_phone="+1 555 0100",
        footage_assets=[_asset(0), _asset(1), _asset(2)],
    )

    spec = reel_adapter.build_edit_spec(request)

    chips = next(o for o in spec["overlays"] if o["type"] == "info_chips")
    assert {item["label"] for item in chips["items"]} == {"Location", "Call"}


def test_urgent_offer_prioritises_the_offer_beat_over_the_narrative_beat():
    request = _request(
        reel_feel=ReelFeel.URGENT_OFFER,
        offer_text="Free trial class",
        key_benefits=["Certified coaches"],
        footage_assets=[_asset(0), _asset(1), _asset(2)],  # exactly one interior shot
    )

    spec = reel_adapter.build_edit_spec(request)

    interior_types = [o["type"] for o in spec["overlays"] if o["type"] not in ("hero_title", "closing")]
    assert interior_types == ["badge"]


def test_other_feels_prioritise_the_narrative_beat_over_the_offer_beat():
    request = _request(
        reel_feel=ReelFeel.CINEMATIC,
        offer_text="Free trial class",
        key_benefits=["Certified coaches"],
        footage_assets=[_asset(0), _asset(1), _asset(2)],  # exactly one interior shot
    )

    spec = reel_adapter.build_edit_spec(request)

    interior_types = [o["type"] for o in spec["overlays"] if o["type"] not in ("hero_title", "closing")]
    assert interior_types == ["checklist"]


def test_no_benefits_no_proof_no_offer_still_produces_a_valid_two_overlay_reel():
    """The mandated floor: a request carrying none of the optional facts
    still produces a clean hook -> CTA reel, not an empty or broken one."""
    request = _request(footage_assets=[_asset(0), _asset(1), _asset(2)])

    spec = reel_adapter.build_edit_spec(request)

    assert [o["type"] for o in spec["overlays"]] == ["hero_title", "closing"]


# --- hero_title.line2: the regression this whole module is careful about ---


@pytest.mark.parametrize("feel", list(ReelFeel))
def test_hero_line2_never_exceeds_20_chars(feel):
    request = _request(
        reel_feel=feel,
        offer_text="A very long offer sentence that definitely exceeds twenty characters",
        footage_assets=[_asset(0), _asset(1)],
    )

    spec = reel_adapter.build_edit_spec(request)

    hero = next(o for o in spec["overlays"] if o["type"] == "hero_title")
    assert len(hero["line2"]) <= reel_plan.HERO_LINE2_MAX_CHARS


# --- build_edit_spec: the actual production path, exercised end to end ------


@pytest.mark.parametrize("feel", list(ReelFeel))
def test_every_feel_produces_a_valid_edit_spec(feel):
    request = _request(
        reel_feel=feel,
        contact_phone="+1 555 0100",
        location="Houston, TX",
        offer_text="Free trial class",
        offer_expires_at=datetime(2026, 10, 1),
        key_benefits=["Certified coaches", "Small groups"],
        proof_point="500+ athletes trained",
        audience="Ages 8-14",
        footage_assets=[_asset(i) for i in range(5)],
    )

    spec = reel_adapter.build_edit_spec(request)

    assert spec["style"]["theme"] in THEME_CATALOG
    assert spec["style"]["defaultOverlayAnimation"] in OVERLAY_ANIMATION_CATALOG
    for shot in spec["shots"]:
        assert shot["motion"] in MOTION_CATALOG
        assert shot["transition"] in TRANSITION_CATALOG
    for overlay in spec["overlays"]:
        assert overlay["type"] in OVERLAY_TYPE_CATALOG


@pytest.mark.parametrize("feel", list(ReelFeel))
@pytest.mark.parametrize("shot_count", [1, 2, 3, 5])
def test_overlays_never_overlap_on_the_real_timeline(feel, shot_count):
    request = _request(
        reel_feel=feel,
        contact_phone="+1 555 0100",
        location="Houston, TX",
        offer_text="Free trial class",
        offer_expires_at=datetime(2026, 10, 1),
        key_benefits=["Certified coaches", "Small groups"],
        proof_point="500+ athletes trained",
        audience="Ages 8-14",
        footage_assets=[_asset(i) for i in range(shot_count)],
    )

    spec = reel_adapter.build_edit_spec(request)

    intervals = sorted((o["start"], o["start"] + o["duration"]) for o in spec["overlays"])
    for (_, earlier_end), (later_start, _) in zip(intervals, intervals[1:]):
        assert later_start >= earlier_end - 1e-6


# --- describe_plan: the UI-facing explanation --------------------------------


def test_describe_plan_returns_one_reason_per_real_decision():
    request = _request(
        reel_feel=ReelFeel.URGENT_OFFER,
        offer_text="Free trial class",
        offer_expires_at=datetime(2026, 10, 1),
        key_benefits=["Certified coaches"],
    )

    plan = reel_plan.describe_plan(request, shot_count=4)

    assert plan.format == CreativeFormat.REEL
    assert plan.feel == ReelFeel.URGENT_OFFER.value
    assert len(plan.decisions) >= 4
    assert all(decision.choice and decision.reason for decision in plan.decisions)


def test_describe_plan_defaults_to_high_energy_when_reel_feel_is_unset():
    plan = reel_plan.describe_plan(_request(), shot_count=2)
    assert plan.feel == ReelFeel.HIGH_ENERGY.value


def test_describe_plan_explains_skipped_beats():
    request = _request()  # no key_benefits/proof_point/audience/offer/contact/location

    plan = reel_plan.describe_plan(request, shot_count=3)

    skipped_choices = [d.choice for d in plan.decisions if d.choice.startswith("Skipped:")]
    assert any("narrative" in choice for choice in skipped_choices)
    assert any("offer" in choice for choice in skipped_choices)
    assert any("contact" in choice for choice in skipped_choices)
