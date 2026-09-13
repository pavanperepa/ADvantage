"""Palette plumbing, and the regenerate/palettes HTTP surface."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from advantage.adapters.poster_ideogram import _stamp, build_art_prompt
from advantage.adapters.reel import build_edit_spec
from advantage.domain.models import (
    PALETTE_SWATCHES,
    BrandPalette,
    CampaignRequest,
    CreativeFormat,
    PosterStyle,
    resolve_palette,
)
from advantage.integrations.google_drive import AssetKind, IntakeAsset, IntakeStatus


def _poster_request(**overrides) -> CampaignRequest:
    base = dict(
        business_name="Northstar Cricket Studio",
        brief_text="Youth cricket coaching for ages 5-13.",
        format=CreativeFormat.POSTER,
        contact_phone="+1 (713) 498-2155",
        destination_url="https://example.com/join",
        offer_text="Free trial session",
    )
    base.update(overrides)
    return CampaignRequest(**base)


def _clip(tmp_path: Path, name: str = "clip.mp4") -> IntakeAsset:
    path = tmp_path / name
    path.write_bytes(b"not a real video")
    return IntakeAsset(
        source_id=name,
        source_name=name,
        source_ref="ref",
        kind=AssetKind.VIDEO,
        mime_type="video/mp4",
        local_ref=str(path),
        status=IntakeStatus.IMPORTED,
        duration_seconds=8.0,
    )


@pytest.mark.parametrize("palette", list(BrandPalette))
def test_every_palette_reaches_the_reel_brand_block(palette: BrandPalette, tmp_path: Path) -> None:
    request = CampaignRequest(
        business_name="Northstar",
        brief_text="Youth cricket",
        format=CreativeFormat.REEL,
        palette=palette,
        footage_assets=[_clip(tmp_path), _clip(tmp_path, "clip2.mp4")],
    )

    brand = build_edit_spec(request)["brand"]
    swatch = PALETTE_SWATCHES[palette]

    assert (brand["primary"], brand["accent"], brand["ink"]) == (
        swatch.primary,
        swatch.accent,
        swatch.ink,
    )


def test_palettes_are_visually_distinct() -> None:
    """A picker of six identical-looking options would be pointless."""
    primaries = {swatch.primary for swatch in PALETTE_SWATCHES.values()}
    assert len(primaries) == len(BrandPalette)


def test_no_palette_keeps_the_original_academy_colours(tmp_path: Path) -> None:
    request = CampaignRequest(
        business_name="Northstar",
        brief_text="Youth cricket",
        format=CreativeFormat.REEL,
        footage_assets=[_clip(tmp_path), _clip(tmp_path, "clip2.mp4")],
    )

    brand = build_edit_spec(request)["brand"]

    assert brand["primary"] == "#2E7BFF"
    assert brand["accent"] == "#FFD100"


@pytest.mark.parametrize("palette", list(BrandPalette))
def test_art_prompt_names_the_palette_without_losing_its_constraints(
    palette: BrandPalette,
) -> None:
    prompt = build_art_prompt(_poster_request(palette=palette)).lower()
    swatch = PALETTE_SWATCHES[palette]

    assert swatch.label.lower() in prompt
    assert swatch.primary.lower() in prompt
    # The safety constraints must survive every added section.
    for constraint in ("no text", "no words", "no letters", "no logos", "no watermarks"):
        assert constraint in prompt


def test_refinement_notes_steer_the_artwork_but_not_the_copy() -> None:
    notes = "make it less empty and show more players"
    prompt = build_art_prompt(_poster_request(refinement_notes=notes))

    assert notes in prompt
    # Steering must never be able to turn into rendered text.
    assert "no text" in prompt.lower()
    assert "scene and framing only" in prompt.lower()


@pytest.mark.parametrize("style", list(PosterStyle))
def test_every_poster_style_keeps_the_text_free_constraints(style: PosterStyle) -> None:
    prompt = build_art_prompt(_poster_request(poster_style=style)).lower()

    assert "no text" in prompt
    assert "4:5" in prompt


@pytest.mark.parametrize("palette", list(BrandPalette))
def test_stamped_poster_uses_the_palette_ink_in_its_footer(
    palette: BrandPalette, tmp_path: Path
) -> None:
    artwork = tmp_path / "art.png"
    Image.new("RGB", (1080, 1350), "#777777").save(artwork)

    result = _stamp(_poster_request(palette=palette), artwork, tmp_path / f"{palette.value}.png")

    with Image.open(result.artifact.file_path) as poster:
        assert poster.size == (1080, 1350)
        footer_pixel = poster.convert("RGB").getpixel((30, 1300))

    expected = resolve_palette(palette).ink.lstrip("#")
    assert "%02X%02X%02X" % footer_pixel == expected.upper()


# --- HTTP surface ----------------------------------------------------------------
#
# These drive the real FastAPI app but never generate anything: `run_campaign`
# is patched, because a real poster render costs an Ideogram call and a minute
# of wall clock. What is under test here is routing, validation, and the
# "regenerate makes a NEW run" contract -- not the renderer.


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from cricket_posts.web import create_app

    return TestClient(create_app())


def test_palettes_endpoint_lists_every_enum_member(client) -> None:
    response = client.get("/api/campaigns/palettes")

    assert response.status_code == 200
    body = response.json()
    assert {row["value"] for row in body} == {palette.value for palette in BrandPalette}
    for row in body:
        assert row["primary"].startswith("#")
        assert row["label"]


def test_palettes_route_is_not_shadowed_by_the_run_id_route(client) -> None:
    """`/palettes` must be declared before `/{run_id}` or it 404s as a run id."""
    assert client.get("/api/campaigns/palettes").status_code == 200


def _seed_run(monkeypatch, request: CampaignRequest):
    """Put one fake completed run in the API's in-memory store."""
    from advantage.domain.models import CampaignArtifact, CampaignResult, VerificationResult
    from cricket_posts import campaign_api

    result = CampaignResult(
        request=request,
        artifact=CampaignArtifact(
            format=CreativeFormat.POSTER, file_path="poster.png", width=1080, height=1350
        ),
        verification=VerificationResult(passed=True),
    )
    campaign_api._RUNS["seed"] = result
    monkeypatch.setattr(campaign_api, "run_campaign", lambda req, *, workdir: result)
    return result


def test_regenerate_creates_a_new_run_and_keeps_the_original(client, monkeypatch) -> None:
    _seed_run(monkeypatch, _poster_request())

    response = client.post(
        "/api/campaigns/seed/regenerate",
        json={"refinement_notes": "make it less empty", "palette": "crimson_sport"},
    )

    assert response.status_code == 201
    assert response.json()["id"] != "seed"
    assert client.get("/api/campaigns/seed").status_code == 200


def test_regenerate_applies_only_the_supplied_overrides(client, monkeypatch) -> None:
    from cricket_posts import campaign_api

    _seed_run(monkeypatch, _poster_request(poster_style=PosterStyle.PHOTOREAL))
    seen: dict[str, CampaignRequest] = {}

    def capture(req, *, workdir):
        seen["request"] = req
        return campaign_api._RUNS["seed"]

    monkeypatch.setattr(campaign_api, "run_campaign", capture)

    client.post("/api/campaigns/seed/regenerate", json={"palette": "forest_green"})

    assert seen["request"].palette is BrandPalette.FOREST_GREEN
    # Untouched fields carry over rather than resetting.
    assert seen["request"].poster_style is PosterStyle.PHOTOREAL
    assert seen["request"].offer_text == "Free trial session"


def test_regenerate_rejects_a_bad_palette_and_names_the_valid_ones(client, monkeypatch) -> None:
    _seed_run(monkeypatch, _poster_request())

    response = client.post("/api/campaigns/seed/regenerate", json={"palette": "neon_pink"})

    assert response.status_code == 422
    assert "academy_blue" in response.json()["detail"]


def test_regenerate_404s_on_an_unknown_run(client) -> None:
    assert client.post("/api/campaigns/nope/regenerate", json={}).status_code == 404
