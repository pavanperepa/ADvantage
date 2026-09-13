"""One verification pass over a produced CampaignArtifact, before it reaches
the owner.

Deliberately one pass, not the two-QA-plus-repair loop the original planning
docs describe (deterministic checks, a separate independent multimodal
inspector, bounded auto-repair and recheck). Per today's scope cut: a single
honest pass that surfaces findings is the win condition. Nothing here repairs
anything automatically -- a human looks at whatever gets flagged.

Poster verification reads `ComposeResult`'s own audit data (`missing_copy`,
`clipped_copy`, `fit`, `dead`, `footer_contrast`) rather than re-deriving it --
those numbers are already `compose()`'s ground truth for this exact render, so
recomputing them would just be trusting the same measurement twice.

Reel verification re-checks the rendered file directly rather than trusting
`reel_adapter.produce_reel()`'s own success return. `produce_reel` already
raises on a bad render, so in practice this rarely finds anything new -- but
an independent look at the artifact, not just the producer's self-report, is
the same "inspector receives the final artifact separately from the
producer's self-assessment" principle this project's planning docs describe
for image QA, applied here in its simplest possible form.
"""

from __future__ import annotations

from pathlib import Path

from ..pipeline import DEAD_SPACE_LIMIT, ComposeResult
from .models import CampaignArtifact, VerificationResult

POSTER_WIDTH = 1080
POSTER_HEIGHT = 1350
REEL_WIDTH = 1080
REEL_HEIGHT = 1920

# A reel far shorter or longer than this is very likely a construction bug
# (e.g. a single-frame render or a runaway timeline), not a legitimate creative
# choice -- generous bounds on purpose, this is a sanity check, not a style rule.
REEL_MIN_SECONDS = 2.0
REEL_MAX_SECONDS = 40.0

#: README.md documents this as the poster pipeline's own contrast gate.
FOOTER_CONTRAST_FLOOR = 4.5


def verify_poster(artifact: CampaignArtifact, compose_result: ComposeResult) -> VerificationResult:
    """Check a composed poster against compose()'s own audit data plus dimensions."""
    findings: list[str] = []

    if (artifact.width, artifact.height) != (POSTER_WIDTH, POSTER_HEIGHT):
        findings.append(
            f"Poster is {artifact.width}x{artifact.height}, expected "
            f"{POSTER_WIDTH}x{POSTER_HEIGHT}."
        )
    if compose_result.missing_copy:
        findings.append(
            "Copy missing from the rendered poster: " + ", ".join(compose_result.missing_copy)
        )
    if compose_result.clipped_copy:
        findings.append(
            "Copy clipped or pushed off-canvas: " + ", ".join(compose_result.clipped_copy)
        )
    if not compose_result.fit.fits:
        overlong = ", ".join(compose_result.fit.overlong_fields) or "unspecified field"
        findings.append(f"Copy did not fit the canvas (overlong: {overlong}).")
    if not compose_result.dead.ok:
        findings.append(
            f"Dead space covers {compose_result.dead.fraction:.0%} of the canvas "
            f"(limit {DEAD_SPACE_LIMIT:.0%})."
        )
    if (
        compose_result.footer_contrast is not None
        and compose_result.footer_contrast < FOOTER_CONTRAST_FLOOR
    ):
        findings.append(
            f"Footer contrast {compose_result.footer_contrast:.2f}:1 is below the "
            f"{FOOTER_CONTRAST_FLOOR:.1f}:1 floor."
        )

    return VerificationResult(passed=not findings, findings=findings)


def verify_reel(artifact: CampaignArtifact) -> VerificationResult:
    """Independently re-check a produced reel's basic facts from the file itself."""
    path = Path(artifact.file_path)
    if not path.exists() or path.stat().st_size == 0:
        return VerificationResult(
            passed=False, findings=[f"Reel file is missing or empty: {path}"]
        )

    findings: list[str] = []
    if (artifact.width, artifact.height) != (REEL_WIDTH, REEL_HEIGHT):
        findings.append(
            f"Reel is {artifact.width}x{artifact.height}, expected {REEL_WIDTH}x{REEL_HEIGHT}."
        )
    if artifact.duration_seconds is None or artifact.duration_seconds <= 0:
        findings.append("Reel has no valid duration.")
    elif artifact.duration_seconds > REEL_MAX_SECONDS:
        findings.append(
            f"Reel runs {artifact.duration_seconds:.1f}s, longer than the "
            f"{REEL_MAX_SECONDS:.0f}s sanity limit."
        )
    elif artifact.duration_seconds < REEL_MIN_SECONDS:
        findings.append(
            f"Reel runs only {artifact.duration_seconds:.1f}s, shorter than the "
            f"{REEL_MIN_SECONDS:.0f}s sanity minimum."
        )

    return VerificationResult(passed=not findings, findings=findings)
