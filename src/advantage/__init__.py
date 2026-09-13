"""Public application surface for ADvantage campaign production.

Import from here (``from advantage import ...``) rather than
reaching into the submodules directly. For most callers, ``run_campaign()``
is the only function you need -- it dispatches to the right creative
adapter, verifies the result, and previews the Meta ad. The individual
adapters stay exported for anything that needs one step in isolation (a
test, a script, a future retry-just-this-step UI action).
"""

from .adapters.meta_ads import MissingBudgetError, build_meta_preview, create_paused_campaign
from .adapters.poster import PosterAdapterError, produce_poster
from .adapters.reel import ReelAdapterError, produce_reel
from .application.orchestrator import OrchestratorError, run_campaign
from .application.verification import verify_poster, verify_reel
from .domain.models import (
    CampaignArtifact,
    CampaignRationale,
    CampaignRequest,
    CampaignResult,
    CreativeDecision,
    CreativeFormat,
    CreativePlan,
    PosterStyle,
    RationaleFactor,
    ReelFeel,
    MetaAdPreview,
    MetaAdResult,
    VerificationResult,
)

__all__ = [
    "CampaignArtifact",
    "CampaignRationale",
    "CampaignRequest",
    "CampaignResult",
    "CreativeDecision",
    "CreativeFormat",
    "CreativePlan",
    "PosterStyle",
    "RationaleFactor",
    "ReelFeel",
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
