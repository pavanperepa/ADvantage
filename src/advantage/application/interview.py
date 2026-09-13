"""Agentic intake: ask the owner a small, targeted set of questions instead
of presenting one big blank form.

Three pieces:

* :func:`next_questions` -- a deterministic, capped, priority-ordered list of
  what is still missing for the chosen format. This is the contract; it must
  work with no LLM involved at all.
* :func:`apply_answers` -- coerce the owner's answers onto the right
  ``CampaignRequest`` fields, validating enum choices and rejecting unknown
  keys instead of silently dropping bad input.
* :func:`enrich_questions` -- an optional OpenAI pass that only rewords
  ``prompt``/``why`` in the owner's own domain language (pulled from
  ``brief_text``). It can never add, remove, reorder a question, change an
  ``id``, or invent a choice; if OpenAI is unavailable, errors, or returns
  anything that doesn't line up 1:1 with the deterministic set, the
  deterministic questions are returned unchanged. Reliability is scored
  here -- the deterministic path is the contract, the LLM is a garnish.
"""

from __future__ import annotations

import os
import re
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..domain.models import CampaignRequest, CreativeFormat, PosterStyle, ReelFeel


class Question(BaseModel):
    """One question to show the owner, tied to a single ``CampaignRequest`` field."""

    model_config = ConfigDict(extra="forbid")

    id: str
    prompt: str
    kind: Literal["text", "choice", "multi_text"]
    choices: list[str] | None = None
    why: str
    required: bool = True


class AnswerValidationError(ValueError):
    """Raised by :func:`apply_answers` when one or more answers are invalid.

    Carries every problem found (not just the first one hit) so a caller can
    surface them all at once instead of silently dropping the bad ones.
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


# --- deterministic question bank -------------------------------------------------

# Priority order per format: highest-impact field first. `reel_feel` /
# `poster_style` lead because they drive the whole creative plan; everything
# after is copy input that sharpens but doesn't restructure the output.
FIELD_PRIORITY: dict[CreativeFormat, list[str]] = {
    CreativeFormat.REEL: ["reel_feel", "offer_text", "key_benefits", "proof_point"],
    CreativeFormat.POSTER: ["poster_style", "art_direction_notes", "offer_text", "key_benefits"],
}

# Every field id either format's priority list can name, and the field name on
# CampaignRequest each answer is coerced onto. Also doubles as the allow-list
# `apply_answers` checks incoming answer keys against.
ANSWERABLE_FIELDS: frozenset[str] = frozenset(
    field for fields in FIELD_PRIORITY.values() for field in fields
)


def _reel_feel_question() -> Question:
    return Question(
        id="reel_feel",
        prompt="What feel should this reel have?",
        kind="choice",
        choices=[feel.value for feel in ReelFeel],
        why=(
            "This is the single input that drives the whole edit plan: pacing, shot "
            "motion, transitions, and which overlays appear."
        ),
        required=True,
    )


def _poster_style_question() -> Question:
    return Question(
        id="poster_style",
        prompt="What art style should the poster artwork use?",
        kind="choice",
        choices=[style.value for style in PosterStyle],
        why="This sets the art direction for the text-free artwork behind your exact business copy.",
        required=True,
    )


def _art_direction_notes_question(_format: CreativeFormat) -> Question:
    return Question(
        id="art_direction_notes",
        prompt="Describe the scene or subject you want in the poster artwork.",
        kind="text",
        why="Directs what the background artwork depicts; your business copy is always stamped on top separately.",
        required=False,
    )


def _offer_text_question(_format: CreativeFormat) -> Question:
    return Question(
        id="offer_text",
        prompt="What offer or promotion should we lead with, if any?",
        kind="text",
        why="Becomes the primary offer line in the ad copy and on the creative itself.",
        required=False,
    )


def _key_benefits_question(format: CreativeFormat) -> Question:
    why = (
        "Feeds the reel's checklist/ticker overlays with short benefit phrases."
        if format == CreativeFormat.REEL
        else "Feeds the poster's benefit bullet list."
    )
    return Question(
        id="key_benefits",
        prompt="List 2-4 short benefits your customers care about (comma-separated).",
        kind="multi_text",
        why=why,
        required=False,
    )


def _proof_point_question(_format: CreativeFormat) -> Question:
    return Question(
        id="proof_point",
        prompt=(
            "Any one verifiable fact, stat, or quote we can use as proof "
            "(e.g. years in business, a specific testimonial)?"
        ),
        kind="text",
        why=(
            "Adds one credible, specific claim instead of generic marketing language. "
            "Only what you supply here is used -- nothing is invented."
        ),
        required=False,
    )


_BUILDERS: dict[str, Callable[[CreativeFormat], Question]] = {
    "reel_feel": lambda _format: _reel_feel_question(),
    "poster_style": lambda _format: _poster_style_question(),
    "art_direction_notes": _art_direction_notes_question,
    "offer_text": _offer_text_question,
    "key_benefits": _key_benefits_question,
    "proof_point": _proof_point_question,
}


def _is_missing(request_draft: CampaignRequest, field_id: str) -> bool:
    value = getattr(request_draft, field_id, None)
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False


def next_questions(
    request_draft: CampaignRequest,
    *,
    format: CreativeFormat,
    max_questions: int = 4,
) -> list[Question]:
    """The next (deterministic, capped) batch of questions to ask the owner.

    Only asks about fields the priority list for ``format`` names, skips any
    field ``request_draft`` already has a real value for, and never returns
    more than ``max_questions`` entries.
    """
    if max_questions < 0:
        raise ValueError("max_questions must be >= 0")

    questions: list[Question] = []
    for field_id in FIELD_PRIORITY.get(format, []):
        if len(questions) >= max_questions:
            break
        if not _is_missing(request_draft, field_id):
            continue
        questions.append(_BUILDERS[field_id](format))
    return questions


def _coerce_key_benefits(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        parts = re.split(r"[,\n]", value)
    else:
        parts = [str(item) for item in value]
    return [part.strip() for part in parts if part.strip()]


def apply_answers(
    request_draft: CampaignRequest,
    answers: dict[str, str | list[str]],
) -> dict[str, Any]:
    """Coerce owner answers onto a ``CampaignRequest``-shaped dict.

    Enum fields (`reel_feel`, `poster_style`) are validated against their
    enum; `key_benefits` accepts either a comma/newline-separated string or a
    list and is normalized to a list of trimmed, non-empty strings; unknown
    keys are rejected. Raises :class:`AnswerValidationError` (carrying every
    problem found) rather than silently dropping bad values -- callers should
    catch it and re-prompt instead of proceeding with partial data.
    """
    merged = request_draft.model_dump(mode="python")
    errors: list[str] = []

    for key, value in answers.items():
        if key not in ANSWERABLE_FIELDS:
            errors.append(f"Unknown answer field: {key!r}")
            continue

        if key == "reel_feel":
            if not isinstance(value, str):
                errors.append("reel_feel must be a single choice string")
                continue
            try:
                merged[key] = ReelFeel(value)
            except ValueError:
                valid = ", ".join(feel.value for feel in ReelFeel)
                errors.append(f"reel_feel must be one of: {valid} (got {value!r})")

        elif key == "poster_style":
            if not isinstance(value, str):
                errors.append("poster_style must be a single choice string")
                continue
            try:
                merged[key] = PosterStyle(value)
            except ValueError:
                valid = ", ".join(style.value for style in PosterStyle)
                errors.append(f"poster_style must be one of: {valid} (got {value!r})")

        elif key == "key_benefits":
            if not isinstance(value, (str, list)):
                errors.append("key_benefits must be a string or list of strings")
                continue
            merged[key] = _coerce_key_benefits(value)

        else:  # offer_text, art_direction_notes, proof_point: plain text
            if not isinstance(value, str):
                errors.append(f"{key} must be a plain text string")
                continue
            merged[key] = value.strip()

    if errors:
        raise AnswerValidationError(errors)
    return merged


# --- optional LLM rewording --------------------------------------------------

ENRICH_INSTRUCTIONS = """You rephrase a fixed set of intake questions for a small business
owner, using the plain language of their own business description.

Rules, all mandatory:
- Return exactly one entry per input question, in the same order, with the same "id".
- Only reword "prompt" and "why". Never add, remove, reorder, merge, or split questions.
- Never invent facts, choices, numbers, dates, prices, or promises.
- Keep each "prompt" a single short question and each "why" a single short sentence.
- If you are not confident a rewording is an improvement, return the original text unchanged
  for that field.
"""


class _EnrichedQuestionText(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    prompt: str = Field(min_length=1, max_length=300)
    why: str = Field(min_length=1, max_length=300)


class _EnrichedQuestions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[_EnrichedQuestionText]


def _merge_enrichment(
    original: list[Question], enriched: list[_EnrichedQuestionText]
) -> list[Question]:
    """Apply LLM rewordings only if they line up 1:1 with the deterministic set.

    Any mismatch in count or id/order falls back to the original questions
    untouched -- this is what keeps a malformed or over-eager LLM response
    from adding, dropping, or reordering questions.
    """
    if len(enriched) != len(original):
        return original
    if [item.id for item in enriched] != [question.id for question in original]:
        return original

    merged: list[Question] = []
    for base, replacement in zip(original, enriched):
        prompt = replacement.prompt.strip() or base.prompt
        why = replacement.why.strip() or base.why
        merged.append(base.model_copy(update={"prompt": prompt, "why": why}))
    return merged


def enrich_questions(
    questions: list[Question],
    *,
    brief_text: str,
    api_key: str | None = None,
    model: str | None = None,
    client: Any | None = None,
) -> list[Question]:
    """Reword ``questions`` in the owner's own language via OpenAI, if possible.

    Degrades to returning ``questions`` unchanged whenever: there are no
    questions to reword; no OpenAI API key is configured; the call raises for
    any reason; the response is missing/malformed; or the response doesn't
    match the deterministic set 1:1 (see :func:`_merge_enrichment`). ``client``
    is accepted purely so tests can inject a fake OpenAI client without
    touching the real network.
    """
    if not questions:
        return questions

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key and client is None:
        return questions

    try:
        openai_client = client
        if openai_client is None:
            from openai import OpenAI

            openai_client = OpenAI(api_key=key)

        response = openai_client.responses.parse(
            model=model or os.getenv("OPENAI_MODEL", "gpt-5.4"),
            instructions=ENRICH_INSTRUCTIONS,
            input=_EnrichedQuestions(
                questions=[
                    _EnrichedQuestionText(id=q.id, prompt=q.prompt, why=q.why) for q in questions
                ]
            ).model_dump_json(),
            text_format=_EnrichedQuestions,
            reasoning={"effort": "low"},
        )
        parsed = response.output_parsed
        if parsed is None or not isinstance(parsed, _EnrichedQuestions):
            return questions
        return _merge_enrichment(questions, parsed.questions)
    except Exception:
        # Any failure (network, auth, malformed schema, unexpected shape) falls
        # back to the deterministic questions. This path must never raise.
        return questions
