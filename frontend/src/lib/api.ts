import type {
  CampaignRun,
  CreatePausedResult,
  CreativeFormat,
  InterviewAnswers,
  InterviewResponse,
} from "./types";

/**
 * Base URL for the FastAPI backend. Defaults to the port the backend uses
 * out of the box (`uvicorn cricket_posts.web:app`, port 8000). Override with
 * NEXT_PUBLIC_API_BASE_URL, e.g. for local testing against a backend running
 * on a different port.
 */
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"
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
