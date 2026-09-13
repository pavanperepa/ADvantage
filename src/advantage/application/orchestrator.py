"""The single entry point for the simplified campaign flow.

``run_campaign()`` is the one function a caller (today: our own happy-path
check; eventually: the web UI) needs to know about: given a
``CampaignRequest``, it dispatches to the right creative adapter (poster or
reel), runs the one verification pass, and -- when the request has a budget
-- builds a read-only Meta ad preview.

It never creates anything on Meta. ``meta_adapter.create_paused_campaign``
is a separate, explicitly authorized step the (future) UI calls only after a
human has looked at the artifact, the verification findings, and the
preview -- keeping "produce a creative" and "publish a creative" as two
different actions is the one piece of the original approval-gating design
this simplified build keeps, because collapsing it would mean a request
alone could result in an external write.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from ..adapters import poster as poster_adapter
from ..adapters import reel_plan
from ..adapters.meta_ads import build_meta_preview
from ..adapters.meta_insights import fetch_account_insights
from ..adapters.poster import produce_poster
from ..adapters.reel import produce_reel
from ..domain.models import CampaignResult, CampaignRequest, CreativeFormat, CreativePlan
from .rationale import build_rationale
from .verification import verify_poster, verify_reel


logger = logging.getLogger(__name__)


class OrchestratorError(RuntimeError):
    """Raised when a CampaignRequest cannot be run at all (see request.blockers())."""


def run_campaign(request: CampaignRequest, *, workdir: Path) -> CampaignResult:
    """Generate, verify, and (budget permitting) preview one campaign request.

    Does not raise on a failed verification -- a human decides what to do
    with the findings, matching the "no auto-repair" scope cut. Does raise
    ``OrchestratorError`` if the request can't produce its format at all
    (``request.blockers()``, e.g. a reel with no footage selected).
    """
    blockers = request.blockers()
    if blockers:
        raise OrchestratorError("Cannot run campaign: " + " ".join(blockers))

    plan: CreativePlan | None = None
    if request.format == CreativeFormat.POSTER:
        artifact, compose_result = produce_poster(request, workdir=workdir)
        verification = verify_poster(artifact, compose_result)
        plan = _safe_plan(lambda: poster_adapter.describe_plan(request))
    else:
        artifact = produce_reel(request, workdir=workdir)
        verification = verify_reel(artifact)
        # The plan is described against the shots that actually survived
        # `produce_reel`'s trimming, not the raw asset count, so what the
        # owner reads matches what was rendered.
        usable = len([asset for asset in request.footage_assets if asset.local_ref])
        plan = _safe_plan(lambda: reel_plan.describe_plan(request, usable))

    meta_preview = None
    rationale = None
    if request.budget_usd is not None:
        meta_preview = build_meta_preview(request, artifact)
        rationale = _safe_rationale(request, artifact, meta_preview, plan)

    return CampaignResult(
        request=request,
        artifact=artifact,
        verification=verification,
        meta_preview=meta_preview,
        plan=plan,
        rationale=rationale,
    )


def _safe_plan(build: Callable[[], CreativePlan]) -> CreativePlan | None:
    """A plan is an explanation of work already done, so failing to build one
    must never discard a successfully rendered artifact -- the owner still
    gets their creative, just without the "why" panel."""
    try:
        return build()
    except Exception:  # noqa: BLE001 - explanation is strictly optional
        logger.exception("Could not describe the creative plan; continuing without it.")
        return None


def _safe_rationale(request, artifact, preview, plan):
    """Same rule as `_safe_plan`, plus: the Meta account read is best-effort.

    `fetch_account_insights` already returns an "unavailable" summary rather
    than raising, and `build_rationale` marks `meta_account_grounded=False`
    in that case, so a missing token degrades to an honest, ungrounded
    explanation instead of an error.
    """
    try:
        insights = fetch_account_insights()
    except Exception:  # noqa: BLE001 - defence in depth; the adapter shouldn't raise
        logger.exception("Meta insights read failed; building an ungrounded rationale.")
        insights = None
    try:
        return build_rationale(request, artifact, preview, plan, insights=insights)
    except Exception:  # noqa: BLE001 - explanation is strictly optional
        logger.exception("Could not build the campaign rationale; continuing without it.")
        return None
