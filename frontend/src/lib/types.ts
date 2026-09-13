/**
 * Mirrors the JSON contract served by `cricket_posts.campaign_api` (FastAPI).
 * Keep this in sync with `CampaignRunOut` / `CreatePausedOut` in
 * `src/cricket_posts/campaign_api.py` -- that file is the source of truth,
 * this is just the TypeScript shape of its responses.
 */

export type CreativeFormat = "poster" | "reel";

export interface CampaignArtifact {
  format: CreativeFormat;
  width: number;
  height: number;
  /** Present (seconds) for a reel, `null` for a poster. */
  duration_seconds: number | null;
  /** Relative API path, e.g. `/api/campaigns/{id}/artifact`. */
  url: string;
}

export interface VerificationResult {
  passed: boolean;
  findings: string[];
}

export interface MetaAdPreview {
  campaign_name: string;
  objective: string;
  daily_budget_usd: number;
  days: number;
  primary_text: string;
  headline: string;
  call_to_action: string;
  destination_url: string | null;
  creative_format: CreativeFormat;
}

export interface CampaignRun {
  id: string;
  artifact: CampaignArtifact;
  verification: VerificationResult;
  /** `null` whenever `budget_usd` wasn't supplied on creation. */
  meta_preview: MetaAdPreview | null;
}

export interface CreatePausedResult {
  dry_run: boolean;
  campaign_id: string | null;
  ad_set_id: string | null;
  ad_id: string | null;
  status: string;
}
