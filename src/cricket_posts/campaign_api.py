"""JSON API for the simplified campaign flow, for the Next.js frontend.

Separate from the legacy poster-studio routes in web.py (paste-text -> poster
only). This is intentionally a thin HTTP wrapper around
``advantage``'s already-tested ``run_campaign()`` -- no new
business logic lives here.

No persistence layer exists yet (P1-02 is deliberately deferred), so runs
live in an in-memory dict for the life of the server process. `run_campaign`
executes synchronously in the request handler (a poster takes ~2-3s, a reel
roughly a minute) -- there is no background job queue, matching that same
scope cut.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from advantage import (
    PALETTE_SWATCHES,
    ActivityStep,
    BrandPalette,
    CampaignRationale,
    CampaignRequest,
    CampaignResult,
    CreativeFormat,
    CreativeCritique,
    CreativePlan,
    MetaAdResult,
    PosterStyle,
    ReelFeel,
    OrchestratorError,
    PosterAdapterError,
    ReelAdapterError,
    create_paused_campaign,
    run_campaign,
)
from advantage.application.interview import (
    AnswerValidationError,
    apply_answers,
    plan_interview,
)
from advantage.integrations.google_drive import (
    AssetKind,
    DriveAuthenticationError,
    DriveFolderNotSharedError,
    DriveIntakeConfig,
    DriveIntakeError,
    GoogleDriveClient,
    IntakeAsset,
    IntakeStatus,
    ingest_drive_folder,
    list_campaign_folders,
)
from advantage.integrations.google_oauth import GoogleOAuthError, resolve_google_drive_access_token
from .renderer import PROJECT_ROOT

# `cli.run_serve` never loads .env (only the one-shot CLI commands and the Meta
# adapters do), so under `uvicorn` the whole process would otherwise start with
# no IDEOGRAM_API_KEY / OPENAI_API_KEY -- silently downgrading every poster to
# the free compose fallback and every interview to un-reworded questions.
# `override=False` keeps a real environment variable authoritative over the file.
load_dotenv(PROJECT_ROOT / ".env", override=False)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

RUNS_DIR = PROJECT_ROOT / "output" / "campaign_runs"
UPLOADS_DIR = PROJECT_ROOT / "output" / "campaign_uploads"

# In-memory only -- see module docstring. Keyed by run id.
_RUNS: dict[str, CampaignResult] = {}

_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}


class ArtifactOut(BaseModel):
    format: CreativeFormat
    width: int
    height: int
    duration_seconds: float | None
    url: str


class VerificationOut(BaseModel):
    passed: bool
    findings: list[str]


class MetaPreviewOut(BaseModel):
    campaign_name: str
    objective: str
    daily_budget_usd: float
    days: int
    primary_text: str
    headline: str
    call_to_action: str
    destination_url: str | None
    creative_format: CreativeFormat


class CampaignRunOut(BaseModel):
    id: str
    artifact: ArtifactOut
    verification: VerificationOut
    meta_preview: MetaPreviewOut | None
    # Both are None on runs where the planner/rationale step produced nothing
    # (e.g. no Meta preview to explain); the UI renders them only when present.
    plan: CreativePlan | None = None
    rationale: CampaignRationale | None = None
    critique: CreativeCritique | None = None
    activity: list[ActivityStep] = []


class QuestionChoiceOut(BaseModel):
    """One selectable answer. The interview module speaks bare enum values;
    the UI needs a display label alongside, so the label is derived here
    rather than duplicating a label table in the domain layer."""

    value: str
    label: str


class QuestionOut(BaseModel):
    id: str
    prompt: str
    kind: str
    choices: list[QuestionChoiceOut] | None
    why: str
    required: bool
    # An answer the agent drafted from the brief, for the owner to confirm or
    # edit. None whenever the agent had nothing honest to propose.
    suggestion: str | list[str] | None = None
    suggestion_note: str | None = None


class AgentInferenceOut(BaseModel):
    field: str
    label: str
    value: str
    note: str


class InterviewIn(BaseModel):
    business_name: str
    brief_text: str
    format: CreativeFormat
    answers: dict[str, Any] = {}


class InterviewOut(BaseModel):
    questions: list[QuestionOut]
    answers: dict[str, Any]
    ready: bool
    # What the agent said, what it worked out from the brief by itself, and
    # where this round sits in the conversation.
    agent_note: str = ""
    understood: list[AgentInferenceOut] = []
    round: int = 1
    total_rounds: int = 1


class CreatePausedOut(BaseModel):
    dry_run: bool
    campaign_id: str | None
    ad_set_id: str | None
    ad_id: str | None
    status: str


def _to_out(run_id: str, result: CampaignResult) -> CampaignRunOut:
    artifact = result.artifact
    return CampaignRunOut(
        id=run_id,
        artifact=ArtifactOut(
            format=artifact.format,
            width=artifact.width,
            height=artifact.height,
            duration_seconds=artifact.duration_seconds,
            url=f"/api/campaigns/{run_id}/artifact",
        ),
        verification=VerificationOut(
            passed=result.verification.passed, findings=result.verification.findings
        ),
        meta_preview=(
            MetaPreviewOut(**result.meta_preview.model_dump()) if result.meta_preview else None
        ),
        plan=result.plan,
        rationale=result.rationale,
        critique=result.critique,
        activity=result.activity,
    )


def _humanize(value: str) -> str:
    """`high_energy` -> `High energy`. Display only; `value` stays canonical."""
    return value.replace("_", " ").capitalize()


@router.post("/interview", response_model=InterviewOut)
def interview(body: InterviewIn) -> InterviewOut:
    """Ask the owner the next small batch of questions for their format.

    Stateless: the client posts back every answer collected so far, and gets
    the next batch (or `ready`) in return. Nothing is generated or written
    here -- this is the intake conversation only.

    The draft below is a throwaway `CampaignRequest` built purely so
    `next_questions`/`apply_answers` can see which fields are still missing;
    it is never rendered or published. `brief_text` needs a non-empty
    placeholder because the model requires one, and an owner may legitimately
    reach this endpoint before typing a brief.
    """
    try:
        draft = CampaignRequest(
            business_name=body.business_name or "Untitled business",
            brief_text=body.brief_text or "(not provided yet)",
            format=body.format,
        )
    except Exception as exc:
        raise HTTPException(422, str(exc)) from exc

    answers = dict(body.answers)
    if answers:
        try:
            merged = apply_answers(draft, answers)
        except AnswerValidationError as exc:
            raise HTTPException(422, str(exc)) from exc
        try:
            draft = CampaignRequest.model_validate(merged)
        except Exception as exc:
            raise HTTPException(422, str(exc)) from exc

    # `round` is derived from how many answers the client has already sent
    # rather than tracked server-side, keeping this endpoint stateless.
    round_index = 2 if answers else 1

    # The agent reads the brief, fills in what it can, and drafts an answer for
    # what it still has to ask. It degrades to the plain deterministic
    # checklist on a missing key, an API failure, or any response it cannot
    # validate -- so intake never depends on the LLM being reachable.
    agent_plan = plan_interview(
        draft,
        format=body.format,
        brief_text=body.brief_text or "",
        round_index=round_index,
    )

    # Anything the agent worked out for itself is applied on the owner's
    # behalf and echoed back in `answers`, so the client posts it forward and
    # the field is never asked about again.
    if agent_plan.inferred_answers:
        candidate = {**answers, **agent_plan.inferred_answers}
        try:
            apply_answers(draft, candidate)
        except AnswerValidationError:
            pass  # already validated per-field in _merge_plan; keep prior answers
        else:
            answers = candidate

    return InterviewOut(
        questions=[
            QuestionOut(
                id=question.id,
                prompt=question.prompt,
                kind=question.kind,
                choices=(
                    [QuestionChoiceOut(value=c, label=_humanize(c)) for c in question.choices]
                    if question.choices
                    else None
                ),
                why=question.why,
                required=question.required,
                suggestion=question.suggestion,
                suggestion_note=question.suggestion_note,
            )
            for question in agent_plan.questions
        ],
        answers=answers,
        ready=not agent_plan.questions,
        agent_note=agent_plan.agent_note,
        understood=[
            AgentInferenceOut(field=i.field, label=i.label, value=i.value, note=i.note)
            for i in agent_plan.understood
        ],
        round=agent_plan.round,
        total_rounds=agent_plan.total_rounds,
    )


def _save_upload(upload: UploadFile, destination_dir: Path) -> tuple[Path, str]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    # Sync read (upload.file is a plain SpooledTemporaryFile), matching the
    # existing /brands route's convention -- not `await upload.read()`. This
    # endpoint is a sync `def`, not `async def`: PosterComposer uses
    # Playwright's *sync* API underneath, which cannot run on the asyncio
    # event loop an `async def` handler executes on. FastAPI runs a sync
    # `def` route in a worker thread instead, which is what actually avoids
    # that conflict -- keeping every read synchronous here is what keeps the
    # whole request able to stay a plain `def`.
    data = upload.file.read()
    digest = hashlib.sha256(data).hexdigest()[:16]
    suffix = Path(upload.filename or "").suffix or ""
    target = destination_dir / f"{digest}{suffix}"
    target.write_bytes(data)
    return target, digest


def _asset_from_upload(
    upload: UploadFile, destination_dir: Path, *, kind: AssetKind
) -> IntakeAsset:
    target, digest = _save_upload(upload, destination_dir)
    return IntakeAsset(
        source_id=upload.filename or target.name,
        source_name=upload.filename or target.name,
        source_ref=digest,
        kind=kind,
        mime_type=upload.content_type or "application/octet-stream",
        local_ref=str(target),
        status=IntakeStatus.IMPORTED,
    )


@router.post("", response_model=CampaignRunOut, status_code=201)
def create_campaign(
    business_name: str = Form(...),
    brief_text: str = Form(...),
    format: CreativeFormat = Form(...),
    contact_phone: str | None = Form(None),
    destination_url: str | None = Form(None),
    offer_text: str | None = Form(None),
    audience: str | None = Form(None),
    budget_usd: float | None = Form(None),
    campaign_days: int = Form(4),
    # Creative direction collected by POST /interview. All optional: a caller
    # that skips the interview entirely still gets a working campaign.
    reel_feel: str | None = Form(None),
    poster_style: str | None = Form(None),
    art_direction_notes: str | None = Form(None),
    proof_point: str | None = Form(None),
    palette: str | None = Form(None),
    refinement_notes: str | None = Form(None),
    key_benefits: list[str] | None = Form(None),
    logo: UploadFile | None = None,
    footage: list[UploadFile] | None = None,
    # Alternative to `logo`/`footage`: an owner picked a folder from
    # GET /drive/folders instead of uploading files directly. When set, it
    # takes over asset selection entirely and any uploaded files are ignored.
    drive_folder_id: str | None = Form(None),
) -> CampaignRunOut:
    run_id = uuid.uuid4().hex[:12]
    workdir = RUNS_DIR / run_id
    upload_dir = UPLOADS_DIR / run_id

    logo_asset: IntakeAsset | None = None
    footage_assets: list[IntakeAsset] = []

    if drive_folder_id:
        client = _drive_client()
        try:
            receipt = ingest_drive_folder(
                client, drive_folder_id, upload_dir / "drive", config=DriveIntakeConfig()
            )
        except DriveAuthenticationError as exc:
            raise HTTPException(503, str(exc) + _REAUTHORIZE_HINT) from exc
        except DriveIntakeError as exc:
            raise HTTPException(422, str(exc)) from exc
        imported = receipt.imported
        footage_assets = [asset for asset in imported if asset.kind == AssetKind.VIDEO]
        image_assets = [
            asset for asset in imported if asset.kind in (AssetKind.LOGO, AssetKind.PHOTO)
        ]
        logo_asset = image_assets[0] if image_assets else None
    else:
        if logo is not None and logo.filename:
            if logo.content_type not in _IMAGE_TYPES:
                raise HTTPException(
                    422, f"Logo must be PNG, JPEG, or WebP; got {logo.content_type!r}."
                )
            logo_asset = _asset_from_upload(logo, upload_dir, kind=AssetKind.LOGO)

        for clip in footage or []:
            if not clip.filename:
                continue
            if clip.content_type not in _VIDEO_TYPES:
                raise HTTPException(422, f"Footage must be MP4/MOV/WebM; got {clip.content_type!r}.")
            footage_assets.append(_asset_from_upload(clip, upload_dir, kind=AssetKind.VIDEO))

    try:
        request = CampaignRequest(
            business_name=business_name,
            brief_text=brief_text,
            format=format,
            contact_phone=contact_phone or None,
            destination_url=destination_url or None,
            offer_text=offer_text or None,
            audience=audience or None,
            budget_usd=budget_usd,
            campaign_days=campaign_days,
            reel_feel=reel_feel or None,
            poster_style=poster_style or None,
            art_direction_notes=art_direction_notes or None,
            proof_point=proof_point or None,
            palette=palette or None,
            refinement_notes=refinement_notes or None,
            key_benefits=[b.strip() for b in (key_benefits or []) if b.strip()],
            logo_asset=logo_asset,
            footage_assets=footage_assets,
        )
    except Exception as exc:
        raise HTTPException(422, str(exc)) from exc

    try:
        result = run_campaign(request, workdir=workdir)
    except (OrchestratorError, PosterAdapterError, ReelAdapterError) as exc:
        raise HTTPException(422, str(exc)) from exc

    _RUNS[run_id] = result
    return _to_out(run_id, result)


def _get_run(run_id: str) -> CampaignResult:
    result = _RUNS.get(run_id)
    if result is None:
        raise HTTPException(404, f"No campaign run {run_id!r} (runs don't survive a server restart).")
    return result


class PaletteOut(BaseModel):
    value: str
    label: str
    primary: str
    accent: str
    ink: str


@router.get("/palettes", response_model=list[PaletteOut])
def list_palettes() -> list[PaletteOut]:
    """The colour schemes a creative can be generated in.

    Built from PALETTE_SWATCHES so it can never drift from the enum the
    request model actually validates against.
    """
    return [
        PaletteOut(
            value=palette.value,
            label=swatch.label,
            primary=swatch.primary,
            accent=swatch.accent,
            ink=swatch.ink,
        )
        for palette, swatch in PALETTE_SWATCHES.items()
    ]


# --- Google Drive intake ----------------------------------------------------
#
# Read-only browsing of the owner's "Shared with me" -> "Social Media" folder,
# and an alternative to uploading files directly. The refresh/access token is
# never configured in this repo's committed state -- `_drive_client()` turns
# that (and an expired token) into a clear 503 rather than a 500, pointing at
# the authorize script. Like `/palettes`, these `/drive/...` literal routes
# must stay declared before `GET /{run_id}` or they would be captured as a
# run id lookup.

DRIVE_PARENT_FOLDER_NAME = "Social Media"
DRIVE_IMPORTS_DIR = PROJECT_ROOT / "output" / "campaign_drive_imports"

# `DriveAuthenticationError` (an expired/invalid token, from a live Drive
# call) doesn't itself name the fix, unlike `GoogleOAuthError` (no token
# configured yet at all), whose message already points at the script.
_REAUTHORIZE_HINT = " Run scripts/intake/google_drive_authorize.py to reconnect it."


def _drive_client() -> GoogleDriveClient:
    try:
        token = resolve_google_drive_access_token(os.environ)
    except GoogleOAuthError as exc:
        raise HTTPException(503, str(exc)) from exc
    return GoogleDriveClient(token)


class DriveFolderOut(BaseModel):
    id: str
    name: str


class DriveImportIn(BaseModel):
    folder_id: str


class DriveImportAssetOut(BaseModel):
    source_ref: str
    name: str
    kind: AssetKind
    mime_type: str
    duration_seconds: float | None
    status: IntakeStatus
    reason: str | None


@router.get("/drive/folders", response_model=list[DriveFolderOut])
def list_drive_folders() -> list[DriveFolderOut]:
    """The campaign subfolders under "Shared with me" -> "Social Media"."""
    client = _drive_client()
    try:
        folders = list_campaign_folders(client, parent_name=DRIVE_PARENT_FOLDER_NAME)
    except DriveAuthenticationError as exc:
        raise HTTPException(503, str(exc) + _REAUTHORIZE_HINT) from exc
    except DriveFolderNotSharedError as exc:
        raise HTTPException(404, str(exc)) from exc
    except DriveIntakeError as exc:
        raise HTTPException(502, str(exc)) from exc
    return [
        DriveFolderOut(id=folder.id, name=f"{DRIVE_PARENT_FOLDER_NAME} / {folder.name}")
        for folder in folders
    ]


@router.post("/drive/import", response_model=list[DriveImportAssetOut])
def import_drive_folder(body: DriveImportIn) -> list[DriveImportAssetOut]:
    """Preview a Drive folder's contents by actually ingesting it (read-only).

    Downloads through the same sanitizing `ingest_drive_folder` path used by
    the CLI intake script; nothing here is wired to a campaign run yet.
    """
    client = _drive_client()
    destination = DRIVE_IMPORTS_DIR / uuid.uuid4().hex[:12]
    try:
        receipt = ingest_drive_folder(client, body.folder_id, destination)
    except DriveAuthenticationError as exc:
        raise HTTPException(503, str(exc) + _REAUTHORIZE_HINT) from exc
    except DriveIntakeError as exc:
        raise HTTPException(422, str(exc)) from exc
    return [
        DriveImportAssetOut(
            source_ref=asset.source_ref,
            name=asset.source_name,
            kind=asset.kind,
            mime_type=asset.mime_type,
            duration_seconds=asset.duration_seconds,
            status=asset.status,
            reason=asset.reason,
        )
        for asset in receipt.assets
    ]


class RegenerateIn(BaseModel):
    refinement_notes: str | None = None
    palette: str | None = None
    poster_style: str | None = None
    reel_feel: str | None = None


def _parse_enum(enum_cls, value: str | None, field: str):
    """Validate one optional enum override, listing valid values on failure."""
    if value is None or not str(value).strip():
        return None
    try:
        return enum_cls(str(value).strip())
    except ValueError:
        valid = ", ".join(member.value for member in enum_cls)
        raise HTTPException(422, f"{field} must be one of: {valid} (got {value!r}).") from None


@router.post("/{run_id}/regenerate", response_model=CampaignRunOut, status_code=201)
def regenerate(run_id: str, body: RegenerateIn) -> CampaignRunOut:
    """Re-run an existing request with refinements, as a NEW run.

    The original run and its artifact are left untouched, so an owner can
    regenerate freely without losing the version they already have. Only the
    supplied overrides are applied; everything else (assets, budget, copy
    facts) carries over from the original request.
    """
    previous = _get_run(run_id)

    overrides: dict[str, Any] = {}
    if body.refinement_notes and body.refinement_notes.strip():
        overrides["refinement_notes"] = body.refinement_notes.strip()
    palette = _parse_enum(BrandPalette, body.palette, "palette")
    if palette is not None:
        overrides["palette"] = palette
    poster_style = _parse_enum(PosterStyle, body.poster_style, "poster_style")
    if poster_style is not None:
        overrides["poster_style"] = poster_style
    reel_feel = _parse_enum(ReelFeel, body.reel_feel, "reel_feel")
    if reel_feel is not None:
        overrides["reel_feel"] = reel_feel

    try:
        request = previous.request.model_copy(update=overrides)
    except Exception as exc:
        raise HTTPException(422, str(exc)) from exc

    new_run_id = uuid.uuid4().hex[:12]
    try:
        result = run_campaign(request, workdir=RUNS_DIR / new_run_id)
    except (OrchestratorError, PosterAdapterError, ReelAdapterError) as exc:
        raise HTTPException(422, str(exc)) from exc

    _RUNS[new_run_id] = result
    return _to_out(new_run_id, result)


@router.get("/{run_id}", response_model=CampaignRunOut)
def get_campaign(run_id: str) -> CampaignRunOut:
    return _to_out(run_id, _get_run(run_id))


@router.get("/{run_id}/artifact")
def get_campaign_artifact(run_id: str) -> FileResponse:
    result = _get_run(run_id)
    path = Path(result.artifact.file_path)
    if not path.exists():
        raise HTTPException(404, "Artifact file is no longer on disk.")
    media_type = "image/png" if result.artifact.format == CreativeFormat.POSTER else "video/mp4"
    return FileResponse(path, media_type=media_type)


@router.post("/{run_id}/create-paused-campaign", response_model=CreatePausedOut)
def create_paused(run_id: str) -> CreatePausedOut:
    """Real external action: creates PAUSED Meta objects. Never called automatically."""
    result = _get_run(run_id)
    if result.meta_preview is None:
        raise HTTPException(422, "No Meta preview available for this run (budget_usd was not set).")
    meta_result: MetaAdResult = create_paused_campaign(
        result.request, result.artifact, result.meta_preview, execute=True
    )
    return CreatePausedOut(**meta_result.model_dump())
