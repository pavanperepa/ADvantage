from __future__ import annotations

import os

import pytest

from cricket_posts.layout import plan_design
from cricket_posts.models import BrandProfile
from cricket_posts.openai_studio import OpenAIStudioProvider


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_AI_TESTS") != "1",
    reason="Set RUN_LIVE_AI_TESTS=1 to run paid live API smoke tests.",
)
def test_live_openai_extract_and_plan():
    provider = OpenAIStudioProvider()
    source = (
        "Organization: Boundary Cricket\n"
        "Title: Lane Booking Open\n"
        "Price: $35 per hour\n"
        "Contact: +1 (469) 555-0188"
    )
    content = provider.extract(source)
    suggestion = provider.plan(content)
    design = plan_design(content, BrandProfile(name="Boundary Cricket"), suggestion)

    assert content.title == "Lane Booking Open"
    assert "$35 per hour" in content.display_strings()
    assert design.art_prompt
