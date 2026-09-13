"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import {
  AlertTriangle,
  Film,
  FolderOpen,
  ImageIcon,
  MessageSquareText,
  ListChecks,
  Loader2,
  Plus,
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
import { PushNotificationWorkspace } from "@/components/push-notification-workspace";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { GenerationProgress } from "@/components/generation-progress";
import { ApiError, createCampaign, fetchDriveFolders, fetchInterviewQuestions } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  AgentInference,
  CreativeFormat,
  DriveFolder,
  InterviewAnswers,
  InterviewQuestion,
} from "@/lib/types";

const ACCEPTED_VIDEO_TYPES = ["video/mp4", "video/quicktime", "video/webm"];
const ACCEPTED_IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"];

// Answer ids the create endpoint understands directly (see
// `POST /api/campaigns`'s optional fields). Any other question id the
// interview loop invents is used only to steer follow-up questions, not
// forwarded on submit.
const KNOWN_STRING_ANSWER_KEYS = [
  "reel_feel",
  "poster_style",
  "art_direction_notes",
  "proof_point",
] as const;

const STEP_TITLES = ["Brief", "A few questions", "Budget & destination"] as const;

// Text generation is a third thing the owner can create, but unlike a poster
// or a reel it produces copy rather than a rendered artifact, so it bypasses
// the three-step flow entirely and hands over to its own workspace.
type CreationFormat = CreativeFormat | "text_generation";

interface FieldErrors {
  business_name?: string;
  brief_text?: string;
  footage?: string;
  budget_usd?: string;
  campaign_days?: string;
}

function isAnswerEmpty(value: string | string[] | undefined): boolean {
  if (value === undefined) return true;
  if (Array.isArray(value)) return value.every((v) => !v.trim());
  return value.trim() === "";
}

export function CampaignForm() {
  const router = useRouter();

  const [step, setStep] = React.useState<1 | 2 | 3>(1);

  const [format, setFormat] = React.useState<CreationFormat>("poster");
  // Narrowed view of `format` for the poster/reel-only paths below. Text
  // generation bails out of both before either is reached.
  const creativeFormat: CreativeFormat = format === "text_generation" ? "poster" : format;
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

  // Alternative to uploading: pick a folder from the owner's Google Drive
  // ("Shared with me" -> "Social Media") instead. Degrades silently to the
  // upload-only UI whenever the folders call fails or Drive isn't connected
  // -- the owner must always be able to create a campaign by uploading.
  const [assetSource, setAssetSource] = React.useState<"upload" | "drive">("upload");
  const [driveFolders, setDriveFolders] = React.useState<DriveFolder[]>([]);
  const [driveFoldersLoading, setDriveFoldersLoading] = React.useState(true);
  const [driveAvailable, setDriveAvailable] = React.useState(false);
  const [selectedDriveFolderId, setSelectedDriveFolderId] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    fetchDriveFolders()
      .then((folders) => {
        if (cancelled) return;
        setDriveFolders(folders);
        setDriveAvailable(true);
      })
      .catch(() => {
        if (cancelled) return;
        setDriveAvailable(false);
      })
      .finally(() => {
        if (!cancelled) setDriveFoldersLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const [errors, setErrors] = React.useState<FieldErrors>({});
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  // Step 2: the agentic interview. `answers` accumulates everything
  // confirmed so far; `questions` is the current batch (kept around after
  // the interview finishes so "Back" from step 3 can return to it);
  // `draftAnswers` holds in-progress edits for the batch on screen.
  const [questions, setQuestions] = React.useState<InterviewQuestion[]>([]);
  const [answers, setAnswers] = React.useState<InterviewAnswers>({});
  const [draftAnswers, setDraftAnswers] = React.useState<InterviewAnswers>({});
  const [questionErrors, setQuestionErrors] = React.useState<Record<string, string>>({});
  const [interviewLoading, setInterviewLoading] = React.useState(false);
  const [interviewAvailable, setInterviewAvailable] = React.useState(true);
  // What the agent already worked out from the brief this round: a short
  // intro line, the facts it applied without asking, and where we are in
  // the (at most two) rounds of questions. All optional -- an older backend
  // or a degraded LLM path simply omits them and the form still works.
  const [agentNote, setAgentNote] = React.useState<string | null>(null);
  const [understood, setUnderstood] = React.useState<AgentInference[]>([]);
  const [round, setRound] = React.useState<number | null>(null);
  const [totalRounds, setTotalRounds] = React.useState<number | null>(null);

  function validateBrief(): FieldErrors {
    const next: FieldErrors = {};
    if (!businessName.trim()) next.business_name = "Tell us the business name.";
    if (!briefText.trim()) next.brief_text = "A rough brief helps us write the ad copy.";
    const usingDriveFolder = assetSource === "drive" && Boolean(selectedDriveFolderId);
    if (format === "reel" && footage.length === 0 && !usingDriveFolder) {
      next.footage = "Add at least one video clip — a reel needs footage to work with.";
    }
    if (assetSource === "drive" && !selectedDriveFolderId) {
      next.footage = "Pick a Google Drive folder, or switch back to uploading files.";
    }
    return next;
  }

  function validateDetails(): FieldErrors {
    const next: FieldErrors = {};
    if (budgetUsd.trim() !== "" && Number(budgetUsd) < 1) {
      next.budget_usd = "Budget must be at least $1, or left blank.";
    }
    const days = Number(campaignDays);
    if (!Number.isInteger(days) || days < 1 || days > 60) {
      next.campaign_days = "Campaign length must be a whole number of days, 1-60.";
    }
    return next;
  }

  // Fetches the next batch of interview questions given everything answered
  // so far, and lands on the right step for the result. On any failure the
  // guided interview is abandoned for this session and we go straight to
  // the final step -- generation must still work without it.
  async function runInterview(accumulated: InterviewAnswers) {
    setInterviewLoading(true);
    try {
      const res = await fetchInterviewQuestions(
        businessName.trim(),
        briefText.trim(),
        creativeFormat,
        accumulated,
      );
      const nextAnswers = res.answers ?? accumulated;
      setAnswers(nextAnswers);
      setInterviewAvailable(true);
      setAgentNote(res.agent_note ?? null);
      setUnderstood(res.understood ?? []);
      setRound(res.round ?? null);
      setTotalRounds(res.total_rounds ?? null);
      if (res.ready || res.questions.length === 0) {
        setStep(3);
      } else {
        setQuestions(res.questions);
        const draft: InterviewAnswers = {};
        for (const q of res.questions) {
          if (nextAnswers[q.id] !== undefined) {
            // Already confirmed in an earlier round -- keep it.
            draft[q.id] = nextAnswers[q.id];
          } else if (q.suggestion !== null && q.suggestion !== undefined) {
            // No answer yet: start from the agent's drafted answer. The
            // user can edit or clear it freely -- this just saves them
            // from typing what the agent already worked out.
            draft[q.id] = q.suggestion;
          }
        }
        setDraftAnswers(draft);
        setStep(2);
      }
    } catch {
      setInterviewAvailable(false);
      setStep(3);
    } finally {
      setInterviewLoading(false);
    }
  }

  async function handleContinueFromBrief() {
    const nextErrors = validateBrief();
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    setSubmitError(null);
    await runInterview(answers);
  }

  function setDraftAnswer(id: string, value: string | string[]) {
    setDraftAnswers((prev) => ({ ...prev, [id]: value }));
    setQuestionErrors((prev) => {
      if (!(id in prev)) return prev;
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }

  async function handleContinueFromQuestions() {
    const nextErrors: Record<string, string> = {};
    for (const q of questions) {
      if (q.required && isAnswerEmpty(draftAnswers[q.id])) {
        nextErrors[q.id] = "This one's required.";
      }
    }
    setQuestionErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    const merged: InterviewAnswers = { ...answers };
    for (const q of questions) {
      const value = draftAnswers[q.id];
      if (isAnswerEmpty(value)) continue;
      merged[q.id] = Array.isArray(value)
        ? value.map((v) => v.trim()).filter(Boolean)
        : value.trim();
    }
    setAnswers(merged);
    await runInterview(merged);
  }

  function handleBackToBrief() {
    setStep(1);
  }

  function handleBackFromDetails() {
    setStep(interviewAvailable && questions.length > 0 ? 2 : 1);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (step !== 3 || submitting || format === "text_generation") return;

    const nextErrors = validateDetails();
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
    if (assetSource === "drive" && selectedDriveFolderId) {
      fd.set("drive_folder_id", selectedDriveFolderId);
    } else {
      if (format === "poster" && logo) fd.set("logo", logo);
      if (format === "reel") {
        for (const file of footage) fd.append("footage", file);
      }
    }

    // Forward whatever the guided interview collected that the create
    // endpoint understands. If the interview never ran (degraded path),
    // `answers` is empty and these are simply skipped.
    for (const key of KNOWN_STRING_ANSWER_KEYS) {
      const value = answers[key];
      if (typeof value === "string" && value.trim()) fd.set(key, value.trim());
    }
    const benefits = answers.key_benefits;
    if (Array.isArray(benefits)) {
      for (const benefit of benefits) {
        if (benefit.trim()) fd.append("key_benefits", benefit.trim());
      }
    } else if (typeof benefits === "string" && benefits.trim()) {
      fd.append("key_benefits", benefits.trim());
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
    return <GenerationProgress format={creativeFormat} />;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6" noValidate>
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            Step {step} of 3
          </span>
          <span className="font-medium text-foreground">{STEP_TITLES[step - 1]}</span>
        </div>
        <Progress value={(step / 3) * 100} />
      </div>

      {step === 1 && (
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
                  <MessageSquareText /> Text
                </TabsTrigger>
              </TabsList>
            </Tabs>
            <p className="text-xs text-muted-foreground">
              {format === "poster"
                ? "A single still image ad, ready in seconds."
                : format === "reel"
                  ? "A short video ad cut from your own footage — takes a minute or two."
                  : "Push and campaign copy, generated as text — no artwork rendered."}
            </p>
          </div>

          {/* Text generation has no brief/asset/budget steps of its own, so it
              takes over the rest of the form rather than continuing to step 2. */}
          {format === "text_generation" ? (
            <PushNotificationWorkspace embedded />
          ) : (
          <>

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

          {driveAvailable && (
            <div className="space-y-1.5">
              <Label>Assets</Label>
              <Tabs
                value={assetSource}
                onValueChange={(v) => setAssetSource(v as "upload" | "drive")}
              >
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="upload" className="gap-1.5">
                    <Upload className="size-4" /> Upload files
                  </TabsTrigger>
                  <TabsTrigger value="drive" className="gap-1.5">
                    <FolderOpen className="size-4" /> Use my Google Drive
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          )}
          {!driveFoldersLoading && !driveAvailable && (
            <p className="text-xs text-muted-foreground">
              Google Drive isn&apos;t connected — upload files below instead.
            </p>
          )}

          <AnimatePresence mode="wait">
            {assetSource === "drive" ? (
              <motion.div
                key="drive"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.2 }}
                className="space-y-1.5"
              >
                <Label>Pick a campaign folder</Label>
                {driveFolders.length === 0 ? (
                  <p className="text-xs text-muted-foreground">
                    No campaign folders found under &quot;Social Media&quot; in your Google
                    Drive.
                  </p>
                ) : (
                  <div className="space-y-1.5">
                    {driveFolders.map((folder) => {
                      const selected = selectedDriveFolderId === folder.id;
                      return (
                        <button
                          key={folder.id}
                          type="button"
                          onClick={() => setSelectedDriveFolderId(folder.id)}
                          className={cn(
                            "flex w-full items-center gap-2.5 rounded-lg border px-3 py-2.5 text-left text-sm transition-colors",
                            selected
                              ? "border-primary bg-primary/5"
                              : "border-input hover:border-ring",
                          )}
                        >
                          <FolderOpen className="size-4 shrink-0 text-muted-foreground" />
                          <span className="flex-1 truncate">{folder.name}</span>
                        </button>
                      );
                    })}
                  </div>
                )}
                {errors.footage && <p className="text-xs text-destructive">{errors.footage}</p>}
              </motion.div>
            ) : format === "poster" ? (
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

          <Button
            type="button"
            size="lg"
            className="w-full gap-1.5"
            disabled={interviewLoading}
            onClick={handleContinueFromBrief}
          >
            {interviewLoading && <Loader2 className="size-4 animate-spin" />}
            Continue
          </Button>

          </>
          )}
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4">
          {agentNote && (
            <div className="flex items-start gap-2.5 rounded-lg border border-border/70 bg-muted/40 px-4 py-3.5">
              <Sparkles className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <div className="space-y-1">
                <p className="text-sm">{agentNote}</p>
                {round != null && totalRounds != null && (
                  <p className="text-xs text-muted-foreground">
                    Question round {round} of {totalRounds}
                  </p>
                )}
              </div>
            </div>
          )}
          {!agentNote && round != null && totalRounds != null && (
            <p className="text-xs text-muted-foreground">
              Question round {round} of {totalRounds}
            </p>
          )}

          {understood.length > 0 && (
            <div className="space-y-2.5 rounded-lg border border-border/70 bg-card px-4 py-3.5">
              <div className="flex items-center gap-2">
                <ListChecks className="size-4 text-muted-foreground" />
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Already picked up from your brief
                </span>
              </div>
              <ul className="space-y-2">
                {understood.map((item) => (
                  <li
                    key={item.field}
                    className="flex flex-col gap-0.5 sm:flex-row sm:items-start sm:justify-between sm:gap-3"
                  >
                    <div className="space-y-0.5">
                      <p className="text-sm font-medium">{item.label}</p>
                      <p className="text-xs text-muted-foreground">{item.note}</p>
                    </div>
                    <p className="text-sm sm:max-w-[55%] sm:text-right">{item.value}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {questions.map((q) => (
            <InterviewQuestionField
              key={q.id}
              question={q}
              value={draftAnswers[q.id]}
              error={questionErrors[q.id]}
              onChange={setDraftAnswer}
            />
          ))}

          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleBackToBrief}
              disabled={interviewLoading}
            >
              Back
            </Button>
            <Button
              type="button"
              className="flex-1 gap-1.5"
              disabled={interviewLoading}
              onClick={handleContinueFromQuestions}
            >
              {interviewLoading && <Loader2 className="size-4 animate-spin" />}
              Looks good — continue
            </Button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-6">
          {!interviewAvailable && (
            <p className="text-xs text-muted-foreground">
              {
                "We couldn't reach the guided questions this time, so we skipped ahead — you can still generate below."
              }
            </p>
          )}

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

          <div className="space-y-1.5">
            <Label htmlFor="audience">Audience (optional)</Label>
            <Input
              id="audience"
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
              placeholder="Parents within 5 miles"
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

          {submitError && (
            <Alert variant="destructive">
              <AlertTriangle />
              <AlertTitle>{"Couldn't create this campaign"}</AlertTitle>
              <AlertDescription>{submitError}</AlertDescription>
            </Alert>
          )}

          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={handleBackFromDetails}>
              Back
            </Button>
            <Button type="submit" size="lg" className="flex-1 gap-1.5">
              <Sparkles className="size-4" />
              Generate {format === "poster" ? "poster" : "reel"}
            </Button>
          </div>
        </div>
      )}
    </form>
  );
}

function InterviewQuestionField({
  question,
  value,
  error,
  onChange,
}: {
  question: InterviewQuestion;
  value: string | string[] | undefined;
  error?: string;
  onChange: (id: string, value: string | string[]) => void;
}) {
  return (
    <div className="space-y-2 rounded-lg border border-border/70 bg-card px-4 py-3.5">
      <div className="space-y-0.5">
        <p className="text-sm font-medium">
          {question.prompt}
          {!question.required && (
            <span className="ml-1.5 text-xs font-normal text-muted-foreground">(optional)</span>
          )}
        </p>
        <p className="text-xs text-muted-foreground">{question.why}</p>
      </div>

      {question.kind === "text" && (
        <Input
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(question.id, e.target.value)}
          aria-invalid={Boolean(error)}
        />
      )}

      {question.kind === "choice" && (
        <div className="flex flex-wrap gap-2">
          {(question.choices ?? []).map((choice) => {
            const selected = value === choice.value;
            const suggested = question.suggestion === choice.value;
            return (
              <Button
                key={choice.value}
                type="button"
                variant={selected ? "default" : "outline"}
                size="sm"
                className="gap-1.5"
                onClick={() => onChange(question.id, selected ? "" : choice.value)}
              >
                {choice.label}
                {suggested && (
                  <Badge variant="secondary" className="h-4 px-1.5 text-[10px] font-normal">
                    Suggested
                  </Badge>
                )}
              </Button>
            );
          })}
        </div>
      )}

      {question.kind === "multi_text" && (
        <MultiTextField
          values={Array.isArray(value) ? value : []}
          onChange={(v) => onChange(question.id, v)}
        />
      )}

      {question.suggestion_note && (
        <p className="text-xs text-muted-foreground italic">{question.suggestion_note}</p>
      )}

      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

function MultiTextField({
  values,
  onChange,
}: {
  values: string[];
  onChange: (values: string[]) => void;
}) {
  const rows = values.length > 0 ? values : [""];

  return (
    <div className="space-y-2">
      {rows.map((row, i) => (
        <div key={i} className="flex items-center gap-2">
          <Input
            value={row}
            onChange={(e) => {
              const next = [...rows];
              next[i] = e.target.value;
              onChange(next);
            }}
          />
          {rows.length > 1 && (
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label="Remove"
              onClick={() => onChange(rows.filter((_, idx) => idx !== i))}
            >
              <X className="size-3.5" />
            </Button>
          )}
        </div>
      ))}
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="gap-1.5"
        onClick={() => onChange([...rows, ""])}
      >
        <Plus className="size-3.5" /> Add another
      </Button>
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
