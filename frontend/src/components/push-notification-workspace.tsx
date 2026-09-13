"use client";

import * as React from "react";
import {
  AlertTriangle,
  BellRing,
  Check,
  Clipboard,
  Loader2,
  RefreshCw,
  Sparkles,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  generatePushNotifications,
  listCampaignTextContexts,
  type CampaignTextContext,
  type MessageFocus,
  type PushGenerationInput,
  type PushObjective,
  type PushTone,
  type PushVariant,
} from "@/lib/text-generation";

const OBJECTIVES: Array<[PushObjective, string]> = [
  ["product_launch", "Product launch"],
  ["promote_offer", "Promote offer"],
  ["abandoned_cart", "Abandoned cart"],
  ["re_engagement", "Re-engagement"],
  ["new_arrival", "New arrival"],
  ["limited_time_urgency", "Limited-time urgency"],
  ["event_reminder", "Event / reminder"],
  ["general_promotion", "General promotion"],
];

const TONES: Array<[PushTone, string]> = [
  ["professional", "Professional"],
  ["casual", "Casual"],
  ["energetic", "Energetic"],
  ["friendly", "Friendly"],
  ["urgent", "Urgent"],
  ["minimal", "Minimal"],
];

const FOCUSES: Array<[MessageFocus, string]> = [
  ["price_discount", "Price / discount"],
  ["convenience", "Convenience"],
  ["product_benefit", "Product benefit"],
  ["newness", "Newness"],
  ["urgency", "Urgency"],
  ["exclusivity", "Exclusivity"],
  ["social_proof", "Social proof"],
];

const CTAS = [
  "Shop now",
  "Learn more",
  "Get offer",
  "View details",
  "Book now",
  "Sign up",
  "Complete purchase",
  "See what's new",
];

interface FormState {
  campaignId: string;
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
}

const DEFAULT_FORM: FormState = {
  campaignId: "",
  productName: "",
  productDescription: "",
  offer: "",
  targetAudience: "",
  objective: "promote_offer",
  tone: "casual",
  messageFocus: "convenience",
  cta: "Shop now",
  additionalInstructions: "",
  numberOfVariants: 3,
};

function errorText(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Couldn't reach the backend. Is it running?";
}

export function PushNotificationWorkspace({
  initialCampaignId,
  embedded = false,
}: {
  initialCampaignId?: string;
  embedded?: boolean;
}) {
  const [form, setForm] = React.useState<FormState>(DEFAULT_FORM);
  const [campaigns, setCampaigns] = React.useState<CampaignTextContext[]>([]);
  const [campaignsLoading, setCampaignsLoading] = React.useState(true);
  const [campaignsError, setCampaignsError] = React.useState<string | null>(null);
  const [variants, setVariants] = React.useState<PushVariant[]>([]);
  const [generating, setGenerating] = React.useState(false);
  const [regenerating, setRegenerating] = React.useState<number | null>(null);
  const [generationError, setGenerationError] = React.useState<string | null>(null);
  const [copied, setCopied] = React.useState<number | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    listCampaignTextContexts()
      .then((items) => {
        if (cancelled) return;
        setCampaigns(items);
        if (initialCampaignId) {
          const match = items.find((item) => item.id === initialCampaignId);
          if (match) setForm((current) => applyCampaign(current, match));
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) setCampaignsError(errorText(error));
      })
      .finally(() => {
        if (!cancelled) setCampaignsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [initialCampaignId]);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function payload(overrides: Partial<PushGenerationInput> = {}): PushGenerationInput {
    return {
      campaignId: form.campaignId || undefined,
      productName: form.productName.trim(),
      productDescription: form.productDescription.trim(),
      offer: form.offer.trim(),
      targetAudience: form.targetAudience.trim(),
      objective: form.objective,
      tone: form.tone,
      messageFocus: form.messageFocus,
      cta: form.cta,
      additionalInstructions: form.additionalInstructions.trim(),
      numberOfVariants: form.numberOfVariants,
      ...overrides,
    };
  }

  function hasContext(): boolean {
    return Boolean(
      form.campaignId ||
        form.productName.trim() ||
        form.productDescription.trim() ||
        form.offer.trim(),
    );
  }

  function selectCampaign(id: string) {
    if (!id) {
      setForm((current) => ({ ...current, campaignId: "" }));
      return;
    }
    const campaign = campaigns.find((item) => item.id === id);
    if (campaign) setForm((current) => applyCampaign(current, campaign));
  }

  async function generate(event: React.FormEvent) {
    event.preventDefault();
    if (!hasContext() || generating) {
      if (!hasContext()) setGenerationError("Select a campaign or add product context.");
      return;
    }
    setGenerating(true);
    setGenerationError(null);
    try {
      setVariants(await generatePushNotifications(payload()));
    } catch (error) {
      setGenerationError(errorText(error));
    } finally {
      setGenerating(false);
    }
  }

  async function regenerate(index: number, instruction: string): Promise<boolean> {
    setRegenerating(index);
    setGenerationError(null);
    try {
      const currentVariant = variants[index];
      const avoidVariants = variants.map((item) => `${item.title}\n${item.body}`);
      const [replacement] = await generatePushNotifications(
        payload({
          numberOfVariants: 1,
          avoidVariants,
          regenerationInstruction: instruction,
          variantToReplace: `${currentVariant.title}\n${currentVariant.body}`,
        }),
      );
      setVariants((current) => current.map((item, i) => (i === index ? replacement : item)));
      return true;
    } catch (error) {
      setGenerationError(errorText(error));
      return false;
    } finally {
      setRegenerating(null);
    }
  }

  async function copyVariant(index: number) {
    const variant = variants[index];
    try {
      await navigator.clipboard.writeText(`${variant.title}\n${variant.body}`);
      setCopied(index);
      window.setTimeout(() => setCopied((current) => (current === index ? null : current)), 1800);
    } catch {
      setGenerationError("Couldn't copy to the clipboard. Select the text and copy it manually.");
    }
  }

  return (
    <div className="space-y-5">
      {embedded && (
        <div className="space-y-1">
          <h2 className="text-lg font-medium">Push notifications</h2>
          <p className="text-sm text-muted-foreground">
            Configure the message and generate concise variants for your campaign.
          </p>
        </div>
      )}
      <div
        className={
          embedded
            ? "grid items-start gap-6"
            : "grid items-start gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]"
        }
      >
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Notification settings</CardTitle>
            <CardDescription>
              Use an existing campaign as a starting point or enter fresh product context.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={generate} className="space-y-5" noValidate>
              <div className="space-y-1.5">
                <Label htmlFor="campaign">Campaign / product</Label>
                <Select
                  id="campaign"
                  value={form.campaignId}
                  onChange={(event) => selectCampaign(event.target.value)}
                  disabled={campaignsLoading}
                >
                  <option value="">
                    {campaignsLoading ? "Loading campaigns…" : "Enter context manually"}
                  </option>
                  {campaigns.map((campaign) => (
                    <option key={campaign.id} value={campaign.id}>
                      {campaign.label}
                    </option>
                  ))}
                </Select>
                {campaignsError && (
                  <p className="text-xs text-destructive">{campaignsError}</p>
                )}
                {!campaignsLoading && campaigns.length === 0 && !campaignsError && (
                  <p className="text-xs text-muted-foreground">
                    No current campaign runs. Enter context below.
                  </p>
                )}
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Product name" htmlFor="product-name">
                  <Input
                    id="product-name"
                    value={form.productName}
                    onChange={(event) => update("productName", event.target.value)}
                    placeholder="Everyday Tote"
                  />
                </Field>
                <Field label="Offer" htmlFor="offer">
                  <Input
                    id="offer"
                    value={form.offer}
                    onChange={(event) => update("offer", event.target.value)}
                    placeholder="20% off through Friday"
                  />
                </Field>
              </div>

              <Field label="Product / campaign description" htmlFor="product-description">
                <Textarea
                  id="product-description"
                  value={form.productDescription}
                  onChange={(event) => update("productDescription", event.target.value)}
                  placeholder="What it is, why it matters, and any facts the copy must preserve."
                  rows={3}
                />
              </Field>

              <Field label="Audience (optional)" htmlFor="audience">
                <Input
                  id="audience"
                  value={form.targetAudience}
                  onChange={(event) => update("targetAudience", event.target.value)}
                  placeholder="Busy commuters looking for a lighter everyday bag"
                />
              </Field>

              <div className="grid gap-4 sm:grid-cols-2">
                <SelectField
                  id="objective"
                  label="Objective"
                  value={form.objective}
                  options={OBJECTIVES}
                  onChange={(value) => update("objective", value as PushObjective)}
                />
                <SelectField
                  id="tone"
                  label="Tone"
                  value={form.tone}
                  options={TONES}
                  onChange={(value) => update("tone", value as PushTone)}
                />
                <SelectField
                  id="message-focus"
                  label="Message focus"
                  value={form.messageFocus}
                  options={FOCUSES}
                  onChange={(value) => update("messageFocus", value as MessageFocus)}
                />
                <SelectField
                  id="cta"
                  label="Call to action"
                  value={form.cta}
                  options={CTAS.map((item) => [item, item])}
                  onChange={(value) => update("cta", value)}
                />
              </div>

              <Field label="Additional instructions (optional)" htmlFor="instructions">
                <Textarea
                  id="instructions"
                  value={form.additionalInstructions}
                  onChange={(event) => update("additionalInstructions", event.target.value)}
                  placeholder="Avoid emojis. Mention curbside pickup."
                  rows={3}
                />
              </Field>

              <Field label="Number of variants" htmlFor="variant-count">
                <Select
                  id="variant-count"
                  value={String(form.numberOfVariants)}
                  onChange={(event) => update("numberOfVariants", Number(event.target.value))}
                >
                  {[1, 2, 3, 4, 5].map((count) => (
                    <option key={count} value={count}>
                      {count}
                    </option>
                  ))}
                </Select>
              </Field>

              {generationError && (
                <Alert variant="destructive">
                  <AlertTriangle />
                  <AlertTitle>Couldn&apos;t generate notifications</AlertTitle>
                  <AlertDescription>{generationError}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" size="lg" className="w-full" disabled={generating}>
                {generating ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <Sparkles />
                )}
                {generating ? "Generating notifications…" : "Generate notifications"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      <section
        aria-labelledby="generated-variants"
        className={embedded ? "space-y-3" : "space-y-3 lg:sticky lg:top-6"}
      >
        <div>
          <h2 id="generated-variants" className="font-medium">
            Generated variants
          </h2>
          <p className="text-sm text-muted-foreground">
            Recommended limits: 40 characters for titles and 100 for bodies.
          </p>
        </div>
        {generating && variants.length === 0 ? (
          <Card>
            <CardContent className="flex min-h-48 flex-col items-center justify-center gap-3 text-muted-foreground">
              <Loader2 className="size-5 animate-spin" />
              <p className="text-sm">Writing distinct notification variants…</p>
            </CardContent>
          </Card>
        ) : variants.length === 0 ? (
          <Card>
            <CardContent className="flex min-h-48 flex-col items-center justify-center gap-3 text-center text-muted-foreground">
              <BellRing className="size-6" />
              <p className="max-w-xs text-sm">
                No notifications generated yet. Choose your campaign settings and generate your
                first variants.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3" aria-live="polite">
            {variants.map((variant, index) => (
              <VariantCard
                key={`${index}-${variant.title}-${variant.body}`}
                index={index}
                variant={variant}
                copied={copied === index}
                regenerating={regenerating === index}
                disabled={generating || regenerating !== null}
                onCopy={() => copyVariant(index)}
                onRegenerate={(instruction) => regenerate(index, instruction)}
              />
            ))}
          </div>
        )}
      </section>
      </div>
    </div>
  );
}

function applyCampaign(current: FormState, campaign: CampaignTextContext): FormState {
  return {
    ...current,
    campaignId: campaign.id,
    productName: campaign.product_name,
    productDescription: campaign.product_description,
    offer: campaign.offer,
    targetAudience: campaign.target_audience,
  };
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
    </div>
  );
}

function SelectField({
  id,
  label,
  value,
  options,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  options: Array<readonly [string, string]>;
  onChange: (value: string) => void;
}) {
  return (
    <Field label={label} htmlFor={id}>
      <Select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </Select>
    </Field>
  );
}

function CharacterCount({ value, limit }: { value: string; limit: number }) {
  const over = value.length > limit;
  return (
    <span className={over ? "font-medium text-destructive" : "text-muted-foreground"}>
      {value.length} / {limit}
    </span>
  );
}

function VariantCard({
  index,
  variant,
  copied,
  regenerating,
  disabled,
  onCopy,
  onRegenerate,
}: {
  index: number;
  variant: PushVariant;
  copied: boolean;
  regenerating: boolean;
  disabled: boolean;
  onCopy: () => void;
  onRegenerate: (instruction: string) => Promise<boolean>;
}) {
  const [modalOpen, setModalOpen] = React.useState(false);
  const [instruction, setInstruction] = React.useState("");
  const [instructionError, setInstructionError] = React.useState<string | null>(null);

  async function submitRegeneration(event: React.FormEvent) {
    event.preventDefault();
    const value = instruction.trim();
    if (!value) {
      setInstructionError("Describe what you want changed in this variant.");
      return;
    }
    setInstructionError(null);
    if (await onRegenerate(value)) {
      setModalOpen(false);
      setInstruction("");
    }
  }

  function changeModalOpen(open: boolean) {
    if (regenerating) return;
    setModalOpen(open);
    if (!open) {
      setInstruction("");
      setInstructionError(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Variant {index + 1}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-3 text-xs">
            <span className="font-medium">Title</span>
            <CharacterCount value={variant.title} limit={40} />
          </div>
          <p className="text-base font-medium leading-snug">{variant.title}</p>
        </div>
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-3 text-xs">
            <span className="font-medium">Body</span>
            <CharacterCount value={variant.body} limit={100} />
          </div>
          <p className="leading-relaxed">{variant.body}</p>
        </div>
        <p className="border-l-2 pl-3 text-xs text-muted-foreground">
          {variant.reasoning_summary}
        </p>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={onCopy}>
            {copied ? <Check /> : <Clipboard />}
            {copied ? "Copied" : "Copy"}
          </Button>
          <AlertDialog open={modalOpen} onOpenChange={changeModalOpen}>
            <AlertDialogTrigger asChild>
              <Button type="button" variant="ghost" disabled={disabled}>
                <RefreshCw /> Regenerate
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent className="max-w-lg! bg-card! shadow-2xl">
              <form onSubmit={submitRegeneration} className="space-y-4">
                <AlertDialogHeader>
                  <AlertDialogTitle>Regenerate variant {index + 1}</AlertDialogTitle>
                  <AlertDialogDescription>
                    Tell ADvantage what to change. The campaign facts and current settings will be
                    preserved.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <div className="rounded-lg bg-muted/50 p-3 text-sm">
                  <p className="font-medium">{variant.title}</p>
                  <p className="mt-1 text-muted-foreground">{variant.body}</p>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor={`regeneration-instruction-${index}`}>
                    Regeneration instructions
                  </Label>
                  <Textarea
                    id={`regeneration-instruction-${index}`}
                    value={instruction}
                    onChange={(event) => {
                      setInstruction(event.target.value);
                      if (instructionError) setInstructionError(null);
                    }}
                    placeholder="For example: Make it warmer, lead with the price, and remove the phrase ‘Shop now’."
                    rows={4}
                    maxLength={1000}
                    aria-invalid={Boolean(instructionError)}
                    autoFocus
                  />
                  <div className="flex justify-between gap-3 text-xs">
                    <span className="text-destructive">{instructionError}</span>
                    <span className="text-muted-foreground">{instruction.length} / 1000</span>
                  </div>
                </div>
                <AlertDialogFooter>
                  <AlertDialogCancel type="button" disabled={regenerating}>
                    Cancel
                  </AlertDialogCancel>
                  <Button type="submit" disabled={regenerating || !instruction.trim()}>
                    {regenerating ? <Loader2 className="animate-spin" /> : <RefreshCw />}
                    {regenerating ? "Regenerating…" : "Regenerate variant"}
                  </Button>
                </AlertDialogFooter>
              </form>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  );
}
