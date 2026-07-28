from __future__ import annotations

import json
from pathlib import Path

import pytest

from cricket_posts.models import PosterContent, parse_poster_content
from cricket_posts.renderer import PROJECT_ROOT


FIXTURE_DIR = PROJECT_ROOT / "fixtures"


@pytest.fixture
def load_content():
    def loader(name: str) -> PosterContent:
        payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
        return parse_poster_content(payload)

    return loader
