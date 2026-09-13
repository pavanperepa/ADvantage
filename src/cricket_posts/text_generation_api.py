"""FastAPI routes for text creative generation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from .campaign_api import _RUNS
from .text_generation import (
    PushGenerationRequest,
    PushNotificationGenerator,
    PushVariants,
)

router = APIRouter(prefix="/api/text-generation", tags=["text-generation"])


class CampaignContextOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    product_name: str
    product_description: str
    offer: str
    target_audience: str


def _campaign_contexts() -> list[CampaignContextOut]:
    contexts: list[CampaignContextOut] = []
    for run_id, result in reversed(list(_RUNS.items())):
        request = result.request
        contexts.append(
            CampaignContextOut(
                id=run_id,
                label=f"{request.business_name} · {request.format.value}",
                product_name=request.business_name,
                product_description=request.brief_text,
                offer=request.offer_text or "",
                target_audience=request.audience or "",
            )
        )
    return contexts


def _with_campaign_context(payload: PushGenerationRequest) -> PushGenerationRequest:
    if not payload.campaign_id:
        return payload
    result = _RUNS.get(payload.campaign_id)
    if result is None:
        raise HTTPException(
            404,
            "That campaign is no longer available. Campaign runs do not survive a server restart.",
        )
    request = result.request
    values = payload.model_dump(mode="python")
    values["product_name"] = payload.product_name.strip() or request.business_name
    values["product_description"] = payload.product_description.strip() or request.brief_text
    values["offer"] = payload.offer.strip() or request.offer_text or ""
    values["target_audience"] = payload.target_audience.strip() or request.audience or ""
    return PushGenerationRequest.model_validate(values)


def get_push_generator() -> PushNotificationGenerator:
    return PushNotificationGenerator()


@router.get("/campaigns", response_model=list[CampaignContextOut])
def list_campaign_contexts() -> list[CampaignContextOut]:
    return _campaign_contexts()


@router.post("/push", response_model=PushVariants)
def generate_push_notifications(payload: PushGenerationRequest) -> PushVariants:
    resolved = _with_campaign_context(payload)
    try:
        return get_push_generator().generate(resolved)
    except RuntimeError as exc:
        message = str(exc)
        if "OPENAI_API_KEY" in message:
            raise HTTPException(503, message) from exc
        raise HTTPException(502, "Notification generation failed. Please try again.") from exc
    except Exception as exc:
        raise HTTPException(502, "Notification generation failed. Please try again.") from exc
