"""Tests for the new CampaignRequest -> poster mapping/glue layer only.

Unlike test_reel_adapter.py/test_meta_adapter.py (which mock the expensive/
external parts -- subprocess, Node, the Meta Graph API), this pipeline is
free, local, and already covered end-to-end by tests/test_pipeline.py against
a real Playwright-driven browser. So these tests run `produce_poster()` for
real, same as test_pipeline.py's own `composer` fixture, and stay narrowly
about the mapping this module adds -- not re-testing `compose()`/
`PosterComposer` behavior the existing suite already covers.
"""

from __future__ import annotations

import pytest

from cricket_posts.campaign import CampaignRequest, CreativeFormat
from cricket_posts.campaign.poster_adapter import PosterAdapterError, produce_poster
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


def test_produce_poster_renders_a_clean_poster(tmp_path):
    request = _request()

    artifact, compose_result = produce_poster(request, workdir=tmp_path)

    assert artifact.format == CreativeFormat.POSTER
    assert artifact.width == 1080
    assert artifact.height == 1350
    assert artifact.duration_seconds is None
    poster_path = tmp_path / "poster.png"
    assert artifact.file_path == str(poster_path)
    assert poster_path.exists() and poster_path.stat().st_size > 0

    assert compose_result.missing_copy == [], f"copy lost: {compose_result.missing_copy}"
    assert compose_result.clipped_copy == [], f"cropped: {compose_result.clipped_copy}"


def test_produce_poster_wrong_format_raises(tmp_path):
    request = _request(format=CreativeFormat.REEL, footage_assets=[])

    with pytest.raises(PosterAdapterError, match="POSTER"):
        produce_poster(request, workdir=tmp_path)


def test_produce_poster_without_offer_text_composes_without_inventing_content(tmp_path):
    """No offer_text -> title falls back to the business name, never a made-up hook."""
    request = _request(offer_text=None)

    artifact, compose_result = produce_poster(request, workdir=tmp_path)

    assert artifact.width == 1080 and artifact.height == 1350
    assert compose_result.missing_copy == []
