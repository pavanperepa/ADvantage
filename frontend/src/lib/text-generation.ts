import { API_BASE_URL, ApiError } from "./api";

export type PushObjective =
  | "product_launch"
  | "promote_offer"
  | "abandoned_cart"
  | "re_engagement"
  | "new_arrival"
  | "limited_time_urgency"
  | "event_reminder"
  | "general_promotion";

export type PushTone =
  | "professional"
  | "casual"
  | "energetic"
  | "friendly"
  | "urgent"
  | "minimal";

export type MessageFocus =
  | "price_discount"
  | "convenience"
  | "product_benefit"
  | "newness"
  | "urgency"
  | "exclusivity"
  | "social_proof";

export interface PushGenerationInput {
  campaignId?: string;
  productName: string;
  productDescription: string;
  offer: string;
  targetAudience: string;
  objective: PushObjective;
  tone: PushTone;
  messageFocus: MessageFocus;
  cta: string;
  additionalInstructions: string;
  numberOfVariants: number;
  avoidVariants?: string[];
  regenerationInstruction?: string;
  variantToReplace?: string;
}

export interface PushVariant {
  title: string;
  body: string;
  reasoning_summary: string;
}

export interface CampaignTextContext {
  id: string;
  label: string;
  product_name: string;
  product_description: string;
  offer: string;
  target_audience: string;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
  } catch {
    // Use the same generic fallback convention as the main API client.
  }
  return `Request failed with status ${response.status}.`;
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  return (await response.json()) as T;
}

export async function listCampaignTextContexts(): Promise<CampaignTextContext[]> {
  const response = await fetch(`${API_BASE_URL}/api/text-generation/campaigns`, {
    cache: "no-store",
  });
  return readJson<CampaignTextContext[]>(response);
}

export async function generatePushNotifications(
  input: PushGenerationInput,
): Promise<PushVariant[]> {
  const response = await fetch(`${API_BASE_URL}/api/text-generation/push`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  const result = await readJson<{ variants: PushVariant[] }>(response);
  return result.variants;
}
