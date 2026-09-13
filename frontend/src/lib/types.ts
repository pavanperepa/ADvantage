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
  /** Relative API path locally, or a direct public Vercel Blob URL when deployed. */
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
  /**
   * A drafted answer the agent worked out from the brief, shaped like the
   * question's `kind` (string for `text`, one of `choices[].value` for
   * `choice`, string array for `multi_text`). `null` when it couldn't guess.
   */
  suggestion: string | string[] | null;
  /** Why the agent proposed `suggestion` -- shown as muted helper text. */
  suggestion_note: string | null;
}

/** Answers accumulate as `{ [question id]: string | string[] }`. */
export type InterviewAnswers = Record<string, string | string[]>;

/** A fact the agent already extracted from the brief and applied itself -- not a question. */
export interface AgentInference {
  field: string;
  label: string;
  value: string;
  note: string;
}

export interface InterviewResponse {
  /** At most 2 at a time. Empty once `ready` is `true`. */
  questions: InterviewQuestion[];
  answers: InterviewAnswers;
  ready: boolean;
  /** One short line from the agent introducing this round, e.g. what it already worked out. */
  agent_note?: string | null;
  /** Facts already picked up from the brief -- read-only, not editable inputs. */
  understood?: AgentInference[];
  /** 1-based round number, paired with `total_rounds` for progress display. */
  round?: number | null;
  total_rounds?: number | null;
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

/** One colour scheme a creative can be generated in (GET /api/campaigns/palettes). */
export interface Palette {
  value: string;
  label: string;
  primary: string;
  accent: string;
  ink: string;
}

/** One step the backend took while producing the creative. */
export interface ActivityStep {
  label: string;
  detail: string;
  status: "done" | "skipped" | "failed";
  /** `null` for a skipped step that never ran. */
  seconds: number | null;
}

/**
 * The system's own review of the finished creative. Separate from
 * `VerificationResult`, which only checks the file is structurally correct --
 * this says whether it is any good, including where it struggled.
 */
export interface CreativeCritique {
  summary: string;
  did: string[];
  why: string[];
  /** The owner's own information that actually reached the artwork. */
  information?: string[];
  /** Internal-only findings; the review panel deliberately does not show these. */
  struggled: string[];
  /** False when no vision model looked at the pixels. */
  model_reviewed: boolean;
}

/** Body for POST /api/campaigns/{id}/regenerate -- every field optional. */
export interface RegenerateRequest {
  refinement_notes?: string;
  palette?: string;
  poster_style?: string;
  reel_feel?: string;
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
  /** `null` when the creative wasn't reviewed (older backend, or review failed). */
  critique?: CreativeCritique | null;
  /** May be absent or empty; the panel renders nothing in that case. */
  activity?: ActivityStep[];
}

export interface CreatePausedResult {
  dry_run: boolean;
  campaign_id: string | null;
  ad_set_id: string | null;
  ad_id: string | null;
  status: string;
}

/** One selectable campaign subfolder (GET /api/campaigns/drive/folders). */
export interface DriveFolder {
  id: string;
  name: string;
}

export interface SlackChannel {
  id: string;
  name: string;
}

export interface SlackShareResult {
  status: "sent";
  channel_id: string;
  channel_name: string;
  file_id: string | null;
}
