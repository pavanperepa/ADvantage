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

    #: An answer the agent drafted from the brief for the owner to confirm or
    #: edit. Shape follows ``kind``: a plain string for "text", one of
    #: ``choices`` for "choice", a list for "multi_text". ``None`` means the
    #: agent had nothing to go on -- never a fabricated placeholder.
    suggestion: str | list[str] | None = None
    suggestion_note: str | None = None


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
    """Split a benefits blob into separate phrases.

    Prefers newlines/semicolons as the separator when either is present, and
    only falls back to commas otherwise: an individual benefit frequently
    contains a comma of its own ("fundamentals, balance and confidence"), so
    splitting on commas as well would cut real phrases in half.
    """
    if isinstance(value, str):
        separator = r"[;\n]" if re.search(r"[;\n]", value) else r","
        parts = re.split(separator, value)
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


# --- agentic planning pass -------------------------------------------------------
#
# `next_questions` above is the contract: a fixed checklist, always available.
# What follows turns that checklist into something that reads like an agent
# doing the work rather than a form demanding it -- it reads `brief_text`,
# fills in what it can actually infer, and drafts an answer for each remaining
# question so the owner confirms instead of authors.
#
# Everything here degrades to the deterministic checklist. The LLM may only
# choose among field ids `next_questions` would already have asked, and every
# value it returns is validated against the same enums `apply_answers` uses,
# so a creative model cannot invent a field, a choice, or a question.

#: Questions per round. Deliberately small: two short rounds read as a
#: conversation, one round of four reads as a form.
QUESTIONS_PER_ROUND = 2


class AgentInference(BaseModel):
    """One fact the agent extracted from the brief and applied by itself."""

    model_config = ConfigDict(extra="forbid")

    field: str
    label: str
    value: str
    note: str


class InterviewPlan(BaseModel):
    """One round of the intake conversation."""

    model_config = ConfigDict(extra="forbid")

    agent_note: str
    understood: list[AgentInference] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    inferred_answers: dict[str, Any] = Field(default_factory=dict)
    round: int = 1
    total_rounds: int = 1


#: Human labels for the fields the agent may fill in or ask about.
FIELD_LABELS: dict[str, str] = {
    "reel_feel": "Reel feel",
    "poster_style": "Art style",
    "art_direction_notes": "Artwork scene",
    "offer_text": "Offer",
    "key_benefits": "Key benefits",
    "proof_point": "Proof point",
}

PLAN_INSTRUCTIONS = """\
You are an ad-campaign intake agent talking to a small-business owner who has
just written a rough brief. Your job is to do as much of the work for them as
possible, then ask only what you genuinely cannot infer.

You are given the brief and a list of fields that are still unfilled. Each
field has an id, a kind, and (for choice fields) the only permitted values.

Return three things:

1. "understood" -- fields you can confidently fill straight from the brief.
   Quote or closely paraphrase the owner's own words. Do NOT guess at facts
   the brief does not contain: never invent a price, date, phone number,
   statistic, guarantee, or testimonial. If the brief does not say it, leave
   the field out of "understood" entirely.
2. "questions" -- the most useful remaining fields to ask about, worded
   specifically for THIS business in plain language (not generic form
   labels). For each, draft a "suggestion": your best answer given the brief,
   which the owner will confirm or edit. A suggestion for a choice field must
   be exactly one of that field's permitted values. If you have nothing
   honest to suggest, use an empty string.
3. "agent_note" -- one short, friendly sentence summarising what you did and
   what you still need. No greeting, no sign-off.

Only ever use the field ids you were given. Never invent a field id or a
choice value.
"""


class _PlanInference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    value: str
    note: str = Field(default="", max_length=200)


class _PlanQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    prompt: str = Field(min_length=1, max_length=300)
    why: str = Field(default="", max_length=300)
    suggestion: str = Field(default="", max_length=400)
    suggestion_note: str = Field(default="", max_length=200)


class _AgentPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_note: str = Field(default="", max_length=300)
    understood: list[_PlanInference] = Field(default_factory=list)
    questions: list[_PlanQuestion] = Field(default_factory=list)


def _coerce_suggestion(question: Question, raw: str) -> str | list[str] | None:
    """Validate a drafted answer against the question it belongs to.

    Returns ``None`` (no suggestion shown) rather than raising whenever the
    model proposed something the owner could not have selected anyway.
    """
    text = (raw or "").strip()
    if not text:
        return None
    if question.kind == "choice":
        return text if question.choices and text in question.choices else None
    if question.kind == "multi_text":
        return _coerce_key_benefits(text) or None
    return text


def _deterministic_plan(
    request_draft: CampaignRequest, *, format: CreativeFormat, round_index: int
) -> InterviewPlan:
    """The always-available fallback: the plain checklist, no agent voice."""
    missing = [f for f in FIELD_PRIORITY.get(format, []) if _is_missing(request_draft, f)]
    questions = next_questions(request_draft, format=format, max_questions=QUESTIONS_PER_ROUND)
    remaining = max(0, len(missing) - len(questions))
    extra_rounds = -(-remaining // QUESTIONS_PER_ROUND)  # ceil
    return InterviewPlan(
        agent_note=(
            "A couple of quick questions and I can build this."
            if questions
            else "I have everything I need."
        ),
        questions=questions,
        round=round_index,
        total_rounds=round_index + extra_rounds,
    )


def plan_interview(
    request_draft: CampaignRequest,
    *,
    format: CreativeFormat,
    brief_text: str,
    round_index: int = 1,
    api_key: str | None = None,
    model: str | None = None,
    client: Any | None = None,
) -> InterviewPlan:
    """Plan one round of intake: what the agent worked out, and what it asks.

    Falls back to :func:`_deterministic_plan` -- the plain checklist -- on a
    missing key, any API failure, a malformed response, or a response that
    references a field the owner was never going to be asked about. The
    fallback is the contract; the agent pass only makes it feel like less
    work for the owner.
    """
    fallback = _deterministic_plan(request_draft, format=format, round_index=round_index)
    if not fallback.questions:
        return fallback

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key and client is None:
        return fallback

    missing = [f for f in FIELD_PRIORITY.get(format, []) if _is_missing(request_draft, f)]
    catalogue = [
        {
            "id": field,
            "kind": _BUILDERS[field](format).kind,
            "permitted_values": _BUILDERS[field](format).choices or [],
        }
        for field in missing
    ]

    try:
        openai_client = client
        if openai_client is None:
            from openai import OpenAI

            openai_client = OpenAI(api_key=key)

        response = openai_client.responses.parse(
            model=model or os.getenv("OPENAI_MODEL", "gpt-5.4"),
            instructions=PLAN_INSTRUCTIONS,
            input=(
                f"Brief from the owner:\n{brief_text.strip() or '(none supplied)'}\n\n"
                f"Business: {request_draft.business_name}\n"
                f"Creative format: {format.value}\n"
                f"Unfilled fields (ask about at most {QUESTIONS_PER_ROUND}):\n"
                f"{catalogue}"
            ),
            text_format=_AgentPlan,
            reasoning={"effort": "low"},
        )
        parsed = response.output_parsed
        if parsed is None or not isinstance(parsed, _AgentPlan):
            return fallback
        return _merge_plan(parsed, request_draft, format=format, round_index=round_index)
    except Exception:
        # Network, auth, schema drift, unexpected shape -- never raises.
        return fallback


def _merge_plan(
    parsed: _AgentPlan,
    request_draft: CampaignRequest,
    *,
    format: CreativeFormat,
    round_index: int,
) -> InterviewPlan:
    """Validate an agent plan against what the owner could actually be asked.

    Anything the model returned that is not a currently-missing field, or not
    a value `apply_answers` would accept, is dropped rather than trusted.
    """
    missing = [f for f in FIELD_PRIORITY.get(format, []) if _is_missing(request_draft, f)]
    allowed = set(missing)

    understood: list[AgentInference] = []
    inferred: dict[str, Any] = {}
    for item in parsed.understood:
        if item.field not in allowed or not item.value.strip():
            continue
        candidate: dict[str, Any] = {item.field: item.value.strip()}
        try:
            apply_answers(request_draft, candidate)  # validates enums/shape
        except AnswerValidationError:
            continue
        value: Any = item.value.strip()
        if item.field == "key_benefits":
            value = _coerce_key_benefits(value)
            if not value:
                continue
        inferred[item.field] = value
        understood.append(
            AgentInference(
                field=item.field,
                label=FIELD_LABELS.get(item.field, item.field),
                value=", ".join(value) if isinstance(value, list) else str(value),
                note=item.note.strip() or "picked up from your brief",
            )
        )
        allowed.discard(item.field)

    questions: list[Question] = []
    seen: set[str] = set()
    for proposed in parsed.questions:
        if proposed.id not in allowed or proposed.id in seen:
            continue
        if len(questions) >= QUESTIONS_PER_ROUND:
            break
        base = _BUILDERS[proposed.id](format)
        questions.append(
            base.model_copy(
                update={
                    "prompt": proposed.prompt.strip() or base.prompt,
                    "why": proposed.why.strip() or base.why,
                    "suggestion": _coerce_suggestion(base, proposed.suggestion),
                    "suggestion_note": proposed.suggestion_note.strip() or None,
                }
            )
        )
        seen.add(proposed.id)

    # The agent may have inferred everything, or returned nothing usable. Keep
    # the round non-empty by falling back to the checklist order for whatever
    # is still unanswered and unasked.
    if not questions:
        for field in missing:
            if field in inferred or len(questions) >= QUESTIONS_PER_ROUND:
                continue
            questions.append(_BUILDERS[field](format))
            seen.add(field)

    open_fields = [f for f in missing if f not in inferred and f not in seen]
    extra_rounds = -(-len(open_fields) // QUESTIONS_PER_ROUND)  # ceil

    return InterviewPlan(
        agent_note=parsed.agent_note.strip()
        or "Here is what I could work out from your brief.",
        understood=understood,
        questions=questions,
        inferred_answers=inferred,
        round=round_index,
        total_rounds=round_index + extra_rounds,
    )
