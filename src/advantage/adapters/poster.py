"""Turn a CampaignRequest into a poster via the existing, free `compose` pipeline.

This module is glue, not a new pipeline: it maps `CampaignRequest` (small,
rough -- a `brief_text` blob plus a handful of optional facts) into the two
objects `PosterComposer.compose()` already knows how to render --
`PosterContent` and `BrandProfile` (see `src/cricket_posts/models.py`) -- then
wraps the result. All rendering, layout-fitting, plate selection, and copy
verification is the pipeline's own existing work (`src/cricket_posts/pipeline.py`,
`archetypes.py`, `plates.py`, `blocks.py`); nothing here re-implements or
tunes it.

Deliberately the FREE path, not the paid one: `compose()` calls no API at all
(three offline layers -- background plate, transparent cut-outs, exact copy --
composited and screenshotted through a local, already-installed Chrome/Edge
via Playwright). The paid Ideogram/GPT hybrid studio pipeline behind the web
app's `/api/projects/{id}/generate` route is a different, separate code path
(`studio.py`) and is not touched or imported here.

`produce_poster()` below now *routes*: when `IDEOGRAM_API_KEY` is configured,
it prefers `poster_ideogram.produce_ideogram_poster()` (text-free Ideogram
artwork + deterministically stamped exact copy -- see that module's
docstring). Everything in this file remains the fallback: no key, or any
failure from the Ideogram path, falls back here so a demo never hard-crashes
for lack of a paid API key. See `produce_poster()`'s own docstring for the
exact rule.

Field mapping (CampaignRequest -> PosterContent / BrandProfile)
-----------------------------------------------------------------
Nothing is invented: every value placed below is copied verbatim (only
length-clipped to the target field's own `max_length`, since `PosterContent`'s
fields carry caps `CampaignRequest`'s free-text fields do not). A field that is
`None`/empty on the request is simply omitted -- `blocks.py`'s own `add()`
already drops a block with no values, so this needs no extra "is it worth
showing" logic here.

* ``brand.name``            <- ``business_name`` (also feeds the LOCKUP block
  as ``content.organization``, so the business is named once, consistently).
* ``brand.logo_path``       <- ``logo_asset.local_ref`` if present, else unset.
* ``brand.registration_url``<- ``destination_url`` (tags the QR/caption scan
  URL `compose()` returns as `ComposeResult.scan_url`; unrelated to whether the
  same link is printed as readable copy -- see cta_lines below).
* ``brand.tagline`` / ``location`` / ``contact_lines`` / ``palette`` are left
  at their defaults: `CampaignRequest` has no brand-level tagline, address, or
  colour fields to source them from honestly (same reasoning `adapters/reel.py`
  gives for reusing a fixed palette rather than inventing one).
* ``content.organization``  <- ``business_name`` (see above).
* ``content.title``         <- ``offer_text`` if supplied (it is the one field
  that is actually a promotional hook, i.e. headline material), else
  ``business_name`` (always present, so `title` -- which is required -- is
  never empty or fabricated).
* ``content.subtitle``      <- ``audience`` if supplied, else "".
* ``content.sections``      <- one `ContentSection(text=brief_text)`. This is
  the one field guaranteed non-empty on every request, so it always becomes
  the poster's body paragraph. `brief_text` is deliberately NOT also used as a
  tagline/eyebrow/headline source: it is prose, not a slogan, and repeating it
  in multiple roles would not add information.
* ``content.contacts``      <- one `Contact(display_text=contact_phone)` if
  supplied, else []. Feeds an INFO_BAR block (a phone-labelled contact strip).
* ``content.cta_lines``     <- ``[destination_url]`` if supplied, else [].
  Feeds a second INFO_BAR block -- this is what actually prints the link as
  readable copy (`brand.registration_url` above only feeds the *tagged* scan
  URL, which is not shown on the artboard unless a QR is drawn).
* ``content.eyebrow`` / ``tagline`` / ``price_line`` / ``detail_lines`` /
  ``location_lines`` / ``schedule`` are left at their empty defaults:
  `CampaignRequest` has no address, schedule, or itemised-facts field, and
  `budget_usd` is ad spend, not a customer-facing price -- printing it as
  `price_line` would be actively misleading, not just an omission.
* ``content_type``          <- always `InformationContent`, the one
  `PosterContent` variant with no extra required fields beyond the shared
  base. `CampaignRequest` carries no vertical/category signal (tournament
  categories, camp coach bio, lane pricing, ...) to justify any of the other
  four variants, and guessing one would risk validation on fields this
  request has no data for.

Not used at all: ``photo_assets`` and ``footage_assets`` (`compose()` takes
subject cut-outs from its own curated bank via `subject_files`, or a plate
with a scene already baked in -- there is no parameter to composite an
arbitrary uploaded photo; wiring that in would mean writing new compositing
logic, which is explicitly out of scope today). ``budget_usd`` and
``campaign_days`` describe the ad buy, not the poster's copy, so neither is
read here at all (Meta ad prep is `adapters/meta_ads.py`'s job).

Archetype and plate
--------------------
Archetype is pinned to `split_field` (`ArchetypeId.SPLIT_FIELD`): per
README.md's "Archetypes" table it paints its own colour field via a
`clip-path` and "takes its region outright instead of measuring for one",
which is why it is the one archetype that "works on every plate in the
bank" with no plate-specific measurement or guessing required -- the safe
default for a generic small-business request with no art-direction input.

A plate is still required (`compose()` always composites onto some background
image), so this pins one explicitly:
``assets/plates/austin-geometric-left-01.png``. Reasoning: `split_field` owns
its own backdrop and paints over whatever is beneath it, so which plate is
picked has no bearing on legibility -- but `plate_file` is still a required
positional choice, and picking one explicitly (vs. leaving it to
`select_plate`'s scoring) keeps the poster deterministic. This plate carries
no `content_types` restriction in `assets/plates/manifest.json` (so it never
conflicts with `InformationContent`), has no baked-in subjects, and its
`intents` list includes `BOLD_ATTENTION`, `compose()`'s own default style
intent.

`intent`/`color_mode` are left at `compose()`'s own defaults
(`StyleIntent.BOLD_ATTENTION` / `ColorMode.DARK`) for the same reason the
palette is left at its default: `CampaignRequest` carries no per-request style
signal to honestly vary them by. `include_qr=False` -- a QR competes for space
against copy on a poster the archetype is already stretching to fill, and the
tagged link this pipeline already computes (`ComposeResult.scan_url`) belongs
in a caption instead (see README.md's "Composing posters" section).

One treatment is NOT left at its default: `info_variant="stack"` (default is
`"bar"`). `canvas.css`'s bottom contact bar is built to overlap a banner below
it (`--bar-drop`'s own comment: "the banner always makes room for exactly the
overlap"). `CampaignRequest` has no field this mapping treats as a banner
strapline (`content.tagline` is left empty -- see above), so with the default
`"bar"` variant and no banner the bar's negative margin runs it past the
canvas's own bottom edge. That is a real clip on that one element, but
`pipeline.py`'s clipped-copy audit walks every leaf's ancestor chain up to
`<body>`, and `.canvas` -- common to every leaf on the poster -- is
`overflow:hidden`; once *any* descendant makes `.canvas.scrollHeight` exceed
its own height, the ancestor check fires for every leaf under it, not just the
one that overflowed. One overflowing footer string was observed to make
`ComposeResult.clipped_copy` list every value on the poster, verbatim copy and
all. `"stack"` places the same contact details inside the fitted copy column
instead of the absolutely-positioned bottom bar, which sidesteps the overlap
entirely -- confirmed by re-composing `fixtures/information.json` (a fixture
with no tagline) through the CLI: `--info bar` reports all 12 values CLIPPED,
`--info stack` reports none. This is a pre-existing `compose()`/template
behavior, not something patched here -- nothing in `pipeline.py`,
`blocks.py`, or `templates/studio/` was touched to reach this default; a
supported, already-shipping treatment was simply chosen instead of the one
that assumes a banner always follows it.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from PIL import Image

from cricket_posts.archetypes import ArchetypeId
from cricket_posts.models import (
    BrandProfile,
    Contact,
    ContentSection,
    InformationContent,
    PosterContent,
)
from cricket_posts.pipeline import ComposeResult, PosterComposer

from ..domain.models import (
    CampaignArtifact,
    CampaignRequest,
    CreativeDecision,
    CreativeFormat,
    CreativePlan,
)
from . import poster_ideogram

logger = logging.getLogger(__name__)

#: Any plate works for `split_field` (it paints its own field over whatever is
#: beneath), so this is a fixed, deterministic default rather than a free
#: choice per request. See the module docstring for why this specific file.
DEFAULT_PLATE_FILE = "austin-geometric-left-01.png"


class PosterAdapterError(RuntimeError):
    """Raised when a poster cannot be built or composed from a CampaignRequest."""


def _clip(value: str, limit: int) -> str:
    """Trim to `limit` chars without ever inventing new content."""
    value = value.strip()
    return value if len(value) <= limit else value[:limit].rstrip()


def build_brand_profile(request: CampaignRequest) -> BrandProfile:
    """Pure mapping: CampaignRequest -> BrandProfile. See module docstring."""
    logo_path = None
    if request.logo_asset and request.logo_asset.local_ref:
        logo_path = request.logo_asset.local_ref

    return BrandProfile(
        name=_clip(request.business_name, 80),
        logo_path=logo_path,
        registration_url=request.destination_url,
    )


def build_poster_content(request: CampaignRequest) -> PosterContent:
    """Pure mapping: CampaignRequest -> PosterContent. See module docstring."""
    contacts: list[Contact] = []
    if request.contact_phone and request.contact_phone.strip():
        contacts.append(Contact(display_text=_clip(request.contact_phone, 220)))

    cta_lines: list[str] = []
    if request.destination_url and request.destination_url.strip():
        cta_lines.append(_clip(request.destination_url, 200))

    if request.offer_text and request.offer_text.strip():
        title = _clip(request.offer_text, 180)
    else:
        title = _clip(request.business_name, 180)

    subtitle = ""
    if request.audience and request.audience.strip():
        subtitle = _clip(request.audience, 240)

    return InformationContent(
        organization=_clip(request.business_name, 100),
        title=title,
        subtitle=subtitle,
        contacts=contacts,
        cta_lines=cta_lines,
        sections=[ContentSection(text=_clip(request.brief_text, 700))],
    )


def _compose_via_pipeline(request: CampaignRequest, *, workdir: Path) -> tuple[CampaignArtifact, ComposeResult]:
    """Compose `request` into a poster PNG under `workdir` via the free pipeline.

    Returns the wrapped `CampaignArtifact` alongside the raw `ComposeResult` --
    the caller (a `verification.py` reading `missing_copy`/`clipped_copy`/
    `dead`/`footer_contrast`/`fit`) gets that untouched; no pass/fail judgment
    is made here.

    Factored out of `produce_poster()` unchanged so both the default call and
    the Ideogram-fallback call share one implementation; the format check and
    workdir setup now live in `produce_poster()`, which always calls this.
    """
    content = build_poster_content(request)
    brand = build_brand_profile(request)
    logo_path = (
        Path(request.logo_asset.local_ref)
        if request.logo_asset and request.logo_asset.local_ref
        else None
    )

    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    destination = workdir / "poster.png"

    composer = PosterComposer()
    try:
        try:
            compose_result = composer.compose(
                content,
                brand,
                destination,
                archetype_id=ArchetypeId.SPLIT_FIELD,
                plate_file=DEFAULT_PLATE_FILE,
                logo_path=logo_path,
                info_variant="stack",
                include_qr=False,
            )
        except Exception as exc:
            raise PosterAdapterError(
                f"compose() failed while producing a poster for "
                f"{request.business_name!r}: {exc}"
            ) from exc
    finally:
        composer.renderer.close()

    if not destination.exists() or destination.stat().st_size == 0:
        raise PosterAdapterError(
            f"compose() reported success but {destination} is missing or empty."
        )

    try:
        with Image.open(destination) as image:
            width, height = image.size
    except Exception as exc:  # a corrupt/truncated PNG must not pass silently
        raise PosterAdapterError(
            f"Composed poster at {destination} is not a readable image: {exc}"
        ) from exc

    artifact = CampaignArtifact(
        format=CreativeFormat.POSTER,
        file_path=str(destination),
        width=width,
        height=height,
    )
    return artifact, compose_result


def produce_poster(
    request: CampaignRequest,
    *,
    workdir: Path,
    allow_ideogram: bool = True,
) -> tuple[CampaignArtifact, ComposeResult | None]:
    """Produce a poster for `request`, preferring Ideogram, falling back to compose().

    Routing rule (reliability over purity -- a demo must never hard-crash for
    lack of a paid API key):

    1. If `allow_ideogram` is True (the default) and `IDEOGRAM_API_KEY` is set
       in the environment, try `poster_ideogram.produce_ideogram_poster()`.
       On success this returns `(artifact, None)` -- there is no `ComposeResult`
       on this path; `verification.py` reads the Ideogram path's own sidecar
       manifest instead (see `poster_ideogram.py`'s module docstring).
    2. Otherwise -- no key configured, `allow_ideogram=False`, or the Ideogram
       call raised anything at all -- fall back to the existing free
       `compose()` pipeline via `_compose_via_pipeline()`, returning
       `(artifact, compose_result)` exactly as before. The fallback reason is
       logged and recorded in a sidecar file next to the rendered poster so
       `verify_poster()` can surface it as a non-blocking finding.

    `allow_ideogram=False` is a deliberate caller opt-out (e.g. tests), not a
    failure, so it is not recorded as a fallback.
    """
    if request.format != CreativeFormat.POSTER:
        raise PosterAdapterError(
            "produce_poster requires CampaignRequest.format == CreativeFormat.POSTER, "
            f"got {request.format.value!r}."
        )

    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    fallback_reason: str | None = None
    if allow_ideogram:
        if not os.getenv("IDEOGRAM_API_KEY"):
            fallback_reason = (
                "IDEOGRAM_API_KEY is not set; used the offline compose() pipeline instead."
            )
        else:
            try:
                stamped = poster_ideogram.produce_ideogram_poster(request, workdir=workdir)
            except Exception as exc:  # a demo must never hard-crash for this
                fallback_reason = (
                    f"Ideogram poster generation failed ({exc}); fell back to the offline "
                    "compose() pipeline."
                )
            else:
                return stamped.artifact, None

    if fallback_reason:
        logger.warning("poster: %s", fallback_reason)

    artifact, compose_result = _compose_via_pipeline(request, workdir=workdir)

    if fallback_reason:
        poster_ideogram.write_fallback_marker(artifact.file_path, fallback_reason)

    return artifact, compose_result


def _describe_compose_plan(request: CampaignRequest) -> CreativePlan:
    """Pure explanation of the free compose() path's decisions (no API calls)."""
    decisions = [
        CreativeDecision(
            choice="Offline compose() pipeline (split_field archetype)",
            reason=(
                "IDEOGRAM_API_KEY is not configured, so produce_poster() will use the free, "
                "local compose() renderer instead of Ideogram."
            ),
        ),
        CreativeDecision(
            choice="Destination URL printed as readable copy, no QR",
            reason="compose()'s split_field/stack layout has no room budgeted for a QR (see this module's own docstring).",
        ),
    ]
    if request.logo_asset and request.logo_asset.local_ref:
        decisions.append(
            CreativeDecision(choice="Include the supplied logo", reason="request.logo_asset.local_ref is present.")
        )
    else:
        decisions.append(CreativeDecision(choice="No logo", reason="No logo asset was supplied on the request."))
    return CreativePlan(format=CreativeFormat.POSTER, feel="offline_compose", decisions=decisions)


def describe_plan(request: CampaignRequest) -> CreativePlan:
    """Explain whichever poster path `produce_poster()` would actually use.

    Pure and API-call-free: it only checks whether `IDEOGRAM_API_KEY` is
    configured, the same signal `produce_poster()` itself checks first.
    """
    if os.getenv("IDEOGRAM_API_KEY"):
        return poster_ideogram.describe_plan(request)
    return _describe_compose_plan(request)
