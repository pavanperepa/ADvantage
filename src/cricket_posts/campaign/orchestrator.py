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

from pathlib import Path

from .meta_adapter import build_meta_preview
from .models import CampaignResult, CampaignRequest, CreativeFormat
from .poster_adapter import produce_poster
from .reel_adapter import produce_reel
from .verification import verify_poster, verify_reel


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

    if request.format == CreativeFormat.POSTER:
        artifact, compose_result = produce_poster(request, workdir=workdir)
        verification = verify_poster(artifact, compose_result)
    else:
        artifact = produce_reel(request, workdir=workdir)
        verification = verify_reel(artifact)

    meta_preview = None
    if request.budget_usd is not None:
        meta_preview = build_meta_preview(request, artifact)

    return CampaignResult(
        request=request,
        artifact=artifact,
        verification=verification,
        meta_preview=meta_preview,
    )
