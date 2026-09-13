"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import {
  AlertTriangle,
  Film,
  ImageIcon,
  MessageSquareText,
  Sparkles,
  Upload,
  Video,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { GenerationProgress } from "@/components/generation-progress";
import { PushNotificationWorkspace } from "@/components/push-notification-workspace";
import { ApiError, createCampaign } from "@/lib/api";
import type { CreativeFormat } from "@/lib/types";

type CreationFormat = CreativeFormat | "text_generation";

const ACCEPTED_VIDEO_TYPES = ["video/mp4", "video/quicktime", "video/webm"];
const ACCEPTED_IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"];

interface FieldErrors {
  business_name?: string;
  brief_text?: string;
  footage?: string;
  budget_usd?: string;
  campaign_days?: string;
}

export function CampaignForm() {
  const router = useRouter();

  const [format, setFormat] = React.useState<CreationFormat>("poster");
  const [businessName, setBusinessName] = React.useState("");
  const [briefText, setBriefText] = React.useState("");
  const [contactPhone, setContactPhone] = React.useState("");
  const [destinationUrl, setDestinationUrl] = React.useState("");
  const [offerText, setOfferText] = React.useState("");
  const [audience, setAudience] = React.useState("");
  const [budgetUsd, setBudgetUsd] = React.useState("");
  const [campaignDays, setCampaignDays] = React.useState("4");
  const [logo, setLogo] = React.useState<File | null>(null);
  const [footage, setFootage] = React.useState<File[]>([]);

  const [errors, setErrors] = React.useState<FieldErrors>({});
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  function validate(): FieldErrors {
    const next: FieldErrors = {};
    if (!businessName.trim()) next.business_name = "Tell us the business name.";
    if (!briefText.trim()) next.brief_text = "A rough brief helps us write the ad copy.";
    if (format === "reel" && footage.length === 0) {
      next.footage = "Add at least one video clip — a reel needs footage to work with.";
    }
    if (budgetUsd.trim() !== "" && Number(budgetUsd) < 1) {
      next.budget_usd = "Budget must be at least $1, or left blank.";
    }
    const days = Number(campaignDays);
    if (!Number.isInteger(days) || days < 1 || days > 60) {
      next.campaign_days = "Campaign length must be a whole number of days, 1-60.";
    }
    return next;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting || format === "text_generation") return;

    const nextErrors = validate();
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitError(null);
    setSubmitting(true);

    const fd = new FormData();
    fd.set("business_name", businessName.trim());
    fd.set("brief_text", briefText.trim());
    fd.set("format", format);
    if (contactPhone.trim()) fd.set("contact_phone", contactPhone.trim());
    if (destinationUrl.trim()) fd.set("destination_url", destinationUrl.trim());
    if (offerText.trim()) fd.set("offer_text", offerText.trim());
    if (audience.trim()) fd.set("audience", audience.trim());
    if (budgetUsd.trim()) fd.set("budget_usd", budgetUsd.trim());
    fd.set("campaign_days", campaignDays.trim() || "4");
    if (format === "poster" && logo) fd.set("logo", logo);
    if (format === "reel") {
      for (const file of footage) fd.append("footage", file);
    }

    try {
      const result = await createCampaign(fd);
      router.push(`/campaigns/${result.id}`);
    } catch (err) {
      setSubmitting(false);
      if (err instanceof ApiError) {
        setSubmitError(err.message);
      } else {
        setSubmitError("Couldn't reach the backend. Is it running?");
      }
    }
  }

  if (submitting) {
    return <GenerationProgress format={format as CreativeFormat} />;
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1.5">
        <Label htmlFor="format">Format</Label>
        <Tabs value={format} onValueChange={(v) => setFormat(v as CreationFormat)}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="poster" className="gap-1.5">
              <ImageIcon /> Poster
            </TabsTrigger>
            <TabsTrigger value="reel" className="gap-1.5">
              <Video /> Reel
            </TabsTrigger>
            <TabsTrigger value="text_generation" className="gap-1.5">
              <MessageSquareText />
              <span className="hidden sm:inline">Push Notifications</span>
              <span className="sm:hidden">Push</span>
            </TabsTrigger>
          </TabsList>
        </Tabs>
        <p className="text-xs text-muted-foreground">
          {format === "poster"
            ? "A single still image ad, ready in seconds."
            : format === "reel"
              ? "A short video ad cut from your own footage — takes a minute or two."
              : "Generate concise marketing copy. Push notifications are available now."}
        </p>
      </div>

      {format === "text_generation" ? (
        <PushNotificationWorkspace embedded />
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="business_name">Business name</Label>
          <Input
            id="business_name"
            value={businessName}
            onChange={(e) => setBusinessName(e.target.value)}
            placeholder="Northstar Community Studio"
            aria-invalid={Boolean(errors.business_name)}
          />
          {errors.business_name && (
            <p className="text-xs text-destructive">{errors.business_name}</p>
          )}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="audience">Audience (optional)</Label>
          <Input
            id="audience"
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
            placeholder="Parents within 5 miles"
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="brief_text">What do you want the ad to say?</Label>
        <Textarea
          id="brief_text"
          value={briefText}
          onChange={(e) => setBriefText(e.target.value)}
          placeholder="Rough notes are fine — we'll turn them into ad copy. E.g. 'We're opening a new pottery studio, free trial class this month, open house on the 20th.'"
          rows={4}
          aria-invalid={Boolean(errors.brief_text)}
        />
        {errors.brief_text && <p className="text-xs text-destructive">{errors.brief_text}</p>}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="offer_text">Offer / deadline (optional)</Label>
          <Input
            id="offer_text"
            value={offerText}
            onChange={(e) => setOfferText(e.target.value)}
            placeholder="Free trial class through Sept 30"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="contact_phone">Contact phone (optional)</Label>
          <Input
            id="contact_phone"
            type="tel"
            value={contactPhone}
            onChange={(e) => setContactPhone(e.target.value)}
            placeholder="(555) 010-0100"
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="destination_url">Destination URL (optional)</Label>
        <Input
          id="destination_url"
          type="url"
          value={destinationUrl}
          onChange={(e) => setDestinationUrl(e.target.value)}
          placeholder="https://example.com/open-house"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="budget_usd">Total ad budget, USD (optional)</Label>
          <Input
            id="budget_usd"
            type="number"
            min={1}
            step="0.01"
            inputMode="decimal"
            value={budgetUsd}
            onChange={(e) => setBudgetUsd(e.target.value)}
            placeholder="Leave blank for no Meta ad preview"
            aria-invalid={Boolean(errors.budget_usd)}
          />
          {errors.budget_usd ? (
            <p className="text-xs text-destructive">{errors.budget_usd}</p>
          ) : (
            <p className="text-xs text-muted-foreground">
              {
                "Spread evenly over the campaign length below. Leave blank and you'll still get your creative — just no ad preview."
              }
            </p>
          )}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="campaign_days">Campaign length, days</Label>
          <Input
            id="campaign_days"
            type="number"
            min={1}
            max={60}
            step="1"
            inputMode="numeric"
            value={campaignDays}
            onChange={(e) => setCampaignDays(e.target.value)}
            aria-invalid={Boolean(errors.campaign_days)}
          />
          {errors.campaign_days && (
            <p className="text-xs text-destructive">{errors.campaign_days}</p>
          )}
        </div>
      </div>

      <AnimatePresence mode="wait">
        {format === "poster" ? (
          <motion.div
            key="logo"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
            className="space-y-1.5"
          >
            <Label htmlFor="logo">Logo (optional)</Label>
            <FileDropInput
              id="logo"
              icon={<ImageIcon className="size-4" />}
              accept={ACCEPTED_IMAGE_TYPES.join(",")}
              hint="PNG, JPEG, or WebP"
              files={logo ? [logo] : []}
              onChange={(files) => setLogo(files[0] ?? null)}
            />
          </motion.div>
        ) : (
          <motion.div
            key="footage"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
            className="space-y-1.5"
          >
            <Label htmlFor="footage">Footage (required for a reel)</Label>
            <FileDropInput
              id="footage"
              icon={<Film className="size-4" />}
              accept={ACCEPTED_VIDEO_TYPES.join(",")}
              hint="MP4, MOV, or WebM — one or more clips"
              multiple
              files={footage}
              onChange={setFootage}
            />
            {errors.footage && <p className="text-xs text-destructive">{errors.footage}</p>}
          </motion.div>
        )}
      </AnimatePresence>

      {submitError && (
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle>{"Couldn't create this campaign"}</AlertTitle>
          <AlertDescription>{submitError}</AlertDescription>
        </Alert>
      )}

      <Button type="submit" size="lg" className="w-full gap-1.5" disabled={submitting}>
        <Sparkles className="size-4" />
        Generate {format === "poster" ? "poster" : "reel"}
      </Button>
        </form>
      )}
    </div>
  );
}

function FileDropInput({
  id,
  icon,
  accept,
  hint,
  multiple,
  files,
  onChange,
}: {
  id: string;
  icon: React.ReactNode;
  accept: string;
  hint: string;
  multiple?: boolean;
  files: File[];
  onChange: (files: File[]) => void;
}) {
  const inputRef = React.useRef<HTMLInputElement>(null);

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className="flex w-full items-center gap-3 rounded-lg border border-dashed border-input bg-transparent px-3 py-3 text-left text-sm text-muted-foreground transition-colors hover:border-ring hover:text-foreground"
      >
        <Upload className="size-4 shrink-0" aria-hidden />
        <span className="flex-1">
          {files.length > 0
            ? `${files.length} file${files.length > 1 ? "s" : ""} selected`
            : `Click to choose ${multiple ? "file(s)" : "a file"}`}
        </span>
        {icon}
      </button>
      <input
        ref={inputRef}
        id={id}
        type="file"
        accept={accept}
        multiple={multiple}
        className="sr-only"
        onChange={(e) => onChange(Array.from(e.target.files ?? []))}
      />
      <p className="text-xs text-muted-foreground">{hint}</p>
      {files.length > 0 && (
        <ul className="space-y-1">
          {files.map((file, i) => (
            <li
              key={`${file.name}-${i}`}
              className="flex items-center justify-between gap-2 rounded-md bg-muted px-2.5 py-1.5 text-xs"
            >
              <span className="truncate">{file.name}</span>
              <button
                type="button"
                onClick={() => onChange(files.filter((_, idx) => idx !== i))}
                className="shrink-0 text-muted-foreground hover:text-foreground"
                aria-label={`Remove ${file.name}`}
              >
                <X className="size-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
