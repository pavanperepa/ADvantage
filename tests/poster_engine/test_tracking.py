"""Campaign links and the QR that carries them."""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest

from cricket_posts.tracking import MIN_PX_PER_MODULE, qr_code, tracked_url

JOIN = "https://axon22yards.com/join?location=houston"


def params(url: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(url).query)


def test_a_routing_parameter_survives_being_tagged():
    """?location=houston routes the visitor; losing it breaks the destination."""
    tagged = tracked_url(JOIN, campaign="foundation-aug", source="instagram")

    assert params(tagged)["location"] == ["houston"]
    assert params(tagged)["utm_campaign"] == ["foundation-aug"]
    assert params(tagged)["utm_source"] == ["instagram"]
    assert params(tagged)["utm_medium"] == ["social"]
    assert urlsplit(tagged).path == "/join"


def test_an_untagged_link_is_left_exactly_as_it_was():
    """No campaign means no tracking, not an empty utm_ soup."""
    assert tracked_url(JOIN) == JOIN
    assert tracked_url("") == ""


def test_tagging_twice_does_not_accumulate_duplicates():
    once = tracked_url(JOIN, campaign="a", source="instagram")
    twice = tracked_url(once, campaign="b", source="instagram")

    assert params(twice)["utm_campaign"] == ["b"]
    assert len(params(twice)["utm_source"]) == 1


def test_the_code_is_sized_by_the_whole_image_not_just_the_symbol():
    """The quiet border is part of the PNG and has to be paid for.

    Sizing from the symbol alone shrinks every real module by the border's
    share — 57 rendered modules across a symbol-sized box is 3.7px each, not
    the 4 it was asked for, and that is the difference between scanning and
    not.
    """
    code = qr_code(tracked_url(JOIN, campaign="foundation-aug", source="instagram"))

    assert code is not None
    assert code.image_modules > code.modules
    assert code.rendered_px() / code.image_modules >= MIN_PX_PER_MODULE


@pytest.mark.parametrize(
    "campaign",
    ["a", "spring-camp-early-bird-2026-houston-westpark"],
)
def test_a_longer_link_gets_a_bigger_code_rather_than_smaller_modules(campaign):
    """A code that scanned yesterday must not quietly stop when a tag grows."""
    code = qr_code(tracked_url(JOIN, campaign=campaign, source="instagram"))

    assert code.rendered_px() / code.image_modules >= MIN_PX_PER_MODULE


def test_no_destination_means_no_code():
    assert qr_code("") is None
