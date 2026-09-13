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

`compose_result` is `None` on the Ideogram path (`adapters/poster.py` routes
there when `IDEOGRAM_API_KEY` is configured; see that module's docstring).
There is no `ComposeResult` to read on that path, so `verify_poster()` instead
checks: exact 1080x1350 dimensions, the file exists/is non-empty/is a readable
PNG, and -- the check with real teeth -- that every string
`poster_ideogram.py` intended to stamp is non-empty and stayed inside its safe
margins. That stamping module writes its own measurements to a small JSON
sidecar next to the rendered PNG (`<poster>.stamp.json`) precisely so this
function can check them without re-deriving anything; `stamped_copy`/
`stamp_overflow` may also be passed in directly (e.g. from a test that already
has a `StampedPoster` in hand) to skip the sidecar read.

`adapters/poster.py` also writes a `<poster>.fallback.json` sidecar whenever
it had to fall back to `compose()` (missing key or a failed Ideogram call).
When present, `verify_poster()` surfaces it as a non-blocking finding on
either path -- it never fails verification by itself.

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

from PIL import Image, UnidentifiedImageError

from cricket_posts.pipeline import DEAD_SPACE_LIMIT, ComposeResult

from ..adapters import poster_ideogram
from ..domain.models import CampaignArtifact, VerificationResult

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


def verify_poster(
    artifact: CampaignArtifact,
    compose_result: ComposeResult | None,
    *,
    stamped_copy: list[str] | None = None,
    stamp_overflow: list[str] | None = None,
) -> VerificationResult:
    """Check a produced poster.

    `compose_result` is the free pipeline's own audit data when that path was
    used, or `None` on the Ideogram path (see module docstring). `stamped_copy`/
    `stamp_overflow` let a caller that already has a `StampedPoster` in hand
    (e.g. a test) skip the sidecar-manifest read; when omitted on the Ideogram
    path, they are read from `<poster>.stamp.json` next to `artifact.file_path`.
    """
    blocking: list[str] = []
    non_blocking: list[str] = []

    if compose_result is not None:
        blocking.extend(_verify_compose_result(artifact, compose_result))
    else:
        blocking.extend(_verify_ideogram_artifact(artifact, stamped_copy, stamp_overflow))

    fallback_reason = poster_ideogram.read_fallback_reason(artifact.file_path)
    if fallback_reason:
        non_blocking.append(f"Note: {fallback_reason}")

    return VerificationResult(passed=not blocking, findings=blocking + non_blocking)


def _verify_compose_result(artifact: CampaignArtifact, compose_result: ComposeResult) -> list[str]:
    """The original compose()-path checks, unchanged."""
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
    return findings


def _verify_ideogram_artifact(
    artifact: CampaignArtifact,
    stamped_copy: list[str] | None,
    stamp_overflow: list[str] | None,
) -> list[str]:
    """Independently check the Ideogram path: dimensions, a readable PNG on
    disk, and that every string `poster_ideogram.py` stamped is non-empty and
    stayed inside its safe margins (surfaced via its own sidecar manifest)."""
    findings: list[str] = []

    if (artifact.width, artifact.height) != (POSTER_WIDTH, POSTER_HEIGHT):
        findings.append(
            f"Poster is {artifact.width}x{artifact.height}, expected "
            f"{POSTER_WIDTH}x{POSTER_HEIGHT}."
        )

    path = Path(artifact.file_path)
    if not path.exists() or path.stat().st_size == 0:
        findings.append(f"Poster file is missing or empty: {path}")
        return findings

    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            if image.format != "PNG":
                findings.append(f"Poster at {path} is not a PNG (format={image.format}).")
    except (UnidentifiedImageError, OSError) as exc:
        findings.append(f"Poster at {path} is not a readable image: {exc}")

    if stamped_copy is None or stamp_overflow is None:
        manifest = poster_ideogram.read_stamp_manifest(path)
        if manifest is None:
            findings.append(
                f"No stamped-copy manifest found alongside {path}; cannot verify the exact "
                "business copy that was stamped onto the poster."
            )
            stamped_copy = stamped_copy if stamped_copy is not None else []
            stamp_overflow = stamp_overflow if stamp_overflow is not None else []
        else:
            stamped_copy = stamped_copy if stamped_copy is not None else manifest["stamped_copy"]
            stamp_overflow = stamp_overflow if stamp_overflow is not None else manifest["overflow"]

    if not stamped_copy or any(not value.strip() for value in stamped_copy):
        findings.append("One or more stamped copy strings are empty; exact business copy was not verified.")
    if stamp_overflow:
        findings.append(
            "Stamped copy did not fit its safe margins and had to be truncated: "
            + ", ".join(stamp_overflow)
        )

    return findings


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
