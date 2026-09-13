"""Tests for the agentic intake: deterministic question selection, answer
coercion, and the optional (must-degrade-gracefully) OpenAI rewording pass.

No real network or OpenAI call happens anywhere in this file -- the OpenAI
client is always a small fake injected via `enrich_questions(..., client=...)`.
"""

from __future__ import annotations

import pytest

from advantage import CampaignRequest, CreativeFormat, PosterStyle, ReelFeel
import advantage.application.interview as interview
from advantage.application.interview import (
    AnswerValidationError,
    apply_answers,
    enrich_questions,
    next_questions,
)


def _request(**overrides: object) -> CampaignRequest:
    defaults: dict[str, object] = dict(
        business_name="22Yards Houston",
        brief_text="Fall registration is open at 22Yards Houston.",
        format=CreativeFormat.REEL,
    )
    defaults.update(overrides)
    return CampaignRequest(**defaults)


class _FakeResponse:
    def __init__(self, output_parsed: object) -> None:
        self.output_parsed = output_parsed


class _FakeResponses:
    def __init__(self, output_parsed: object = None, raise_exc: BaseException | None = None) -> None:
        self._output_parsed = output_parsed
        self._raise_exc = raise_exc
        self.calls = 0

    def parse(self, **kwargs: object) -> _FakeResponse:
        self.calls += 1
        if self._raise_exc is not None:
            raise self._raise_exc
        return _FakeResponse(self._output_parsed)


class _FakeClient:
    def __init__(self, output_parsed: object = None, raise_exc: BaseException | None = None) -> None:
        self.responses = _FakeResponses(output_parsed, raise_exc)


# --- next_questions -----------------------------------------------------------


def test_reel_question_set_in_priority_order():
    request = _request(format=CreativeFormat.REEL)
    questions = next_questions(request, format=CreativeFormat.REEL, max_questions=10)
    assert [q.id for q in questions] == [
        "reel_feel",
        "offer_text",
        "key_benefits",
        "proof_point",
    ]


def test_poster_question_set_in_priority_order():
    request = _request(format=CreativeFormat.POSTER, business_name="22Yards")
    questions = next_questions(request, format=CreativeFormat.POSTER, max_questions=10)
    assert [q.id for q in questions] == [
        "poster_style",
        "art_direction_notes",
        "offer_text",
        "key_benefits",
    ]


def test_cap_is_respected():
    request = _request(format=CreativeFormat.REEL)
    questions = next_questions(request, format=CreativeFormat.REEL, max_questions=2)
    assert len(questions) == 2
    assert [q.id for q in questions] == ["reel_feel", "offer_text"]


def test_default_cap_matches_full_reel_field_list():
    request = _request(format=CreativeFormat.REEL)
    questions = next_questions(request, format=CreativeFormat.REEL)
    assert len(questions) == 4  # default max_questions=4, exactly matches the reel list


def test_zero_cap_returns_no_questions():
    request = _request(format=CreativeFormat.REEL)
    assert next_questions(request, format=CreativeFormat.REEL, max_questions=0) == []


def test_negative_cap_is_rejected():
    request = _request(format=CreativeFormat.REEL)
    with pytest.raises(ValueError):
        next_questions(request, format=CreativeFormat.REEL, max_questions=-1)


def test_already_answered_fields_are_never_reasked():
    request = _request(
        format=CreativeFormat.REEL,
        reel_feel=ReelFeel.HIGH_ENERGY,
        offer_text="Free trial week",
    )
    questions = next_questions(request, format=CreativeFormat.REEL, max_questions=10)
    ids = [q.id for q in questions]
    assert "reel_feel" not in ids
    assert "offer_text" not in ids
    assert ids == ["key_benefits", "proof_point"]


def test_blank_string_still_counts_as_missing():
    request = _request(format=CreativeFormat.REEL, offer_text="   ")
    questions = next_questions(request, format=CreativeFormat.REEL, max_questions=10)
    assert "offer_text" in [q.id for q in questions]


def test_empty_list_still_counts_as_missing():
    request = _request(format=CreativeFormat.REEL, key_benefits=[])
    questions = next_questions(request, format=CreativeFormat.REEL, max_questions=10)
    assert "key_benefits" in [q.id for q in questions]


def test_populated_key_benefits_counts_as_answered():
    request = _request(format=CreativeFormat.REEL, key_benefits=["Fitness", "Fun"])
    questions = next_questions(request, format=CreativeFormat.REEL, max_questions=10)
    assert "key_benefits" not in [q.id for q in questions]


def test_no_questions_when_everything_present():
    request = _request(
        format=CreativeFormat.REEL,
        reel_feel=ReelFeel.HIGH_ENERGY,
        offer_text="Free trial week",
        key_benefits=["Fitness"],
        proof_point="10 years coaching in Houston",
    )
    assert next_questions(request, format=CreativeFormat.REEL) == []


def test_reel_feel_choices_match_enum_exactly():
    request = _request(format=CreativeFormat.REEL)
    [question] = next_questions(request, format=CreativeFormat.REEL, max_questions=1)
    assert question.id == "reel_feel"
    assert question.kind == "choice"
    assert question.required is True
    assert question.choices == [feel.value for feel in ReelFeel]


def test_poster_style_choices_match_enum_exactly():
    request = _request(format=CreativeFormat.POSTER)
    [question] = next_questions(request, format=CreativeFormat.POSTER, max_questions=1)
    assert question.id == "poster_style"
    assert question.kind == "choice"
    assert question.required is True
    assert question.choices == [style.value for style in PosterStyle]


def test_text_questions_have_no_choices_and_are_not_required():
    request = _request(format=CreativeFormat.REEL, reel_feel=ReelFeel.CINEMATIC)
    questions = next_questions(request, format=CreativeFormat.REEL, max_questions=10)
    assert all(q.choices is None for q in questions)
    assert all(q.required is False for q in questions)


def test_every_question_has_a_nonempty_why():
    request = _request(format=CreativeFormat.POSTER)
    questions = next_questions(request, format=CreativeFormat.POSTER, max_questions=10)
    assert all(q.why.strip() for q in questions)


# --- apply_answers -------------------------------------------------------------


def test_valid_answers_are_coerced_onto_the_right_fields():
    request = _request(format=CreativeFormat.REEL)
    result = apply_answers(
        request,
        {
            "reel_feel": "high_energy",
            "offer_text": "  Free trial week  ",
            "key_benefits": "Fitness, Fun, Discipline",
            "proof_point": "10 years coaching in Houston",
        },
    )
    assert result["reel_feel"] == ReelFeel.HIGH_ENERGY
    assert result["offer_text"] == "Free trial week"
    assert result["key_benefits"] == ["Fitness", "Fun", "Discipline"]
    assert result["proof_point"] == "10 years coaching in Houston"


def test_poster_style_answer_is_coerced():
    request = _request(format=CreativeFormat.POSTER)
    result = apply_answers(request, {"poster_style": "bold_graphic"})
    assert result["poster_style"] == PosterStyle.BOLD_GRAPHIC


def test_key_benefits_accepts_a_list_and_trims_blanks():
    request = _request(format=CreativeFormat.REEL)
    result = apply_answers(request, {"key_benefits": ["Fitness", " Fun ", "", "  "]})
    assert result["key_benefits"] == ["Fitness", "Fun"]


def test_key_benefits_splits_on_newlines_too():
    request = _request(format=CreativeFormat.REEL)
    result = apply_answers(request, {"key_benefits": "Fitness\nFun\n"})
    assert result["key_benefits"] == ["Fitness", "Fun"]


def test_rejects_bad_reel_feel_value():
    request = _request(format=CreativeFormat.REEL)
    with pytest.raises(AnswerValidationError) as excinfo:
        apply_answers(request, {"reel_feel": "not_a_real_feel"})
    assert any("reel_feel" in error for error in excinfo.value.errors)


def test_rejects_bad_poster_style_value():
    request = _request(format=CreativeFormat.POSTER)
    with pytest.raises(AnswerValidationError) as excinfo:
        apply_answers(request, {"poster_style": "ugly"})
    assert any("poster_style" in error for error in excinfo.value.errors)


def test_rejects_unknown_field_instead_of_dropping_it():
    request = _request(format=CreativeFormat.REEL)
    with pytest.raises(AnswerValidationError) as excinfo:
        apply_answers(request, {"business_name": "A New Name"})
    assert any("Unknown answer field" in error for error in excinfo.value.errors)


def test_collects_every_error_not_just_the_first():
    request = _request(format=CreativeFormat.REEL)
    with pytest.raises(AnswerValidationError) as excinfo:
        apply_answers(request, {"reel_feel": "nope", "bogus_field": "x"})
    assert len(excinfo.value.errors) == 2


def test_apply_answers_does_not_mutate_the_original_request():
    request = _request(format=CreativeFormat.REEL)
    apply_answers(request, {"offer_text": "New offer"})
    assert request.offer_text is None


# --- enrich_questions (must degrade gracefully) --------------------------------


def test_enrich_questions_falls_back_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    request = _request(format=CreativeFormat.REEL)
    questions = next_questions(request, format=CreativeFormat.REEL)
    result = enrich_questions(questions, brief_text="A cricket academy for kids")
    assert result == questions


def test_enrich_questions_returns_empty_for_empty_input():
    assert enrich_questions([], brief_text="anything") == []


def test_enrich_questions_rewords_prompt_and_why_only():
    request = _request(format=CreativeFormat.REEL)
    questions = next_questions(request, format=CreativeFormat.REEL, max_questions=2)
    enriched = interview._EnrichedQuestions(
        questions=[
            interview._EnrichedQuestionText(
                id=q.id, prompt=f"Reworded: {q.prompt}", why=f"Reworded: {q.why}"
            )
            for q in questions
        ]
    )
    fake_client = _FakeClient(output_parsed=enriched)
    result = enrich_questions(questions, brief_text="brief", client=fake_client)

    assert [q.id for q in result] == [q.id for q in questions]
    assert all(updated.prompt.startswith("Reworded:") for updated in result)
    assert all(updated.why.startswith("Reworded:") for updated in result)
    for original, updated in zip(questions, result):
        assert updated.kind == original.kind
        assert updated.choices == original.choices
        assert updated.required == original.required
        assert updated.id == original.id


def test_enrich_questions_falls_back_when_llm_adds_a_question():
    request = _request(format=CreativeFormat.REEL)
    questions = next_questions(request, format=CreativeFormat.REEL, max_questions=2)
    enriched = interview._EnrichedQuestions(
        questions=[
            interview._EnrichedQuestionText(id=q.id, prompt=q.prompt, why=q.why) for q in questions
        ]
        + [interview._EnrichedQuestionText(id="budget_usd", prompt="What's your budget?", why="Money")]
    )
    fake_client = _FakeClient(output_parsed=enriched)
    result = enrich_questions(questions, brief_text="brief", client=fake_client)
    assert result == questions


def test_enrich_questions_falls_back_when_llm_drops_a_question():
    request = _request(format=CreativeFormat.REEL)
    questions = next_questions(request, format=CreativeFormat.REEL, max_questions=3)
    enriched = interview._EnrichedQuestions(
        questions=[
            interview._EnrichedQuestionText(
                id=questions[0].id, prompt=questions[0].prompt, why=questions[0].why
            )
        ]
    )
    fake_client = _FakeClient(output_parsed=enriched)
    result = enrich_questions(questions, brief_text="brief", client=fake_client)
    assert result == questions


def test_enrich_questions_falls_back_when_llm_reorders_ids():
    request = _request(format=CreativeFormat.REEL)
    questions = next_questions(request, format=CreativeFormat.REEL, max_questions=3)
    enriched = interview._EnrichedQuestions(
        questions=[
            interview._EnrichedQuestionText(id=q.id, prompt=q.prompt, why=q.why)
            for q in reversed(questions)
        ]
    )
    fake_client = _FakeClient(output_parsed=enriched)
    result = enrich_questions(questions, brief_text="brief", client=fake_client)
    assert result == questions


def test_enrich_questions_falls_back_when_llm_invents_a_different_id():
    request = _request(format=CreativeFormat.REEL)
    questions = next_questions(request, format=CreativeFormat.REEL, max_questions=1)
    enriched = interview._EnrichedQuestions(
        questions=[interview._EnrichedQuestionText(id="made_up_field", prompt="Huh?", why="Because")]
    )
    fake_client = _FakeClient(output_parsed=enriched)
    result = enrich_questions(questions, brief_text="brief", client=fake_client)
    assert result == questions


def test_enrich_questions_falls_back_on_none_output():
    request = _request(format=CreativeFormat.REEL)
    questions = next_questions(request, format=CreativeFormat.REEL, max_questions=2)
    fake_client = _FakeClient(output_parsed=None)
    result = enrich_questions(questions, brief_text="brief", client=fake_client)
    assert result == questions


def test_enrich_questions_falls_back_on_exception():
    request = _request(format=CreativeFormat.REEL)
    questions = next_questions(request, format=CreativeFormat.REEL, max_questions=2)
    fake_client = _FakeClient(raise_exc=RuntimeError("network down"))
    result = enrich_questions(questions, brief_text="brief", client=fake_client)
    assert result == questions


def test_enrich_questions_falls_back_on_unexpected_output_type():
    request = _request(format=CreativeFormat.REEL)
    questions = next_questions(request, format=CreativeFormat.REEL, max_questions=2)
    fake_client = _FakeClient(output_parsed={"not": "the expected pydantic model"})
    result = enrich_questions(questions, brief_text="brief", client=fake_client)
    assert result == questions
