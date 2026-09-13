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
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from ..adapters import poster as poster_adapter
from ..adapters import reel_plan
from ..adapters.meta_ads import build_meta_preview
from ..adapters.meta_insights import fetch_account_insights
from ..adapters.poster import produce_poster
from ..adapters.reel import produce_reel
from ..domain.models import (
    ActivityStep,
    CampaignRequest,
    CampaignResult,
    CreativeCritique,
    CreativeFormat,
    CreativePlan,
    resolve_palette,
)
from .critique import review_creative
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

    log = _ActivityLog()

    plan: CreativePlan | None = None
    if request.format == CreativeFormat.POSTER:
        with log.step("Generating the poster", f"{_palette_label(request)} palette"):
            artifact, compose_result = produce_poster(request, workdir=workdir)
        with log.step("Checking the file", "dimensions, copy, contrast"):
            verification = verify_poster(artifact, compose_result)
        plan = _safe_plan(lambda: poster_adapter.describe_plan(request))
    else:
        usable = len([asset for asset in request.footage_assets if asset.local_ref])
        with log.step("Editing the reel", f"{usable} clip(s), {_feel_label(request)} feel"):
            artifact = produce_reel(request, workdir=workdir)
        with log.step("Checking the file", "dimensions, duration"):
            verification = verify_reel(artifact)
        # The plan is described against the shots that actually survived
        # `produce_reel`'s trimming, not the raw asset count, so what the
        # owner reads matches what was rendered.
        plan = _safe_plan(lambda: reel_plan.describe_plan(request, usable))

    # An independent look at the finished artifact, separate from the
    # structural check above: `verify_*` answers "is this file correct",
    # `review_creative` answers "is this any good, and what went wrong".
    critique = None
    with log.step("Reviewing the result", "looking for dead space and weak spots") as step:
        critique = _safe_critique(artifact, request, plan, verification)
        if critique is None:
            step.status = "failed"
        elif not critique.model_reviewed:
            step.detail = "automated measurements only (no vision model)"

    meta_preview = None
    rationale = None
    if request.budget_usd is not None:
        with log.step("Building the Meta ad", "objective, budget, audience, CTA"):
            meta_preview = build_meta_preview(request, artifact)
        with log.step("Explaining the campaign", "grounding it in account history") as step:
            rationale = _safe_rationale(request, artifact, meta_preview, plan)
            if rationale is not None and not rationale.meta_account_grounded:
                step.detail = "no ad-account history available; used platform defaults"
    else:
        log.skip("Building the Meta ad", "no budget set on this request")

    return CampaignResult(
        request=request,
        artifact=artifact,
        verification=verification,
        meta_preview=meta_preview,
        plan=plan,
        rationale=rationale,
        critique=critique,
        activity=log.steps,
    )


def _palette_label(request: CampaignRequest) -> str:
    return resolve_palette(request.palette).label


def _feel_label(request: CampaignRequest) -> str:
    return (request.reel_feel.value if request.reel_feel else "high energy").replace("_", " ")


class _ActivityLog:
    """Collects owner-facing ``ActivityStep``s as the run progresses.

    Deliberately dumb: it times a block and records what happened. It exists
    because a generate call is otherwise an opaque wait, and an owner has no
    way to tell a slow render from a silent fallback.
    """

    def __init__(self) -> None:
        self.steps: list[ActivityStep] = []

    @contextmanager
    def step(self, label: str, detail: str = "") -> "Iterator[ActivityStep]":
        entry = ActivityStep(label=label, detail=detail)
        started = time.monotonic()
        try:
            yield entry
        except Exception:
            entry.status = "failed"
            entry.seconds = round(time.monotonic() - started, 2)
            self.steps.append(entry)
            raise
        entry.seconds = round(time.monotonic() - started, 2)
        self.steps.append(entry)

    def skip(self, label: str, detail: str) -> None:
        self.steps.append(ActivityStep(label=label, detail=detail, status="skipped"))


def _safe_critique(artifact, request, plan, verification) -> CreativeCritique | None:
    """`review_creative` already swallows its own failures; this is one more
    layer so an unexpected error in the *description* of a creative can never
    discard the creative itself."""
    try:
        return review_creative(artifact, request, plan, verification)
    except Exception:  # noqa: BLE001 - critique is strictly optional
        logger.exception("Could not review the creative; continuing without a critique.")
        return None


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
