"""Meta Ads preview and paused-creation adapter for the simplified campaign flow.

Two entry points, matching today's hackathon-day contract in
``src/advantage/domain/models.py``:

* :func:`build_meta_preview` -- pure, makes no network calls, and derives the
  Meta ad payload fields (campaign name, objective, budget, copy, CTA,
  destination) from a ``CampaignRequest``/``CampaignArtifact`` pair instead of
  the hardcoded constants in
  ``reference/main/scripts/meta_ads_create_campaign.py``.
* :func:`create_paused_campaign` -- defaults to a dry run (``execute=False``):
  builds every payload and returns a result with **zero HTTP requests**. With
  ``execute=True`` it creates a campaign, ad set, and ad, all with
  ``status=PAUSED``, then performs a GET read-back on each created object
  (mirroring ``scripts/meta/meta_ads_monitor.py``'s ``fetch()``) to confirm they
  actually came back PAUSED before reporting success. It never sets any status
  other than PAUSED -- there is no activation/unpause path here, full stop.

On reusing vs. reimplementing ``Graph``
----------------------------------------
The ``Graph`` wrapper below is *adapted* from
``reference/main/scripts/meta_ads_create_campaign.py`` rather than imported
from it, for two
concrete reasons:

1. ``scripts/`` has no ``__init__.py`` -- it is a folder of standalone CLI
   entry points, not a package on this project's import path. Importing it
   from ``src/advantage`` would need ``sys.path`` surgery that would only
   work in some run contexts (plain pytest) and not others (the installed
   package, a future web worker), which is exactly the kind of fragility this
   hackathon build should avoid.
2. More importantly, the script's ``Graph._unwrap`` raises ``SystemExit`` on
   any Graph API error. That is fine for a standalone CLI (it just exits the
   process with a message) but wrong for library code that a web app calls
   in-process: ``SystemExit`` is not caught by ``except Exception`` and would
   tear down the whole server on a single failed Graph API call. This module
   keeps the exact same structure and behavior (dry-run short-circuits every
   POST before any network call, the token is never printed or logged) but
   raises :class:`MetaGraphError`, an ordinary exception, instead.

Lead-generation forms (``create_lead_form`` / ``PROVEN_FORM_ID`` in the
original script) are intentionally not reproduced here: ``CampaignRequest``
carries a ``destination_url`` but no lead-form identifiers, so this module
builds plain link-click ads (image or video) against that URL rather than
inventing a forms workflow the request model does not describe.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from ..domain.models import (
    CampaignArtifact,
    CampaignRequest,
    CreativeFormat,
    MetaAdPreview,
    MetaAdResult,
)

ROOT = Path(__file__).resolve().parents[3]
GRAPH_ROOT = "https://graph.facebook.com"
DEFAULT_API_VERSION = "v24.0"

# Account infrastructure, not campaign copy: the Facebook Page this account
# advertises from. Same value as the reference Meta creator. There is
# no per-request field for this yet (CampaignRequest has no page identifier),
# so -- unlike the campaign name/copy/budget -- it stays a module constant.
PAGE_ID = "346097132754442"


class MissingBudgetError(ValueError):
    """Raised when a Meta ad preview/creation is attempted with no budget.

    A poster or reel can still be produced with ``request.budget_usd`` unset;
    Meta ad prep specifically needs a real number to compute a daily/lifetime
    budget, so this is raised early and distinctly rather than letting a
    ``None`` propagate into arithmetic or a Graph API payload.
    """


class MetaGraphError(RuntimeError):
    """Raised for a Graph API error response (see module docstring)."""


class MetaVerificationError(RuntimeError):
    """Raised when a created object's read-back does not confirm PAUSED."""


class Graph:
    """Thin Graph API wrapper: dry-run short-circuits every POST before any
    network call, and errors raise :class:`MetaGraphError` rather than
    printing/logging the token or the raw response.
    """

    def __init__(self, token: str, version: str, account_id: str, dry_run: bool) -> None:
        self.token = token
        self.base = f"{GRAPH_ROOT}/{version}"
        self.account = f"act_{account_id}"
        self.dry_run = dry_run

    def get(self, path: str, **params: Any) -> dict:
        params["access_token"] = self.token
        response = requests.get(f"{self.base}/{path}", params=params, timeout=60)
        return self._unwrap(response)

    def post(self, path: str, files: Any = None, token: str | None = None,
             **payload: Any) -> dict:
        printable = {k: v for k, v in payload.items()}
        print(f"\n  POST {path}")
        print("  " + json.dumps(printable, indent=2)[:2000].replace("\n", "\n  "))
        if self.dry_run:
            return {"id": f"<dry-run:{path}>"}
        payload["access_token"] = token or self.token
        response = requests.post(
            f"{self.base}/{path}", data=payload, files=files, timeout=600
        )
        return self._unwrap(response)

    @staticmethod
    def _unwrap(response: requests.Response) -> dict:
        try:
            body = response.json()
        except ValueError:
            response.raise_for_status()
            raise
        if "error" in body:
            error = body["error"]
            raise MetaGraphError(
                f"Graph API error {error.get('code')}/{error.get('error_subcode')}: "
                f"{error.get('message')}"
            )
        return body


def upload_video(graph: Graph, path: Path) -> str:
    """Upload a reel and block until Meta finishes transcoding it.

    Same behavior as the reference Meta creator: in dry-run mode
    the local file is still opened (so a missing artifact fails fast even
    before ``--execute``), but ``Graph.post`` returns before any network call,
    and the polling loop below never runs because it returns immediately after
    the dry-run post.
    """
    if not path.exists():
        raise MetaGraphError(f"Video not found: {path}")
    size_mb = path.stat().st_size / 1_048_576
    print(f"\nUploading {path.name} ({size_mb:.1f} MB)...")
    with path.open("rb") as handle:
        created = graph.post(
            f"{graph.account}/advideos",
            files={"source": (path.name, handle, "video/mp4")},
            name=path.stem,
        )
    video_id = created["id"]
    if graph.dry_run:
        return video_id

    for attempt in range(60):
        status = graph.get(video_id, fields="status").get("status", {})
        state = status.get("video_status")
        if state == "ready":
            print(f"  video {video_id} ready")
            return video_id
        if state == "error":
            raise MetaGraphError(f"Video processing failed: {status}")
        print(f"  processing ({state})... {attempt * 10}s")
        time.sleep(10)
    raise MetaGraphError("Timed out waiting for video processing")


def pick_thumbnail(graph: Graph, video_id: str) -> str | None:
    """Meta requires a thumbnail for video creatives; prefer its own pick."""
    if graph.dry_run:
        return None
    thumbs = graph.get(f"{video_id}/thumbnails").get("data", [])
    if not thumbs:
        return None
    preferred = next((t for t in thumbs if t.get("is_preferred")), thumbs[0])
    return preferred.get("uri")


def upload_image(graph: Graph, path: Path) -> str:
    """Upload a static creative PNG via ``/adimages`` and return its image hash.

    Mirrors :func:`upload_video`'s shape: open the local file, POST it through
    the same ``Graph.post`` wrapper (so dry-run behaves identically -- no
    network call), then pull the hash out of Meta's ``{"images": {...}}``
    response shape once ``--execute`` actually talks to the API.
    """
    if not path.exists():
        raise MetaGraphError(f"Image not found: {path}")
    size_mb = path.stat().st_size / 1_048_576
    print(f"\nUploading {path.name} ({size_mb:.1f} MB)...")
    with path.open("rb") as handle:
        created = graph.post(
            f"{graph.account}/adimages",
            files={"filename": (path.name, handle, "image/png")},
        )
    if graph.dry_run:
        return f"<dry-run:{path.name}>"

    images = created.get("images") or {}
    for meta in images.values():
        image_hash = meta.get("hash")
        if image_hash:
            return image_hash
    raise MetaGraphError(f"Meta did not return an image hash for {path.name}: {created}")


def _build_targeting(request: CampaignRequest) -> dict:
    """Broad, country-level targeting.

    The earlier reference creator found broad targeting (no interest
    stacking) outperformed interest-based targeting in this account.
    ``CampaignRequest`` doesn't carry a venue/location fact yet, so this
    defaults to a broad US audience rather than inventing coordinates; add a
    location field and thread it through here once the request model has one.
    """
    return {
        "age_min": 18,
        "age_max": 65,
        "geo_locations": {"countries": ["US"]},
        "targeting_automation": {"advantage_audience": 1},
    }


def _campaign_name(request: CampaignRequest) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", request.business_name).strip("_").upper()
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{slug or 'BUSINESS'}_{request.format.value.upper()}_{today}"


def _objective(request: CampaignRequest) -> str:
    """OUTCOME_LEADS matches this account's own proven history. Kept as a
    function (not a bare top-level constant) so it is a real decision point;
    it does not yet vary by request field because there's nothing on
    CampaignRequest to condition it on beyond format, which does not change
    the objective here -- only the ad-level creative changes per format."""
    return "OUTCOME_LEADS"


def _primary_text(request: CampaignRequest) -> str:
    """Template only -- not a copywriting pass. Business + brief + offer +
    phone, in that order, skipping anything the request didn't supply."""
    parts = [f"{request.business_name}: {request.brief_text.strip()}"]
    if request.offer_text:
        parts.append(request.offer_text.strip())
    if request.contact_phone:
        parts.append(f"Call or text {request.contact_phone} to learn more.")
    return "\n\n".join(part for part in parts if part)


def _headline(request: CampaignRequest) -> str:
    if request.audience:
        return f"{request.business_name} — {request.audience}"
    return request.business_name


def _call_to_action(request: CampaignRequest) -> str:
    if request.destination_url:
        return "LEARN_MORE"
    if request.contact_phone:
        return "CALL_NOW"
    return "LEARN_MORE"


def _call_to_action_payload(preview: MetaAdPreview) -> dict:
    payload: dict[str, Any] = {"type": preview.call_to_action}
    if preview.destination_url:
        payload["value"] = {"link": preview.destination_url}
    return payload


def build_meta_preview(request: CampaignRequest, artifact: CampaignArtifact) -> MetaAdPreview:
    """Derive a read-only Meta ad preview from the request and its artifact.

    Raises :class:`MissingBudgetError` if ``request.budget_usd`` is not set --
    a poster/reel can be produced without a budget, but Meta prep cannot.
    """
    if request.budget_usd is None:
        raise MissingBudgetError(
            "request.budget_usd is required to prepare a Meta ad preview "
            "(a poster or reel can still be produced without one)."
        )
    return MetaAdPreview(
        campaign_name=_campaign_name(request),
        objective=_objective(request),
        daily_budget_usd=round(request.budget_usd / request.campaign_days, 2),
        days=request.campaign_days,
        primary_text=_primary_text(request),
        headline=_headline(request),
        call_to_action=_call_to_action(request),
        destination_url=request.destination_url,
        creative_format=artifact.format,
    )


def _verify_paused(graph: Graph, label: str, object_id: str) -> None:
    """GET an object back and confirm it is PAUSED (mirrors monitor.py's fetch()).

    A failure here is a hard failure: this raises rather than letting
    ``create_paused_campaign`` return a success result for an object that did
    not actually come back paused.
    """
    check = graph.get(object_id, fields="id,status,effective_status")
    if check.get("status") != "PAUSED":
        raise MetaVerificationError(
            f"{label} {object_id} did not read back as PAUSED "
            f"(status={check.get('status')!r}, "
            f"effective_status={check.get('effective_status')!r})."
        )


def create_paused_campaign(
    request: CampaignRequest,
    artifact: CampaignArtifact,
    preview: MetaAdPreview,
    *,
    execute: bool = False,
) -> MetaAdResult:
    """Build (and, with ``execute=True``, create) a PAUSED campaign/ad set/ad.

    Defaults to a dry run: every payload is built and printed, and the
    function returns a ``MetaAdResult(dry_run=True, ...)`` without a single
    HTTP request. Never creates anything with a status other than PAUSED --
    there is no parameter, flag, or code path here that activates or unpauses
    anything.
    """
    if request.budget_usd is None:
        raise MissingBudgetError(
            "request.budget_usd is required to create a Meta campaign."
        )

    load_dotenv(ROOT / ".env")
    token = os.environ.get("META_ACCESS_TOKEN") or ""
    account_id = os.environ.get("META_AD_ACCOUNT_ID") or ""
    if execute and (not token or not account_id):
        raise MetaGraphError(
            "META_ACCESS_TOKEN and META_AD_ACCOUNT_ID must be set in .env to execute."
        )

    graph = Graph(
        token,
        os.environ.get("META_API_VERSION", DEFAULT_API_VERSION),
        account_id,
        dry_run=not execute,
    )

    start = datetime.now(timezone.utc) + timedelta(minutes=15)
    end = start + timedelta(days=preview.days)

    campaign = graph.post(
        f"{graph.account}/campaigns",
        name=preview.campaign_name,
        objective=preview.objective,
        buying_type="AUCTION",
        bid_strategy="LOWEST_COST_WITHOUT_CAP",
        lifetime_budget=int(round(request.budget_usd * 100)),
        special_ad_categories=json.dumps([]),
        status="PAUSED",
    )

    adset = graph.post(
        f"{graph.account}/adsets",
        name=f"{preview.campaign_name}_ADSET",
        campaign_id=campaign["id"],
        optimization_goal="LINK_CLICKS",
        billing_event="IMPRESSIONS",
        destination_type="WEBSITE" if preview.destination_url else "ON_AD",
        targeting=json.dumps(_build_targeting(request)),
        start_time=start.isoformat(),
        end_time=end.isoformat(),
        status="PAUSED",
    )

    if artifact.format == CreativeFormat.REEL:
        video_id = upload_video(graph, Path(artifact.file_path))
        thumbnail = pick_thumbnail(graph, video_id)
        video_data: dict[str, Any] = {
            "video_id": video_id,
            "title": preview.headline,
            "message": preview.primary_text,
            "call_to_action": _call_to_action_payload(preview),
        }
        if thumbnail:
            video_data["image_url"] = thumbnail
        story_spec: dict[str, Any] = {"page_id": PAGE_ID, "video_data": video_data}
    elif artifact.format == CreativeFormat.POSTER:
        image_hash = upload_image(graph, Path(artifact.file_path))
        link_data: dict[str, Any] = {
            "image_hash": image_hash,
            "message": preview.primary_text,
            "name": preview.headline,
            "call_to_action": _call_to_action_payload(preview),
        }
        if preview.destination_url:
            link_data["link"] = preview.destination_url
        story_spec = {"page_id": PAGE_ID, "link_data": link_data}
    else:  # pragma: no cover - CreativeFormat has exactly these two members
        raise ValueError(f"Unsupported creative format: {artifact.format!r}")

    creative = graph.post(
        f"{graph.account}/adcreatives",
        name=f"{preview.campaign_name}_CREATIVE",
        object_story_spec=json.dumps(story_spec),
        # Keep Meta from re-cropping or overlaying the composed creative.
        degrees_of_freedom_spec=json.dumps(
            {"creative_features_spec": {"standard_enhancements": {"enroll_status": "OPT_OUT"}}}
        ),
    )

    ad = graph.post(
        f"{graph.account}/ads",
        name=f"{preview.campaign_name}_AD",
        adset_id=adset["id"],
        creative=json.dumps({"creative_id": creative["id"]}),
        status="PAUSED",
    )

    if not execute:
        return MetaAdResult(
            dry_run=True,
            campaign_id=campaign["id"],
            ad_set_id=adset["id"],
            creative_id=creative["id"],
            ad_id=ad["id"],
            status="DRY_RUN",
        )

    # Read every created object back before declaring success. If any of
    # these don't confirm PAUSED, _verify_paused raises -- this function must
    # never return a success result for an object that isn't actually paused.
    _verify_paused(graph, "campaign", campaign["id"])
    _verify_paused(graph, "ad set", adset["id"])
    _verify_paused(graph, "ad", ad["id"])

    return MetaAdResult(
        dry_run=False,
        campaign_id=campaign["id"],
        ad_set_id=adset["id"],
        creative_id=creative["id"],
        ad_id=ad["id"],
        status="PAUSED",
    )
