"""Single-entry-point package for the simplified poster-or-reel campaign flow.

Import from here (``from cricket_posts.campaign import ...``) rather than
reaching into the submodules directly. For most callers, ``run_campaign()``
is the only function you need -- it dispatches to the right creative
adapter, verifies the result, and previews the Meta ad. The individual
adapters stay exported for anything that needs one step in isolation (a
test, a script, a future retry-just-this-step UI action).
"""

from .meta_adapter import MissingBudgetError, build_meta_preview, create_paused_campaign
from .models import (
    CampaignArtifact,
    CampaignRequest,
    CampaignResult,
    CreativeFormat,
    MetaAdPreview,
    MetaAdResult,
    VerificationResult,
)
from .orchestrator import OrchestratorError, run_campaign
from .poster_adapter import PosterAdapterError, produce_poster
from .reel_adapter import ReelAdapterError, produce_reel
from .verification import verify_poster, verify_reel

__all__ = [
    "CampaignArtifact",
    "CampaignRequest",
    "CampaignResult",
    "CreativeFormat",
    "MetaAdPreview",
    "MetaAdResult",
    "VerificationResult",
    "MissingBudgetError",
    "OrchestratorError",
    "PosterAdapterError",
    "ReelAdapterError",
    "build_meta_preview",
    "create_paused_campaign",
    "produce_poster",
    "produce_reel",
    "run_campaign",
    "verify_poster",
    "verify_reel",
]
