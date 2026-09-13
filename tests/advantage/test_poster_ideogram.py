"""Tests for the Ideogram poster path and its fallback into `poster.py`.

Per the paid-API rule: `cricket_posts.ideogram.generate_from_prompt` is always
mocked here -- these tests never make a real Ideogram call. The two "falls
back to compose()" tests still exercise the real, free, local `compose()`
pipeline (same as `test_poster_adapter.py`), so they share its
`_skip_if_no_plates` guard.
"""

from __future__ import annotations

import pytest
from PIL import Image

from advantage import CampaignRequest, CreativeFormat, PosterStyle
from advantage.adapters import poster_ideogram
from advantage.adapters.poster import describe_plan, produce_poster
from advantage.adapters.poster_ideogram import (
    PosterAdapterError,
    StampedPoster,
    build_art_prompt,
    produce_ideogram_poster,
)
from advantage.application.verification import verify_poster
from advantage.domain.models import CampaignArtifact
from cricket_posts.plates import PlateBank


def _request(**overrides: object) -> CampaignRequest:
    defaults: dict[str, object] = dict(
        business_name="22Yards Houston",
        brief_text="Fall registration is open for junior cricket sessions.",
        format=CreativeFormat.POSTER,
        contact_phone="+1 (713) 498-2155",
        destination_url="https://axon22yards.com/join?location=houston",
        offer_text="New players get a free trial session.",
        audience="Parents of kids 5-13",
    )
    defaults.update(overrides)
    return CampaignRequest(**defaults)


@pytest.fixture(scope="module", autouse=True)
def _skip_if_no_plates() -> None:
    if not PlateBank.load().entries:
        pytest.skip("plate bank is empty; run `cricket-posts bank plates`")


# --- build_art_prompt --------------------------------------------------------

NEGATIVE_CONSTRAINTS = ("no text", "no words", "no letters", "no logos", "no watermarks")


@pytest.mark.parametrize("style", [*list(PosterStyle), None])
def test_build_art_prompt_includes_text_free_constraints_for_every_style(style):
    request = _request(poster_style=style)

    prompt = build_art_prompt(request)
    low = prompt.lower()

    for phrase in NEGATIVE_CONSTRAINTS:
        assert phrase in low, f"{phrase!r} missing for style={style!r}"
    assert "4:5" in prompt
    assert "lower third" in low


def test_build_art_prompt_defaults_to_photoreal_when_style_is_none():
    with_style = build_art_prompt(_request(poster_style=PosterStyle.PHOTOREAL))
    without_style = build_art_prompt(_request(poster_style=None))

    # Same preset text drives both -- the PHOTOREAL scene description appears
    # in each, proving the None case really did default to PHOTOREAL.
    photoreal_marker = "documentary-style sports photography"
    assert photoreal_marker in with_style
    assert photoreal_marker in without_style


def test_build_art_prompt_never_asks_ideogram_to_render_business_copy_as_text():
    # The business name/offer/audience appear as *context* sentences, never
    # inside a quoted "render this text" instruction.
    request = _request()
    prompt = build_art_prompt(request)
    assert "render" not in prompt.lower()


# --- stamping / produce_ideogram_poster --------------------------------------


def _fake_artwork(path, size=(1792, 2240)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (90, 120, 150)).save(path)
    return path


def test_produce_ideogram_poster_stamps_a_real_1080x1350_png(tmp_path, monkeypatch):
    def fake_generate_from_prompt(prompt, destination, **kwargs):
        return _fake_artwork(destination)

    monkeypatch.setattr(poster_ideogram, "generate_from_prompt", fake_generate_from_prompt)

    request = _request()
    stamped = produce_ideogram_poster(request, workdir=tmp_path)

    assert isinstance(stamped, StampedPoster)
    assert stamped.artifact.format == CreativeFormat.POSTER
    assert stamped.artifact.width == 1080
    assert stamped.artifact.height == 1350
    poster_path = tmp_path / "poster.png"
    assert stamped.artifact.file_path == str(poster_path)
    assert poster_path.exists() and poster_path.stat().st_size > 0

    with Image.open(poster_path) as image:
        assert image.size == (1080, 1350)
        assert image.format == "PNG"

    # Every field we intended to stamp is present, non-empty, verbatim.
    assert stamped.stamped_copy
    assert request.business_name in stamped.stamped_copy
    assert request.offer_text in stamped.stamped_copy
    assert request.contact_phone in stamped.stamped_copy
    assert request.destination_url in stamped.stamped_copy
    assert stamped.overflow == []

    # The sidecar manifest verification.py reads exists and matches.
    manifest = poster_ideogram.read_stamp_manifest(poster_path)
    assert manifest is not None
    assert manifest["stamped_copy"] == stamped.stamped_copy
    assert manifest["overflow"] == []


def test_produce_ideogram_poster_wrong_format_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(
        poster_ideogram, "generate_from_prompt", lambda *a, **k: pytest.fail("must not call Ideogram")
    )
    request = _request(format=CreativeFormat.REEL, footage_assets=[])

    with pytest.raises(PosterAdapterError, match="POSTER"):
        produce_ideogram_poster(request, workdir=tmp_path)


def test_produce_ideogram_poster_raises_when_generation_fails(tmp_path, monkeypatch):
    def failing_generate(prompt, destination, **kwargs):
        raise RuntimeError("Ideogram returned no image URL")

    monkeypatch.setattr(poster_ideogram, "generate_from_prompt", failing_generate)

    with pytest.raises(PosterAdapterError, match="Ideogram artwork generation failed"):
        produce_ideogram_poster(_request(), workdir=tmp_path)


def test_produce_ideogram_poster_flags_overflow_for_an_unbreakable_field(tmp_path, monkeypatch):
    def fake_generate_from_prompt(prompt, destination, **kwargs):
        return _fake_artwork(destination)

    monkeypatch.setattr(poster_ideogram, "generate_from_prompt", fake_generate_from_prompt)

    # A single space-free run of characters can't be word-wrapped, so it must
    # be caught by the drawn-box safe-margin check instead.
    request = _request(brief_text="x" * 260)

    stamped = produce_ideogram_poster(request, workdir=tmp_path)

    assert stamped.overflow, "an unbreakable overlong field should be recorded as overflow, not silently clipped off-canvas"


# --- describe_plan ------------------------------------------------------------


def test_poster_ideogram_describe_plan_returns_non_empty_decisions():
    for style in [*list(PosterStyle), None]:
        plan = poster_ideogram.describe_plan(_request(poster_style=style))
        assert plan.format == CreativeFormat.POSTER
        assert plan.decisions
        assert all(decision.choice and decision.reason for decision in plan.decisions)


def test_module_describe_plan_delegates_to_ideogram_when_key_present(monkeypatch):
    monkeypatch.setenv("IDEOGRAM_API_KEY", "fake-key-for-test")
    plan = describe_plan(_request())
    assert plan.feel in {style.value for style in PosterStyle}


def test_module_describe_plan_delegates_to_compose_when_key_missing(monkeypatch):
    monkeypatch.delenv("IDEOGRAM_API_KEY", raising=False)
    plan = describe_plan(_request())
    assert plan.feel == "offline_compose"
    assert plan.decisions


# --- produce_poster routing/fallback -----------------------------------------


def test_produce_poster_uses_ideogram_when_key_present_and_call_succeeds(tmp_path, monkeypatch):
    monkeypatch.setenv("IDEOGRAM_API_KEY", "fake-key-for-test")

    fabricated_artifact = CampaignArtifact(
        format=CreativeFormat.POSTER,
        file_path=str(tmp_path / "poster.png"),
        width=1080,
        height=1350,
    )
    fabricated = StampedPoster(
        artifact=fabricated_artifact,
        stamped_copy=["22Yards Houston", "New players get a free trial session."],
        overflow=[],
    )

    def fake_produce_ideogram_poster(request, *, workdir):
        return fabricated

    monkeypatch.setattr(poster_ideogram, "produce_ideogram_poster", fake_produce_ideogram_poster)

    artifact, compose_result = produce_poster(_request(), workdir=tmp_path)

    assert artifact is fabricated_artifact
    assert compose_result is None
    # A successful Ideogram call is not a fallback -- no marker written.
    assert poster_ideogram.read_fallback_reason(artifact.file_path) is None


def test_produce_poster_falls_back_to_compose_when_key_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("IDEOGRAM_API_KEY", raising=False)

    artifact, compose_result = produce_poster(_request(), workdir=tmp_path)

    assert compose_result is not None  # the real ComposeResult from compose()
    assert artifact.width == 1080 and artifact.height == 1350

    reason = poster_ideogram.read_fallback_reason(artifact.file_path)
    assert reason is not None
    assert "IDEOGRAM_API_KEY" in reason


def test_produce_poster_falls_back_to_compose_when_ideogram_call_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("IDEOGRAM_API_KEY", "fake-key-for-test")

    def failing_produce_ideogram_poster(request, *, workdir):
        raise PosterAdapterError("Ideogram artwork generation failed: boom")

    monkeypatch.setattr(poster_ideogram, "produce_ideogram_poster", failing_produce_ideogram_poster)

    artifact, compose_result = produce_poster(_request(), workdir=tmp_path)

    assert compose_result is not None
    assert artifact.width == 1080 and artifact.height == 1350

    reason = poster_ideogram.read_fallback_reason(artifact.file_path)
    assert reason is not None
    assert "boom" in reason


def test_produce_poster_allow_ideogram_false_skips_ideogram_and_leaves_no_marker(tmp_path, monkeypatch):
    monkeypatch.setenv("IDEOGRAM_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(
        poster_ideogram,
        "produce_ideogram_poster",
        lambda *a, **k: pytest.fail("must not call Ideogram when allow_ideogram=False"),
    )

    artifact, compose_result = produce_poster(_request(), workdir=tmp_path, allow_ideogram=False)

    assert compose_result is not None
    # A deliberate opt-out is not a fallback, so no marker is written.
    assert poster_ideogram.read_fallback_reason(artifact.file_path) is None


# --- verify_poster on the Ideogram path --------------------------------------


def test_verify_poster_passes_for_a_clean_stamped_poster(tmp_path, monkeypatch):
    monkeypatch.setattr(
        poster_ideogram, "generate_from_prompt", lambda prompt, destination, **k: _fake_artwork(destination)
    )
    stamped = produce_ideogram_poster(_request(), workdir=tmp_path)

    result = verify_poster(stamped.artifact, None)

    assert result.passed is True, result.findings
    assert result.findings == []


def test_verify_poster_ideogram_path_flags_wrong_dimensions(tmp_path, monkeypatch):
    monkeypatch.setattr(
        poster_ideogram, "generate_from_prompt", lambda prompt, destination, **k: _fake_artwork(destination)
    )
    stamped = produce_ideogram_poster(_request(), workdir=tmp_path)
    wrong = stamped.artifact.model_copy(update={"width": 1080, "height": 1080})

    result = verify_poster(wrong, None)

    assert result.passed is False
    assert any("1080x1080" in finding for finding in result.findings)


def test_verify_poster_ideogram_path_flags_missing_manifest(tmp_path):
    # A real 1080x1350 PNG with no .stamp.json sidecar alongside it -- as if
    # the manifest write were ever skipped.
    poster_path = tmp_path / "poster.png"
    Image.new("RGB", (1080, 1350), (200, 200, 200)).save(poster_path)
    artifact = CampaignArtifact(
        format=CreativeFormat.POSTER, file_path=str(poster_path), width=1080, height=1350
    )

    result = verify_poster(artifact, None)

    assert result.passed is False
    assert any("manifest" in finding.lower() for finding in result.findings)


def test_verify_poster_ideogram_path_flags_overflow_via_explicit_kwargs(tmp_path):
    poster_path = tmp_path / "poster.png"
    Image.new("RGB", (1080, 1350), (200, 200, 200)).save(poster_path)
    artifact = CampaignArtifact(
        format=CreativeFormat.POSTER, file_path=str(poster_path), width=1080, height=1350
    )

    result = verify_poster(
        artifact,
        None,
        stamped_copy=["22Yards Houston"],
        stamp_overflow=["a very long brief that had to be truncated"],
    )

    assert result.passed is False
    assert any("truncated" in finding.lower() for finding in result.findings)


def test_verify_poster_ideogram_path_flags_empty_stamped_copy(tmp_path):
    poster_path = tmp_path / "poster.png"
    Image.new("RGB", (1080, 1350), (200, 200, 200)).save(poster_path)
    artifact = CampaignArtifact(
        format=CreativeFormat.POSTER, file_path=str(poster_path), width=1080, height=1350
    )

    result = verify_poster(artifact, None, stamped_copy=[], stamp_overflow=[])

    assert result.passed is False
    assert any("empty" in finding.lower() for finding in result.findings)


def test_verify_poster_surfaces_fallback_as_non_blocking(tmp_path, monkeypatch):
    monkeypatch.delenv("IDEOGRAM_API_KEY", raising=False)

    artifact, compose_result = produce_poster(_request(), workdir=tmp_path)

    result = verify_poster(artifact, compose_result)

    assert result.passed is True, result.findings
    assert any("fell back" in finding.lower() or "not set" in finding.lower() for finding in result.findings)
