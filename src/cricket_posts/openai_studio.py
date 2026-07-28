from __future__ import annotations

import base64
import os
import re
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from .layout import allowed_layouts, layout_summary
from .models import (
    AuditIssue,
    AuditSeverity,
    CampContent,
    CoachingContent,
    Contact,
    ContentSection,
    ContentType,
    Density,
    DesignSpec,
    DesignTokens,
    EventCategory,
    InformationContent,
    LaneRentalContent,
    LayoutFamily,
    PosterContent,
    Schedule,
    TournamentContent,
    protect_all_copy,
)


class ExtractedPosterContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_type: ContentType
    organization: str = ""
    eyebrow: str = ""
    title: str
    subtitle: str = ""
    tagline: str = ""
    schedule: Schedule = Field(default_factory=Schedule)
    detail_lines: list[str] = Field(default_factory=list)
    location_lines: list[str] = Field(default_factory=list)
    contacts: list[Contact] = Field(default_factory=list)
    sections: list[ContentSection] = Field(default_factory=list)
    cta_lines: list[str] = Field(default_factory=list)
    short_name: str = ""
    organizer_tagline: str = ""
    categories: list[EventCategory] = Field(default_factory=list)
    program_info: str = ""
    coach_heading: str = ""
    coach_bio: str = ""
    price_line: str = ""


class ExtractedPoster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: ExtractedPosterContent


def extraction_to_content(extracted: ExtractedPosterContent) -> PosterContent:
    schedule = extracted.schedule if extracted.schedule.display() else None
    common: dict[str, Any] = {
        "organization": extracted.organization,
        "eyebrow": extracted.eyebrow,
        "title": extracted.title,
        "subtitle": extracted.subtitle,
        "tagline": extracted.tagline,
        "schedule": schedule,
        "price_line": extracted.price_line,
        "detail_lines": extracted.detail_lines,
        "location_lines": extracted.location_lines,
        "contacts": extracted.contacts,
        "sections": extracted.sections,
        "cta_lines": extracted.cta_lines,
        "protected_copy": [],
    }
    if extracted.content_type == ContentType.TOURNAMENT:
        return TournamentContent(
            **common,
            short_name=extracted.short_name,
            organizer_tagline=extracted.organizer_tagline,
            categories=extracted.categories,
        )
    if extracted.content_type == ContentType.CAMP:
        return CampContent(
            **common,
            program_info=extracted.program_info,
            coach_heading=extracted.coach_heading,
            coach_bio=extracted.coach_bio,
        )
    if extracted.content_type == ContentType.COACHING:
        return CoachingContent(**common)
    if extracted.content_type == ContentType.LANE_RENTAL:
        return LaneRentalContent(**common)
    return InformationContent(**common)


class LayoutSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family: LayoutFamily
    density: Density
    art_prompt: str = Field(min_length=40, max_length=1500)
    art_focus: Literal["left", "center", "right"]
    tokens: DesignTokens


class TokenPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title_scale: float | None = Field(default=None, ge=0.88, le=1.12)
    body_scale: float | None = Field(default=None, ge=1.0, le=1.12)
    panel_opacity: float | None = Field(default=None, ge=0.72, le=0.96)
    spacing_scale: float | None = Field(default=None, ge=0.82, le=1.08)
    art_position_x: int | None = Field(default=None, ge=0, le=100)
    art_position_y: int | None = Field(default=None, ge=0, le=100)


class CriticResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pass_required: bool
    issues: list[str] = Field(default_factory=list, max_length=8)
    token_patch: TokenPatch = Field(default_factory=TokenPatch)


EXTRACTION_PROMPT = """You extract cricket-poster content into the supplied schema.

Non-negotiable copy rules:
- Every factual display value must be copied from the user's source. Do not correct,
  normalize, rewrite, summarize, embellish, or invent names, punctuation, dates, times,
  ages, prices, phone numbers, addresses, awards, credentials, or claims.
- Preserve unusual spellings such as "Best Bats(man)" when supplied.
- Ignore Markdown table syntax and field-label decoration, but keep the actual values.
- Use display_text on contacts, schedules, and prizes when separators or punctuation
  must remain exactly as supplied.
- Never omit a supplied price or fee. Use price_line unless it belongs to a
  tournament category's registration_fee.
- Empty optional fields are better than invented copy.
- Choose the content_type that best matches the source.
- Put logically grouped lists into sections. Tournament divisions belong in categories.
- Leave protected_copy empty; the application fills it after verifying the extraction.
"""


PLANNER_PROMPT = """You are a constrained cricket-poster art director.
Choose only from the allowed layout families and density levels supplied by the application.
Do not create, alter, or repeat factual event copy. Produce a prompt for a continuous,
full-frame sports photograph only. Ask for one large, visually dominant cricket subject and
a believable environment. Never ask for graphic design, panels, borders, grids, UI motifs,
copy space, or a composed advertising page. The photograph must contain no text, letters,
numbers, pseudo-text, signs, logos, jersey writing, or watermarks.

The tokens object must contain exactly: title_scale, body_scale, panel_opacity,
spacing_scale, art_position_x, art_position_y. Keep values inside their schema bounds.
"""


CRITIC_PROMPT = """Review this rendered 1080x1350 cricket poster as a visual-design critic.
The deterministic audit already owns copy accuracy, overflow, and dimensions.
Suggest a refinement only when hierarchy, contrast, visual balance, or artwork crop is
materially weak. You may modify only the supplied token fields. Never rewrite copy, choose
a different layout, introduce a second page, or ask for regenerated text. Prefer no change
when the poster is already clear and balanced.
"""


def _normalized_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def verify_source_copy(content: PosterContent, source_text: str) -> list[str]:
    source = _normalized_whitespace(source_text)
    missing: list[str] = []
    for value in content.display_strings():
        normalized = _normalized_whitespace(value)
        if normalized and normalized not in source:
            missing.append(value)
    return missing


def verify_plain_source_coverage(
    content: PosterContent,
    source_text: str,
) -> list[str]:
    # Markdown tables mix field labels with values, so the extraction schema
    # validates those through verify_source_copy. For ordinary pasted copy,
    # every non-empty source line must survive somewhere in the display model.
    lines = [line.strip() for line in source_text.splitlines() if line.strip()]
    if any("|" in line for line in lines) or source_text.count("**") >= 4:
        return []
    visible = _normalized_whitespace(" ".join(content.display_strings()))
    missing: list[str] = []
    for line in lines:
        normalized = _normalized_whitespace(line)
        if normalized and normalized not in visible:
            missing.append(line)
    return list(dict.fromkeys(missing))


class OpenAIStudioProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is missing. Add it to .env.")
        self.client = OpenAI(api_key=key)
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5.4")

    def extract(self, source_text: str) -> PosterContent:
        response = self.client.responses.parse(
            model=self.model,
            instructions=EXTRACTION_PROMPT,
            input=source_text,
            text_format=ExtractedPoster,
            reasoning={"effort": "low"},
        )
        if response.output_parsed is None:
            raise RuntimeError(f"OpenAI returned no structured poster: {response.output_text}")
        content = extraction_to_content(response.output_parsed.content)
        missing = verify_source_copy(content, source_text)
        if missing:
            preview = "; ".join(repr(item) for item in missing[:6])
            raise ValueError(
                "Extraction changed or invented display copy. Review the source or structured "
                f"JSON. Non-verbatim values: {preview}"
            )
        omitted = verify_plain_source_coverage(content, source_text)
        if omitted:
            preview = "; ".join(repr(item) for item in omitted[:6])
            raise ValueError(
                "Extraction omitted supplied copy. Every pasted line must be assigned to a "
                f"display field without rewriting. Missing source lines: {preview}"
            )
        return protect_all_copy(content)

    def plan(self, content: PosterContent) -> dict[str, Any]:
        summary = layout_summary(content)
        response = self.client.responses.parse(
            model=self.model,
            instructions=PLANNER_PROMPT,
            input=(
                "Plan artwork and layout using this content-shape summary. Do not reproduce the "
                f"content itself:\n{summary}"
            ),
            text_format=LayoutSuggestion,
            reasoning={"effort": "low"},
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI returned no layout suggestion.")
        suggestion = response.output_parsed
        if suggestion.family not in allowed_layouts(content):
            raise ValueError(f"Planner selected disallowed layout: {suggestion.family.value}")
        return suggestion.model_dump(mode="json")

    def critique(self, image_path: Path, design: DesignSpec) -> CriticResult:
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        response = self.client.responses.parse(
            model=self.model,
            instructions=CRITIC_PROMPT,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                f"Current layout: {design.family.value}; density: "
                                f"{design.density.value}; tokens: "
                                f"{design.tokens.model_dump(mode='json')}"
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{encoded}",
                            "detail": "high",
                        },
                    ],
                }
            ],
            text_format=CriticResult,
            reasoning={"effort": "low"},
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI returned no critic result.")
        return response.output_parsed


def apply_critic_patch(design: DesignSpec, result: CriticResult) -> DesignSpec:
    if not result.pass_required:
        return design
    current = design.tokens.model_dump(mode="python")
    patch = result.token_patch.model_dump(exclude_none=True)
    current.update(patch)
    payload = design.model_dump(mode="python")
    payload["tokens"] = current
    return DesignSpec.model_validate(payload)


def critic_issues(result: CriticResult) -> list[AuditIssue]:
    return [
        AuditIssue(
            code="visual_critic",
            severity=AuditSeverity.WARNING,
            message=message,
        )
        for message in result.issues
    ]
