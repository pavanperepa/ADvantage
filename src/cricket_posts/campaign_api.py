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
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from advantage import (
    CampaignRationale,
    CampaignRequest,
    CampaignResult,
    CreativeFormat,
    CreativePlan,
    MetaAdResult,
    OrchestratorError,
    PosterAdapterError,
    ReelAdapterError,
    create_paused_campaign,
    run_campaign,
)
from advantage.application.interview import (
    AnswerValidationError,
    apply_answers,
    enrich_questions,
    next_questions,
)
from advantage.integrations.google_drive import AssetKind, IntakeAsset, IntakeStatus
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


class InterviewIn(BaseModel):
    business_name: str
    brief_text: str
    format: CreativeFormat
    answers: dict[str, Any] = {}


class InterviewOut(BaseModel):
    questions: list[QuestionOut]
    answers: dict[str, Any]
    ready: bool


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

    questions = next_questions(draft, format=body.format)
    # Rewording is a garnish: enrich_questions returns the deterministic set
    # unchanged whenever OpenAI is unavailable or answers oddly, so a missing
    # key or a flaky call can never block the intake flow.
    questions = enrich_questions(questions, brief_text=body.brief_text or "")

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
            )
            for question in questions
        ],
        answers=answers,
        ready=not questions,
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
    key_benefits: list[str] | None = Form(None),
    logo: UploadFile | None = None,
    footage: list[UploadFile] | None = None,
) -> CampaignRunOut:
    run_id = uuid.uuid4().hex[:12]
    workdir = RUNS_DIR / run_id
    upload_dir = UPLOADS_DIR / run_id

    logo_asset: IntakeAsset | None = None
    if logo is not None and logo.filename:
        if logo.content_type not in _IMAGE_TYPES:
            raise HTTPException(422, f"Logo must be PNG, JPEG, or WebP; got {logo.content_type!r}.")
        logo_asset = _asset_from_upload(logo, upload_dir, kind=AssetKind.LOGO)

    footage_assets: list[IntakeAsset] = []
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
