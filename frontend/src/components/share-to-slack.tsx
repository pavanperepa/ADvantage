"use client";

import * as React from "react";
import { AlertTriangle, BadgeCheck, Loader2 } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, listSlackChannels, sharePosterToSlack } from "@/lib/api";
import type { SlackChannel, SlackShareResult } from "@/lib/types";

const DEFAULT_MESSAGE = "Sharing a new creative from ADvantage.";

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Couldn't reach the backend.";
}

function SlackMark({ className = "size-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} role="img" aria-label="Slack">
      <path fill="#36C5F0" d="M9.2 2.5a2.2 2.2 0 1 1-4.4 0 2.2 2.2 0 0 1 4.4 0v5.6H7a2.2 2.2 0 0 1 0-4.4h2.2V2.5Z" />
      <path fill="#2EB67D" d="M21.5 9.2a2.2 2.2 0 1 1 0-4.4 2.2 2.2 0 0 1 0 4.4h-5.6V7a2.2 2.2 0 0 1 4.4 0v2.2h1.2Z" />
      <path fill="#ECB22E" d="M14.8 21.5a2.2 2.2 0 1 1 4.4 0 2.2 2.2 0 0 1-4.4 0v-5.6H17a2.2 2.2 0 0 1 0 4.4h-2.2v1.2Z" />
      <path fill="#E01E5A" d="M2.5 14.8a2.2 2.2 0 1 1 0 4.4 2.2 2.2 0 0 1 0-4.4h5.6V17a2.2 2.2 0 0 1-4.4 0v-2.2H2.5Z" />
      <path fill="#36C5F0" d="M11.4 7a2.2 2.2 0 1 1 4.4 0v2.2h-4.4V7Z" />
      <path fill="#2EB67D" d="M17 11.4a2.2 2.2 0 1 1 0 4.4h-2.2v-4.4H17Z" />
      <path fill="#ECB22E" d="M12.6 17a2.2 2.2 0 1 1-4.4 0v-2.2h4.4V17Z" />
      <path fill="#E01E5A" d="M7 12.6a2.2 2.2 0 1 1 0-4.4h2.2v4.4H7Z" />
    </svg>
  );
}

export function ShareToSlack({ runId, posterSrc }: { runId: string; posterSrc: string }) {
  const [open, setOpen] = React.useState(false);
  const [channels, setChannels] = React.useState<SlackChannel[] | null>(null);
  const [channelId, setChannelId] = React.useState("");
  const [message, setMessage] = React.useState(DEFAULT_MESSAGE);
  const [loadingChannels, setLoadingChannels] = React.useState(false);
  const [sending, setSending] = React.useState(false);
  const [channelError, setChannelError] = React.useState<string | null>(null);
  const [sendError, setSendError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<SlackShareResult | null>(null);

  async function loadChannels() {
    setLoadingChannels(true);
    setChannelError(null);
    try {
      const available = await listSlackChannels(runId);
      setChannels(available);
      setChannelId((current) =>
        available.some((channel) => channel.id === current)
          ? current
          : (available[0]?.id ?? ""),
      );
    } catch (error) {
      setChannels(null);
      setChannelError(errorMessage(error));
    } finally {
      setLoadingChannels(false);
    }
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen && sending) return;
    setOpen(nextOpen);
    if (nextOpen && channels === null && !loadingChannels) void loadChannels();
  }

  async function handleSend() {
    if (sending || !channelId || !message.trim()) return;
    setSending(true);
    setSendError(null);
    try {
      const response = await sharePosterToSlack(runId, channelId, message);
      setResult(response);
      setOpen(false);
    } catch (error) {
      setSendError(errorMessage(error));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="space-y-3 border-t pt-4">
      {result && (
        <Alert className="border-emerald-600/30 text-emerald-700 dark:text-emerald-400">
          <BadgeCheck />
          <AlertTitle>Sent to #{result.channel_name}</AlertTitle>
          <AlertDescription>The message and poster were shared successfully.</AlertDescription>
        </Alert>
      )}

      <AlertDialog open={open} onOpenChange={handleOpenChange}>
        <AlertDialogTrigger asChild>
          <Button
            variant="outline"
            className="w-full gap-2 border-[#4A154B]/25 bg-white text-[#4A154B] shadow-sm hover:border-[#4A154B]/40 hover:bg-[#F8F3F8] hover:text-[#4A154B] dark:bg-white sm:w-auto"
          >
            <SlackMark className="size-[18px]" /> {result ? "Send again" : "Send to Slack"}
          </Button>
        </AlertDialogTrigger>

        <AlertDialogContent className="sm:max-w-lg">
          <AlertDialogHeader>
            <AlertDialogTitle>Send poster to Slack</AlertDialogTitle>
            <AlertDialogDescription>
              Choose a public channel and add the message that should accompany the poster.
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="space-y-4 py-1">
            {channelError && (
              <Alert variant="destructive">
                <AlertTriangle />
                <AlertTitle>{"Couldn't load Slack channels"}</AlertTitle>
                <AlertDescription className="space-y-2">
                  <p>{channelError}</p>
                  <Button type="button" variant="outline" size="sm" onClick={() => void loadChannels()}>
                    Try again
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="slack-channel">Channel</Label>
              <select
                id="slack-channel"
                value={channelId}
                onChange={(event) => setChannelId(event.target.value)}
                disabled={loadingChannels || sending || !channels?.length}
                className="h-9 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loadingChannels && <option value="">Loading channels…</option>}
                {!loadingChannels && channels?.length === 0 && <option value="">No public channels available</option>}
                {!loadingChannels && channels === null && <option value="">Select a channel</option>}
                {channels?.map((channel) => (
                  <option key={channel.id} value={channel.id}>#{channel.name}</option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="slack-message">Message</Label>
              <Textarea
                id="slack-message"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                disabled={sending}
                maxLength={4000}
                rows={3}
              />
            </div>

            <div className="overflow-hidden rounded-lg bg-muted ring-1 ring-foreground/10">
              {/* eslint-disable-next-line @next/next/no-img-element -- dynamic FastAPI artifact URL. */}
              <img src={posterSrc} alt="Poster that will be sent to Slack" className="mx-auto max-h-64 w-auto object-contain" />
            </div>

            {sendError && (
              <Alert variant="destructive">
                <AlertTriangle />
                <AlertTitle>{"Couldn't send to Slack"}</AlertTitle>
                <AlertDescription>{sendError}</AlertDescription>
              </Alert>
            )}
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel disabled={sending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                void handleSend();
              }}
              disabled={sending || loadingChannels || !channelId || !message.trim()}
            >
              {sending && <Loader2 className="size-4 animate-spin" />}
              {sending ? "Sending…" : "Send to Slack"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
