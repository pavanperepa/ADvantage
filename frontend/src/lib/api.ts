import type {
  CampaignRun,
  CreatePausedResult,
  CreativeFormat,
  DriveFolder,
  InterviewAnswers,
  InterviewResponse,
  Palette,
  RegenerateRequest,
  SlackChannel,
  SlackShareResult,
} from "./types";

/**
 * Browser-visible base URL for the FastAPI backend. It is relative by default,
 * so the deployment router can send `/api` to the backend service (and Next.js
 * can proxy to port 8000 during standalone local development). Set
 * NEXT_PUBLIC_API_BASE_URL only when deliberately exposing the backend at a
 * separate public origin.
 */
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? ""
).replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function extractErrorMessage(res: Response): Promise<string> {
  try {
    const data: unknown = await res.json();
    if (
      data &&
      typeof data === "object" &&
      "detail" in data &&
      typeof (data as { detail?: unknown }).detail === "string"
    ) {
      return (data as { detail: string }).detail;
    }
  } catch {
    // Body wasn't JSON -- fall through to the generic message below.
  }
  return `Request failed with status ${res.status}.`;
}

/** POST /api/campaigns -- create a run. Blocks until generation finishes. */
export async function createCampaign(formData: FormData): Promise<CampaignRun> {
  const res = await fetch(`${API_BASE_URL}/api/campaigns`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new ApiError(res.status, await extractErrorMessage(res));
  return (await res.json()) as CampaignRun;
}

/**
 * POST /api/campaigns/interview -- the agentic intake loop. Call with
 * `answers: {}` for the first batch of questions, then POST the accumulated
 * answers back for the next batch. At most 4 questions come back at a time;
 * `ready: true` means it's time to generate.
 */
export async function fetchInterviewQuestions(
  businessName: string,
  briefText: string,
  format: CreativeFormat,
  answers: InterviewAnswers,
): Promise<InterviewResponse> {
  const res = await fetch(`${API_BASE_URL}/api/campaigns/interview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      business_name: businessName,
      brief_text: briefText,
      format,
      answers,
    }),
  });
  if (!res.ok) throw new ApiError(res.status, await extractErrorMessage(res));
  return (await res.json()) as InterviewResponse;
}

/** GET /api/campaigns/{id} -- fetch a run's current record. */
export async function getCampaign(id: string): Promise<CampaignRun> {
  const res = await fetch(`${API_BASE_URL}/api/campaigns/${encodeURIComponent(id)}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new ApiError(res.status, await extractErrorMessage(res));
  return (await res.json()) as CampaignRun;
}

/** Full URL for the rendered artifact (image or video), for direct `src=` use. */
export function artifactUrl(id: string): string {
  return `${API_BASE_URL}/api/campaigns/${encodeURIComponent(id)}/artifact`;
}

/** POST /api/campaigns/{id}/create-paused-campaign -- a real, external write. */
export async function createPausedCampaign(id: string): Promise<CreatePausedResult> {
  const res = await fetch(
    `${API_BASE_URL}/api/campaigns/${encodeURIComponent(id)}/create-paused-campaign`,
    { method: "POST" },
  );
  if (!res.ok) throw new ApiError(res.status, await extractErrorMessage(res));
  return (await res.json()) as CreatePausedResult;
}

/** GET /api/campaigns/palettes -- the colour schemes a creative can use. */
export async function fetchPalettes(): Promise<Palette[]> {
  const res = await fetch(`${API_BASE_URL}/api/campaigns/palettes`, { cache: "no-store" });
  if (!res.ok) throw new ApiError(res.status, await extractErrorMessage(res));
  return (await res.json()) as Palette[];
}

/**
 * GET /api/campaigns/drive/folders -- the owner's Google Drive campaign
 * subfolders (under "Shared with me" -> "Social Media"), for picking one
 * instead of uploading files. Throws `ApiError` with status 503 when Drive
 * isn't connected yet -- callers should degrade to the upload UI rather than
 * surface this as a hard failure.
 */
export async function fetchDriveFolders(): Promise<DriveFolder[]> {
  const res = await fetch(`${API_BASE_URL}/api/campaigns/drive/folders`, { cache: "no-store" });
  if (!res.ok) throw new ApiError(res.status, await extractErrorMessage(res));
  return (await res.json()) as DriveFolder[];
}

/**
 * POST /api/campaigns/{id}/regenerate -- re-run with refinements.
 * Returns a NEW run; the original is kept, not overwritten.
 */
export async function regenerateCampaign(
  id: string,
  body: RegenerateRequest,
): Promise<CampaignRun> {
  const res = await fetch(
    `${API_BASE_URL}/api/campaigns/${encodeURIComponent(id)}/regenerate`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  if (!res.ok) throw new ApiError(res.status, await extractErrorMessage(res));
  return (await res.json()) as CampaignRun;
}

/** GET eligible public Slack channels for a generated poster. */
export async function listSlackChannels(id: string): Promise<SlackChannel[]> {
  const res = await fetch(
    `${API_BASE_URL}/api/campaigns/${encodeURIComponent(id)}/slack/channels`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new ApiError(res.status, await extractErrorMessage(res));
  return (await res.json()) as SlackChannel[];
}

/** Send the generated poster and message to one public Slack channel. */
export async function sharePosterToSlack(
  id: string,
  channelId: string,
  message: string,
): Promise<SlackShareResult> {
  const res = await fetch(
    `${API_BASE_URL}/api/campaigns/${encodeURIComponent(id)}/slack`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel_id: channelId, message }),
    },
  );
  if (!res.ok) throw new ApiError(res.status, await extractErrorMessage(res));
  return (await res.json()) as SlackShareResult;
}
