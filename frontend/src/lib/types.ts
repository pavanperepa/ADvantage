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

export type InterviewQuestionKind = "text" | "choice" | "multi_text";

export interface QuestionChoice {
  value: string;
  label: string;
}

export interface InterviewQuestion {
  id: string;
  prompt: string;
  kind: InterviewQuestionKind;
  choices: QuestionChoice[] | null;
  /** One sentence on why we're asking -- shown as helper text. */
  why: string;
  required: boolean;
}

/** Answers accumulate as `{ [question id]: string | string[] }`. */
export type InterviewAnswers = Record<string, string | string[]>;

export interface InterviewResponse {
  /** At most 4 at a time. Empty once `ready` is `true`. */
  questions: InterviewQuestion[];
  answers: InterviewAnswers;
  ready: boolean;
}

export interface CreativeDecision {
  choice: string;
  reason: string;
}

export interface CreativePlan {
  format: CreativeFormat;
  feel: string;
  decisions: CreativeDecision[];
}

export type RationaleSource = "meta_insights" | "meta_defaults" | "request" | "creative_plan";

export interface RationaleFactor {
  claim: string;
  evidence: string;
  source: RationaleSource;
}

export interface CampaignRationale {
  summary: string;
  factors: RationaleFactor[];
  meta_account_grounded: boolean;
}

export interface CampaignRun {
  id: string;
  artifact: CampaignArtifact;
  verification: VerificationResult;
  /** `null` whenever `budget_usd` wasn't supplied on creation. */
  meta_preview: MetaAdPreview | null;
  /** `null` when the creative plan wasn't recorded for this run. */
  plan: CreativePlan | null;
  /** `null` when no rationale was recorded for this run. */
  rationale: CampaignRationale | null;
}

export interface CreatePausedResult {
  dry_run: boolean;
  campaign_id: string | null;
  ad_set_id: string | null;
  ad_id: string | null;
  status: string;
}
