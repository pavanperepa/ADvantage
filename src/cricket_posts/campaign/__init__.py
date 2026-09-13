"""Single-entry-point package for the simplified poster-or-reel campaign flow.

Import from here (``from cricket_posts.campaign import ...``) rather than
reaching into the submodules directly -- this is the one surface the rest of
the app, and the eventual web UI, should depend on.
"""

from .meta_adapter import MissingBudgetError, build_meta_preview, create_paused_campaign
from .models import (
    CampaignArtifact,
    CampaignRequest,
    CreativeFormat,
    MetaAdPreview,
    MetaAdResult,
    VerificationResult,
)
from .reel_adapter import ReelAdapterError, produce_reel

__all__ = [
    "CampaignArtifact",
    "CampaignRequest",
    "CreativeFormat",
    "MetaAdPreview",
    "MetaAdResult",
    "VerificationResult",
    "MissingBudgetError",
    "ReelAdapterError",
    "build_meta_preview",
    "create_paused_campaign",
    "produce_reel",
]
