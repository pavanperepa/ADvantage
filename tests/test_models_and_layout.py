from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from cricket_posts.layout import (
    allowed_layouts,
    choose_density,
    choose_layout,
    content_density_score,
    ideogram_only_assessment,
    infer_visual_intents,
    plan_design,
)
from cricket_posts.models import (
    BrandProfile,
    ColorMode,
    CompositionMode,
    Density,
    DesignSpec,
    FontPreset,
    InformationContent,
    LayoutFamily,
    Palette,
    VisualTreatment,
    parse_editable_content,
    parse_poster_content,
    protect_all_copy,
)
from cricket_posts.openai_studio import (
    CriticResult,
    ExtractedPoster,
    ExtractedPosterContent,
    TokenPatch,
    apply_critic_patch,
    extraction_to_content,
    verify_plain_source_coverage,
    verify_source_copy,
)
from cricket_posts.renderer import PROJECT_ROOT


FIXTURES = [
    "information.json",
    "tournament-registration.json",
    "coaching-services.json",
    "lane-rental.json",
    "summer-camp.json",
    "svats-cup.json",
]


@pytest.mark.parametrize("filename", FIXTURES)
def test_fixture_copy_can_be_fully_protected(filename, load_content):
    content = protect_all_copy(load_content(filename))
    visible = "\n".join(content.display_strings())
    assert content.protected_copy
    assert all(value in visible for value in content.protected_copy)


@pytest.mark.parametrize(
    ("filename", "family"),
    [
        ("information.json", LayoutFamily.ANNOUNCEMENT_HERO),
        ("tournament-registration.json", LayoutFamily.TOURNAMENT_REGISTRATION),
        ("svats-cup.json", LayoutFamily.TOURNAMENT_CATEGORY_GRID),
        ("summer-camp.json", LayoutFamily.SUMMER_CAMP),
        ("coaching-services.json", LayoutFamily.COACHING_SERVICES),
        ("lane-rental.json", LayoutFamily.LANE_RENTAL),
    ],
)
def test_layout_registry_covers_six_single_page_families(filename, family, load_content):
    content = load_content(filename)
    assert choose_layout(content) == family
    assert family in allowed_layouts(content)
    assert choose_density(content) in set(Density)
    assert content_density_score(content) > 0


def test_protected_copy_cannot_reference_missing_text():
    with pytest.raises(ValidationError):
        InformationContent(title="Opening Hours", protected_copy=["Changed Date"])


def test_editable_content_replaces_stale_protection():
    edited = parse_editable_content(
        {
            "content_type": "information",
            "title": "Updated Opening Hours",
            "protected_copy": ["Old Opening Hours"],
        }
    )
    protected = protect_all_copy(edited)
    assert protected.protected_copy == ["Updated Opening Hours"]


def test_source_verification_detects_rewritten_fact():
    content = InformationContent(
        title="Summer Cup",
        detail_lines=["July 26, 2026"],
    )
    missing = verify_source_copy(
        content,
        "Summer Cup\nDate: July 25, 2026",
    )
    assert missing == ["July 26, 2026"]


def test_plain_source_coverage_detects_omitted_line():
    content = InformationContent(
        title="FOUNDATION PROGRAM NOW OPEN!",
        subtitle="BEGIN THEIR CRICKET JOURNEY WITH US!",
    )
    missing = verify_plain_source_coverage(
        content,
        "FOUNDATION PROGRAM NOW OPEN!\n"
        "BEGIN THEIR CRICKET JOURNEY WITH US!\n"
        "STRONG START. BRIGHT FUTURE.",
    )
    assert missing == ["STRONG START. BRIGHT FUTURE."]


def test_foundation_program_uses_vignette_and_semantic_intents():
    payload = json.loads(
        (PROJECT_ROOT / "fixtures" / "foundation-program-houston.json").read_text(
            encoding="utf-8"
        )
    )
    content = parse_poster_content(payload["content"])
    design = plan_design(content, BrandProfile.model_validate(payload["brand"]))
    intent_by_text = {
        intent.source_text: intent.kind.value for intent in design.visual_intents
    }

    assert design.visual_treatment == VisualTreatment.VIGNETTE
    assert design.font_preset == FontPreset.MODERN
    assert design.color_mode == ColorMode.DARK
    assert intent_by_text["BUILD STRONG FUNDAMENTALS"] == "strength"
    assert intent_by_text["IMPROVE COORDINATION"] == "coordination"
    assert intent_by_text["LEARN THE GAME THE RIGHT WAY"] == "learning"
    assert intent_by_text["FUN & ENGAGING ENVIRONMENT"] == "fun"


def test_every_fun_experience_claim_receives_a_specific_visual_intent():
    payload = json.loads(
        (PROJECT_ROOT / "fixtures" / "foundation-fun-houston.json").read_text(
            encoding="utf-8"
        )
    )
    content = parse_poster_content(payload["content"])
    intents = {
        intent.source_text: intent.kind.value
        for intent in infer_visual_intents(content)
    }
    claims = content.sections[0].items

    assert set(claims).issubset(intents)
    assert all(intents[claim] != "generic" for claim in claims)
    assert intents["FRIENDLY COACHES WHO KEEP IT SIMPLE"] == "coaching"
    assert intents["MAKE NEW FRIENDS & FEEL INCLUDED"] == "friendship"
    assert (
        intents["LEAVE MORE COMFORTABLE, CONFIDENT & EXCITED TO PLAY AGAIN"]
        == "confidence"
    )


def test_openai_extraction_schema_avoids_unsupported_one_of():
    schema = json.dumps(ExtractedPoster.model_json_schema())
    assert '"oneOf"' not in schema


def test_flat_extraction_converts_to_domain_model_without_rewriting():
    extracted = ExtractedPosterContent(
        content_type="camp",
        title="winter training program",
        price_line="250$ price",
        detail_lines=["250$ price", "ages 8-18"],
        schedule={
            "date": "dec 1-30",
            "days": "mon to thrusday",
            "time": "5pm to 630 pm - 16 classes",
        },
        sections=[
            {
                "heading": "PROGRAM",
                "text": "our classes will consist of all the performance boosting activiteis",
            }
        ],
    )
    content = extraction_to_content(extracted)
    assert content.content_type.value == "camp"
    assert content.title == "winter training program"
    assert content.schedule is not None
    assert content.schedule.time == "5pm to 630 pm - 16 classes"
    assert content.price_line == "250$ price"
    assert content.detail_lines == ["250$ price", "ages 8-18"]


def test_light_program_selects_art_forward_and_allows_ideogram_only():
    content = extraction_to_content(
        ExtractedPosterContent(
            content_type="camp",
            title="winter training program",
            price_line="250$ price",
            schedule={
                "display_text": "dec 1-30 mon to thrusday 5pm to 630 pm - 16 classes"
            },
            detail_lines=["ages 8-18"],
            sections=[
                {
                    "text": "we are going to develop personliazed porgram that will get them to the next elvel"
                },
                {
                    "text": "our classes will consist of all the performance boosting activiteis"
                },
            ],
        )
    )
    design = plan_design(content, BrandProfile(name="22 Yards Houston"))
    assessment = ideogram_only_assessment(content)

    assert design.density == Density.SPACIOUS
    assert design.composition == CompositionMode.ART_FORWARD
    assert assessment["eligible"] is True
    assert assessment["line_count"] <= 14


def test_dense_tournament_disallows_ideogram_only(load_content):
    content = load_content("svats-cup.json")
    assessment = ideogram_only_assessment(content)
    assert assessment["eligible"] is False
    assert assessment["density"] == "dense"
    assert any("multi-category" in reason for reason in assessment["reasons"])


def test_critic_can_only_change_bounded_tokens(load_content):
    content = load_content("information.json")
    brand = BrandProfile(name="Test")
    design = plan_design(content, brand)
    result = CriticResult(
        pass_required=True,
        issues=["Move artwork slightly right."],
        token_patch=TokenPatch(art_position_x=62, panel_opacity=0.92),
    )
    updated = apply_critic_patch(design, result)
    assert updated.family == design.family
    assert updated.density == design.density
    assert updated.art_prompt == design.art_prompt
    assert updated.tokens.art_position_x == 62
    assert updated.tokens.panel_opacity == 0.92


def test_planner_cannot_select_disallowed_layout(load_content):
    content = load_content("information.json")
    brand = BrandProfile(name="Test")
    design = plan_design(
        content,
        brand,
        {
            "family": "summer_camp",
            "density": "dense",
            "art_prompt": "A" * 80,
        },
    )
    assert design.family == LayoutFamily.ANNOUNCEMENT_HERO


def test_fixture_json_uses_no_carousel_interface():
    for path in (PROJECT_ROOT / "fixtures").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "carousel" not in json.dumps(payload).lower()
