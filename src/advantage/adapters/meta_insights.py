"""Read-only Meta Ads insights, for grounding the campaign rationale.

Strictly GET-only: this module never constructs, updates, or deletes a Meta
object, and has no function that could. It fetches account-lifetime
performance plus placement and age/gender breakdowns for the configured ad
account, and reduces them to a small typed summary. If credentials are
missing, the call fails, or the account has no delivery history, it returns a
clearly-marked "unavailable" result (``available=False`` with a ``reason``)
instead of raising -- a caller (``application/rationale.py``) should be able
to treat "no Meta history" as a normal, expected case, not an error to catch.

The access token is read from the environment and used only as a request
query parameter; it is never printed, logged, or included in any returned
value or error message.
"""

from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[3]
GRAPH_ROOT = "https://graph.facebook.com"
DEFAULT_API_VERSION = "v24.0"
DEFAULT_TIMEOUT_SECONDS = 15.0


class PlacementInsight(BaseModel):
    """One placement's lifetime performance (e.g. Reels, Feed)."""

    model_config = ConfigDict(extra="forbid")

    placement: str
    impressions: int
    ctr_pct: float


class AgeBandInsight(BaseModel):
    """One age band's lifetime performance."""

    model_config = ConfigDict(extra="forbid")

    age_range: str
    impressions: int
    ctr_pct: float


class MetaInsightsSummary(BaseModel):
    """A reduced, typed summary of one ad account's lifetime performance.

    ``available=False`` is the normal, expected result when credentials are
    absent or the account has no history yet -- callers must check it before
    trusting any other field.
    """

    model_config = ConfigDict(extra="forbid")

    available: bool
    reason: str | None = None
    account_id: str | None = None

    lifetime_impressions: int | None = None
    lifetime_clicks: int | None = None
    average_ctr_pct: float | None = None
    average_cpc_usd: float | None = None
    average_cpm_usd: float | None = None

    top_placements: list[PlacementInsight] = Field(default_factory=list)
    best_age_bands: list[AgeBandInsight] = Field(default_factory=list)


def _unavailable(reason: str) -> MetaInsightsSummary:
    return MetaInsightsSummary(available=False, reason=reason)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _placement_label(row: dict) -> str:
    platform = row.get("publisher_platform") or "unknown"
    position = row.get("platform_position") or ""
    return f"{platform}/{position}" if position else str(platform)


def _age_band_label(row: dict) -> str:
    return str(row.get("age") or "unknown")


def fetch_account_insights(
    *,
    token: str | None = None,
    account_id: str | None = None,
    api_version: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    top_n: int = 3,
) -> MetaInsightsSummary:
    """Fetch a small, safe lifetime-performance summary for one ad account.

    GET requests only. Returns ``MetaInsightsSummary(available=False, ...)``
    -- never raises -- when credentials are missing, any request fails, the
    response is malformed, or the account has no lifetime delivery.
    """
    load_dotenv(ROOT / ".env", override=False)
    token = token or os.environ.get("META_ACCESS_TOKEN")
    account_id = account_id or os.environ.get("META_AD_ACCOUNT_ID")
    api_version = api_version or os.environ.get("META_API_VERSION", DEFAULT_API_VERSION)

    if not token or not account_id:
        return _unavailable(
            "META_ACCESS_TOKEN and/or META_AD_ACCOUNT_ID are not configured; "
            "no account read was attempted."
        )

    account = f"act_{account_id}" if not str(account_id).startswith("act_") else str(account_id)
    base = f"{GRAPH_ROOT}/{api_version}/{account}/insights"

    def _get(params: dict) -> list[dict]:
        request_params = dict(params)
        request_params["access_token"] = token
        response = requests.get(base, params=request_params, timeout=timeout)
        body = response.json()
        if not response.ok or "error" in body:
            message = "Meta insights request failed"
            if isinstance(body, dict) and isinstance(body.get("error"), dict):
                message = f"{message}: {body['error'].get('message', 'unknown error')}"
            raise RuntimeError(message)
        return body.get("data", [])

    try:
        lifetime_rows = _get(
            {
                "level": "account",
                "date_preset": "maximum",
                "fields": "impressions,clicks,ctr,cpc,cpm",
            }
        )
        placement_rows = _get(
            {
                "level": "account",
                "date_preset": "maximum",
                "breakdowns": "publisher_platform,platform_position",
                "fields": "impressions,clicks,ctr",
            }
        )
        demographic_rows = _get(
            {
                "level": "account",
                "date_preset": "maximum",
                "breakdowns": "age,gender",
                "fields": "impressions,clicks,ctr",
            }
        )
    except RuntimeError as exc:
        # Raised by _get() above for a Graph API error payload; the message is
        # built from the Graph API's own error text (never from request
        # params), so it is safe to surface directly.
        return _unavailable(str(exc))
    except Exception as exc:
        # Any other failure: network error, timeout, non-JSON body, etc.
        # Never surface str(exc) here -- some exception types (including
        # requests' own) embed the full request URL, which contains the
        # access_token query parameter, in their message.
        return _unavailable(f"Meta insights request failed: {exc.__class__.__name__}")

    if not lifetime_rows:
        return _unavailable("This ad account has no lifetime delivery history yet.")

    lifetime = lifetime_rows[0]
    lifetime_impressions = _safe_int(lifetime.get("impressions"))
    if lifetime_impressions <= 0:
        return _unavailable("This ad account has no lifetime delivery history yet.")

    top_placements = sorted(
        (
            PlacementInsight(
                placement=_placement_label(row),
                impressions=_safe_int(row.get("impressions")),
                ctr_pct=_safe_float(row.get("ctr")),
            )
            for row in placement_rows
            if _safe_int(row.get("impressions")) > 0
        ),
        key=lambda placement: placement.impressions,
        reverse=True,
    )[:top_n]

    # Collapse gender rows into one entry per age band by summing impressions
    # and taking an impression-weighted CTR, then rank by CTR (a band with
    # very few impressions winning on CTR alone is a coincidence, not signal).
    by_age: dict[str, dict[str, float]] = {}
    for row in demographic_rows:
        band = _age_band_label(row)
        entry = by_age.setdefault(band, {"impressions": 0.0, "weighted_ctr": 0.0})
        impressions = _safe_float(row.get("impressions"))
        entry["impressions"] += impressions
        entry["weighted_ctr"] += _safe_float(row.get("ctr")) * impressions

    best_age_bands = sorted(
        (
            AgeBandInsight(
                age_range=band,
                impressions=int(values["impressions"]),
                ctr_pct=(values["weighted_ctr"] / values["impressions"])
                if values["impressions"]
                else 0.0,
            )
            for band, values in by_age.items()
            if values["impressions"] > 0
        ),
        key=lambda band: band.ctr_pct,
        reverse=True,
    )[:top_n]

    return MetaInsightsSummary(
        available=True,
        account_id=str(account_id),
        lifetime_impressions=lifetime_impressions,
        lifetime_clicks=_safe_int(lifetime.get("clicks")),
        average_ctr_pct=_safe_float(lifetime.get("ctr")),
        average_cpc_usd=_safe_float(lifetime.get("cpc")),
        average_cpm_usd=_safe_float(lifetime.get("cpm")),
        top_placements=top_placements,
        best_age_bands=best_age_bands,
    )
