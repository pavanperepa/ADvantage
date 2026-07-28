from __future__ import annotations

from typing import Any

from .models import (
    BrandProfile,
    CampContent,
    CoachingContent,
    ColorMode,
    CompositionMode,
    ContentType,
    Density,
    DesignSpec,
    DesignTokens,
    FontPreset,
    InformationContent,
    IntentKind,
    LaneRentalContent,
    LayoutFamily,
    PosterContent,
    StyleIntent,
    TournamentContent,
    VisualIntent,
    VisualTreatment,
)
from .theme import build_theme


NO_TEXT_GUARDRAIL = (
    "Background artwork only. Include zero readable typography and zero pseudo-typography: "
    "no text, letters, words, numbers, labels, signs, banners, logos, brand marks, jersey "
    "writing, captions, interface elements, borders, or watermarks. Clothing is unbranded."
)


def poster_copy_lines(
    content: PosterContent,
    brand: BrandProfile | None = None,
) -> list[str]:
    lines: list[str] = []

    def add(*values: str) -> None:
        for value in values:
            clean = value.strip()
            if clean:
                lines.append(clean)

    add(content.organization or (brand.name if brand else ""))
    add(content.eyebrow, content.title, content.subtitle, content.tagline)
    if isinstance(content, TournamentContent):
        add(content.short_name, content.organizer_tagline)
    if content.schedule:
        add(content.schedule.display())
    add(content.price_line)
    if isinstance(content, CampContent):
        add(content.program_info)
    for detail in content.detail_lines:
        add(detail)
    for section in content.sections:
        add(section.heading, section.text)
        for item in section.items:
            add(item)
    if isinstance(content, CampContent):
        add(content.coach_heading, content.coach_bio)
    if isinstance(content, TournamentContent):
        for category in content.categories:
            add(category.name, category.registration_fee)
            for prize in category.prizes:
                add(prize.display())
            add(category.awards_heading)
            for award in category.awards:
                add(award)
            for contact in category.contacts:
                add(contact.display())
    for location in content.location_lines:
        add(location)
    for contact in content.contacts:
        add(contact.display())
    for cta in content.cta_lines:
        add(cta)
    if brand:
        add(brand.tagline)
        if not content.location_lines:
            add(brand.location)
        for contact in brand.contact_lines:
            add(contact)
    return list(dict.fromkeys(lines))


def content_density_score(content: PosterContent) -> int:
    lines = poster_copy_lines(content)
    character_score = sum(len(value) for value in lines)
    structure_score = len(lines) * 18 + len(content.sections) * 32
    category_score = (
        len(content.categories) * 120 if isinstance(content, TournamentContent) else 0
    )
    return character_score + structure_score + category_score


def choose_density(content: PosterContent) -> Density:
    score = content_density_score(content)
    if score < 600:
        return Density.SPACIOUS
    if score < 1450:
        return Density.COMPACT
    return Density.DENSE


def choose_composition(content: PosterContent) -> CompositionMode:
    density = choose_density(content)
    if density == Density.SPACIOUS:
        return CompositionMode.ART_FORWARD
    if density == Density.COMPACT:
        return CompositionMode.BALANCED
    return CompositionMode.INFORMATION_DENSE


def choose_visual_treatment(content: PosterContent) -> VisualTreatment:
    return (
        VisualTreatment.HERO
        if choose_density(content) == Density.SPACIOUS
        else VisualTreatment.VIGNETTE
    )


def choose_font_preset(content: PosterContent) -> FontPreset:
    if content.content_type in {ContentType.TOURNAMENT, ContentType.CAMP}:
        return FontPreset.ATHLETIC
    if content.content_type == ContentType.COACHING:
        return FontPreset.MODERN
    if content.content_type == ContentType.LANE_RENTAL:
        return FontPreset.MODERN
    return FontPreset.EDITORIAL


INTENT_RULES: tuple[tuple[IntentKind, tuple[str, ...]], ...] = (
    (IntentKind.STRENGTH, ("strength", "strong", "power", "conditioning")),
    (
        IntentKind.COORDINATION,
        ("coordination", "agility", "balance", "reaction", "fielding"),
    ),
    (IntentKind.BATTING, ("batting", "batter", "power hitting", "finishing")),
    (IntentKind.BOWLING, ("bowling", "bowler", "spin", "pace")),
    (IntentKind.FITNESS, ("fitness", "athletic", "performance", "high-intensity")),
    (IntentKind.LEARNING, ("learn", "fundamental", "development", "skill", "tactical")),
    (IntentKind.FRIENDSHIP, ("make friends", "new friends", "friendship", "belong")),
    (IntentKind.CONFIDENCE, ("confidence", "confident", "comfortable", "included")),
    (
        IntentKind.FUN,
        ("fun", "engaging", "enjoy", "love", "play", "grow", "smile", "laugh", "excited"),
    ),
    (IntentKind.COACHING, ("coach", "training", "program", "academy")),
    (IntentKind.SCHEDULE, ("schedule", "date", "monday", "friday", "classes")),
    (IntentKind.REGISTRATION, ("register", "registration", "spots", "join")),
    (IntentKind.TROPHY, ("trophy", "winner", "champion", "prize", "award")),
    (IntentKind.FACILITY, ("facility", "lane", "rental", "nets")),
    (IntentKind.CONTACT, ("call", "phone", "text", "email", "contact")),
    (IntentKind.LOCATION, ("address", "location", "road", "street", "suite")),
)


def infer_visual_intents(content: PosterContent, *, limit: int = 8) -> list[VisualIntent]:
    candidates = [
        *content.detail_lines,
        *(
            value
            for section in content.sections
            for value in (section.heading, *section.items)
            if value
        ),
    ]
    intents: list[VisualIntent] = []
    seen: set[str] = set()
    for source_text in candidates:
        normalized = source_text.casefold()
        kind = next(
            (
                candidate_kind
                for candidate_kind, keywords in INTENT_RULES
                if any(keyword in normalized for keyword in keywords)
            ),
            IntentKind.GENERIC,
        )
        if source_text not in seen:
            intents.append(VisualIntent(source_text=source_text, kind=kind))
            seen.add(source_text)
        if len(intents) >= limit:
            break
    return intents


def ideogram_only_assessment(content: PosterContent) -> dict[str, Any]:
    lines = poster_copy_lines(content)
    characters = sum(len(line) for line in lines)
    reasons: list[str] = []
    if len(lines) > 14:
        reasons.append(f"{len(lines)} text elements exceeds the light-copy limit of 14")
    if characters > 520:
        reasons.append(f"{characters} characters exceeds the light-copy limit of 520")
    if isinstance(content, TournamentContent) and len(content.categories) > 1:
        reasons.append("multi-category tournaments require deterministic typography")
    if sum(len(section.items) for section in content.sections) > 8:
        reasons.append("long item lists require deterministic typography")
    return {
        "eligible": not reasons,
        "reasons": reasons,
        "line_count": len(lines),
        "character_count": characters,
        "density_score": content_density_score(content),
        "density": choose_density(content).value,
        "composition": choose_composition(content).value,
    }


def allowed_layouts(content: PosterContent) -> tuple[LayoutFamily, ...]:
    if isinstance(content, InformationContent):
        return (LayoutFamily.ANNOUNCEMENT_HERO,)
    if isinstance(content, TournamentContent):
        return (
            LayoutFamily.TOURNAMENT_REGISTRATION,
            LayoutFamily.TOURNAMENT_CATEGORY_GRID,
        )
    if isinstance(content, CampContent):
        return (LayoutFamily.SUMMER_CAMP,)
    if isinstance(content, CoachingContent):
        return (LayoutFamily.COACHING_SERVICES,)
    if isinstance(content, LaneRentalContent):
        return (LayoutFamily.LANE_RENTAL,)
    raise TypeError(f"Unsupported content model: {type(content).__name__}")


def choose_layout(content: PosterContent) -> LayoutFamily:
    if isinstance(content, TournamentContent):
        if len(content.categories) >= 2:
            return LayoutFamily.TOURNAMENT_CATEGORY_GRID
        return LayoutFamily.TOURNAMENT_REGISTRATION
    return allowed_layouts(content)[0]


def default_art_prompt(
    content: PosterContent,
    brand: BrandProfile,
    composition: CompositionMode | None = None,
    visual_treatment: VisualTreatment | None = None,
) -> str:
    composition = composition or choose_composition(content)
    visual_treatment = visual_treatment or choose_visual_treatment(content)
    color_phrase = "deep navy shadows, warm golden highlights, restrained electric cyan accents"
    copy_context = " ".join(poster_copy_lines(content)).lower()
    coaching_scene = (
        "warm foundation cricket coaching moment with an encouraging coach helping a young child "
        "around five years old hold a cricket bat correctly, premium indoor cricket nets, joyful "
        "and age-appropriate"
        if any(
            marker in copy_context
            for marker in ("foundation", "starting from 5", "children", "young players")
        )
        else (
            "elite cricket coaching session with coach and batter training in the right foreground, "
            "modern indoor academy, motion and focused athletic energy"
        )
    )
    scene_by_type = {
        ContentType.INFORMATION: (
            "modern indoor cricket academy with a full-length training lane and one athlete preparing"
        ),
        ContentType.TOURNAMENT: (
            "cricket stadium at night with a polished trophy and cricket ball, "
            "atmospheric floodlights"
        ),
        ContentType.CAMP: (
            "high-performance youth cricket training scene with a dynamic teenage batter, outdoor "
            "practice nets and stadium lights"
        ),
        ContentType.COACHING: coaching_scene,
        ContentType.LANE_RENTAL: (
            "premium indoor cricket practice lanes with a bowling machine, strong perspective "
            "lines and professional equipment"
        ),
    }
    composition_direction = {
        CompositionMode.ART_FORWARD: (
            "Use a full-frame photographic composition. Make the primary athlete large and "
            "visually dominant, occupying roughly the right half of the frame from mid-height "
            "toward the lower third. Fill the complete canvas with a believable sports environment. "
            "Keep only the upper-left region calm and dark."
        ),
        CompositionMode.BALANCED: (
            "Use a full-frame photograph with a medium-large subject on the right and a darker, "
            "less detailed left side."
        ),
        CompositionMode.INFORMATION_DENSE: (
            "Use a full-frame photograph with the subject confined to the upper-right and broad "
            "uncluttered dark areas elsewhere."
        ),
    }
    treatment_direction = (
        "Create a centered square editorial vignette with a close subject, a complete natural "
        "background, edge-to-edge visual detail, and no empty copy area. "
        if visual_treatment == VisualTreatment.VIGNETTE
        else composition_direction[composition]
    )
    canvas_phrase = (
        "Square professional editorial sports photograph"
        if visual_treatment == VisualTreatment.VIGNETTE
        else "Vertical full-frame professional editorial sports photograph"
    )
    return (
        f"{canvas_phrase} of "
        f"{scene_by_type[content.content_type]}. {treatment_direction} "
        f"Use {color_phrase}. This must be a continuous photograph only. Do not add panels, "
        f"grids, decorative borders, or UI motifs. {NO_TEXT_GUARDRAIL}"
    )


def choose_style_intent(content: PosterContent) -> StyleIntent:
    """Default mood per content type, used until the caller supplies one."""
    return {
        ContentType.INFORMATION: StyleIntent.PROFESSIONAL_CLEAN,
        ContentType.TOURNAMENT: StyleIntent.BOLD_ATTENTION,
        ContentType.CAMP: StyleIntent.YOUTHFUL_ENERGETIC,
        ContentType.COACHING: StyleIntent.PROFESSIONAL_CLEAN,
        ContentType.LANE_RENTAL: StyleIntent.MODERN_SLEEK,
    }[content.content_type]


def plan_design(
    content: PosterContent,
    brand: BrandProfile,
    suggestion: dict[str, Any] | None = None,
    *,
    style_intent: StyleIntent | None = None,
    color_mode: ColorMode = ColorMode.DARK,
    font_preset: FontPreset | None = None,
) -> DesignSpec:
    family = choose_layout(content)
    density = choose_density(content)
    composition = choose_composition(content)
    visual_treatment = choose_visual_treatment(content)
    intent = style_intent or choose_style_intent(content)
    theme = build_theme(intent, brand.palette, color_mode, font_preset)
    tokens = DesignTokens(
        panel_opacity=theme.panel_opacity,
        art_position_y=35 if visual_treatment == VisualTreatment.VIGNETTE else 50,
    )
    art_prompt = default_art_prompt(content, brand, composition, visual_treatment)
    art_focus = "right"

    if suggestion:
        suggested_family = suggestion.get("family")
        if suggested_family:
            candidate = LayoutFamily(suggested_family)
            if candidate in allowed_layouts(content):
                family = candidate
        if suggestion.get("art_prompt"):
            art_prompt = f"{str(suggestion['art_prompt']).rstrip(' .')}. {NO_TEXT_GUARDRAIL}"
        if suggestion.get("art_focus") in {"left", "center", "right"}:
            art_focus = suggestion["art_focus"]
        if suggestion.get("tokens"):
            tokens = DesignTokens.model_validate(suggestion["tokens"])

    return DesignSpec(
        family=family,
        density=density,
        composition=composition,
        color_mode=color_mode,
        # The intent's recipe picks the typeface unless the caller overrode it.
        font_preset=theme.font_preset,
        style_intent=intent,
        theme=theme,
        visual_treatment=visual_treatment,
        visual_intents=infer_visual_intents(content),
        palette=brand.palette,
        tokens=tokens,
        art_prompt=art_prompt,
        art_focus=art_focus,
    )


def layout_summary(content: PosterContent) -> dict[str, Any]:
    summary = {
        "content_type": content.content_type.value,
        "density_score": content_density_score(content),
        "allowed_layouts": [family.value for family in allowed_layouts(content)],
        "recommended_layout": choose_layout(content).value,
        "recommended_density": choose_density(content).value,
        "recommended_composition": choose_composition(content).value,
        "recommended_visual_treatment": choose_visual_treatment(content).value,
        "recommended_font": choose_font_preset(content).value,
        "detected_intents": [
            intent.model_dump(mode="json") for intent in infer_visual_intents(content)
        ],
    }
    summary["ideogram_only"] = ideogram_only_assessment(content)
    return summary
