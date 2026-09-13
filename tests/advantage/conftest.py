"""Test-suite guards for the campaign flow.

The poster adapter routes to the paid Ideogram API whenever
``IDEOGRAM_API_KEY`` is present in the environment, and the API server loads
``.env`` at import time. Without the guard below, simply having a working
``.env`` on the machine would make the unit suite issue real, billable image
generations -- slow, non-deterministic, and exactly the kind of incidental
paid call ``AGENTS.md`` rules out.

Tests that genuinely exercise the Ideogram path mock
``generate_from_prompt`` and set the key themselves inside the test body,
which still wins over this fixture.
"""

from __future__ import annotations

import pytest


#: Credentials whose mere presence would send a unit test to a paid or live
#: external API (Ideogram image generation, OpenAI rewording, Meta ad-account
#: reads).
PAID_API_KEYS = (
    "IDEOGRAM_API_KEY",
    "OPENAI_API_KEY",
    "META_ACCESS_TOKEN",
    "META_AD_ACCOUNT_ID",
)


@pytest.fixture(scope="session", autouse=True)
def _no_paid_api_calls():
    """Hide paid-API credentials from every test in this package by default.

    Session-scoped on purpose: the `monkeypatch` fixture is function-scoped,
    so a function-scoped guard would not cover a module- or session-scoped
    fixture that renders a poster while building its own test data -- which
    is exactly where the accidental billable call was happening.

    Set blank rather than deleted, deliberately: several adapters call
    ``load_dotenv(..., override=False)`` at call time, which would put a
    deleted key straight back and silently re-arm the paid path for every
    later test. ``override=False`` leaves an already-present variable alone,
    and every call site treats the empty string as "not configured".
    """
    patcher = pytest.MonkeyPatch()
    for name in PAID_API_KEYS:
        patcher.setenv(name, "")
    yield
    patcher.undo()
