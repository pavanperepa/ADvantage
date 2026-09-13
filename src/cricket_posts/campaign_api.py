"""JSON API for the simplified campaign flow, for the Next.js frontend.

Separate from the legacy poster-studio routes in web.py (paste-text -> poster
only). This is intentionally a thin HTTP wrapper around
``cricket_posts.campaign``'s already-tested ``run_campaign()`` -- no new
business logic lives here.

Campaign runs live in an in-memory dict for the life of the server. `run_campaign`
executes synchronously in the request handler (a poster takes ~2-3s, a reel
roughly a minute) -- there is no background job queue, matching that same
scope cut.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .campaign import (
    CampaignRequest,
    CampaignResult,
    CreativeFormat,
    MetaAdResult,
    OrchestratorError,
    PosterAdapterError,
    ReelAdapterError,
    create_paused_campaign,
    run_campaign,
)
from .drive_intake import AssetKind, IntakeAsset, IntakeStatus
from .renderer import PROJECT_ROOT
from .slack_sharing import (
    SlackChannelUnavailableError,
    SlackNotConfiguredError,
    SlackSharingError,
    SlackSharingService,
)

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


class CreatePausedOut(BaseModel):
    dry_run: bool
    campaign_id: str | None
    ad_set_id: str | None
    ad_id: str | None
    status: str


class SlackChannelOut(BaseModel):
    id: str
    name: str


class SlackShareIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel_id: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("channel_id", "message")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

class SlackShareOut(BaseModel):
    status: str
    channel_id: str
    channel_name: str
    file_id: str | None


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


def _slack_service() -> SlackSharingService:
    try:
        return SlackSharingService.from_env()
    except SlackNotConfiguredError as exc:
        raise HTTPException(503, str(exc)) from exc


def _poster_path(run_id: str) -> tuple[CampaignResult, Path]:
    result = _get_run(run_id)
    if result.artifact.format != CreativeFormat.POSTER:
        raise HTTPException(422, "Only generated posters can be shared to Slack.")
    path = Path(result.artifact.file_path)
    if not path.is_file():
        raise HTTPException(404, "The generated poster is no longer on disk.")
    return result, path


@router.get("/{run_id}/slack/channels", response_model=list[SlackChannelOut])
def list_slack_channels(run_id: str) -> list[SlackChannelOut]:
    _poster_path(run_id)
    try:
        channels = _slack_service().list_public_channels()
    except SlackSharingError as exc:
        raise HTTPException(502, str(exc)) from exc
    return [SlackChannelOut(id=channel.id, name=channel.name) for channel in channels]


@router.post("/{run_id}/slack", response_model=SlackShareOut)
def share_campaign_poster_to_slack(run_id: str, payload: SlackShareIn) -> SlackShareOut:
    result, poster_path = _poster_path(run_id)
    try:
        receipt = _slack_service().share_poster(
            channel_id=payload.channel_id,
            message=payload.message,
            poster_path=poster_path,
            title=f"{result.request.business_name} — ADvantage poster",
        )
    except SlackChannelUnavailableError as exc:
        raise HTTPException(422, str(exc)) from exc
    except SlackSharingError as exc:
        raise HTTPException(502, str(exc)) from exc
    return SlackShareOut(
        status="sent",
        channel_id=receipt.channel_id,
        channel_name=receipt.channel_name,
        file_id=receipt.file_id,
    )


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
