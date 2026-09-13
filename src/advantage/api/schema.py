"""Machine-readable JSON Schema bundle for UI/client generation."""

from __future__ import annotations

from typing import TypeAlias

from pydantic import BaseModel

from .contracts import (
    API_CONTRACT_VERSION,
    ApiError,
    CampaignDraftRequest,
    CampaignJobAccepted,
    CampaignReviewView,
    DriveIntakeRequest,
    DriveIntakeView,
    PausedCampaignCreateRequest,
    PausedCampaignView,
)


ContractModel: TypeAlias = type[BaseModel]

PUBLIC_CONTRACTS: tuple[ContractModel, ...] = (
    DriveIntakeRequest,
    DriveIntakeView,
    CampaignDraftRequest,
    CampaignJobAccepted,
    CampaignReviewView,
    PausedCampaignCreateRequest,
    PausedCampaignView,
    ApiError,
)


def export_contract_schema() -> dict[str, object]:
    """Return one deterministic bundle keyed by public model name."""

    return {
        "contract_version": API_CONTRACT_VERSION,
        "models": {
            model.__name__: model.model_json_schema(mode="serialization")
            for model in PUBLIC_CONTRACTS
        },
    }
