"use client";

import * as React from "react";
import { AlertTriangle, BadgeCheck, Loader2, MegaphoneOff } from "lucide-react";

import { Button } from "@/components/ui/button";
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
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ApiError, createPausedCampaign } from "@/lib/api";
import type { CreatePausedResult } from "@/lib/types";

export function CreatePausedCampaign({
  runId,
  hasMetaPreview,
}: {
  runId: string;
  hasMetaPreview: boolean;
}) {
  const [open, setOpen] = React.useState(false);
  const [pending, setPending] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<CreatePausedResult | null>(null);

  async function handleConfirm() {
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      const res = await createPausedCampaign(runId);
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't reach the backend.");
    } finally {
      setPending(false);
      setOpen(false);
    }
  }

  if (result) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BadgeCheck className="size-4 text-emerald-600 dark:text-emerald-400" />
            Paused campaign created
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p className="text-muted-foreground">
            {
              "This is a real object on the connected Meta Ads account. It won't spend anything until someone switches it on."
            }
          </p>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 pt-1">
            <dt className="text-muted-foreground">Status</dt>
            <dd>
              <Badge variant="secondary">{result.status}</Badge>
            </dd>
            <dt className="text-muted-foreground">Campaign ID</dt>
            <dd className="font-mono text-xs break-all">{result.campaign_id ?? "—"}</dd>
            <dt className="text-muted-foreground">Ad set ID</dt>
            <dd className="font-mono text-xs break-all">{result.ad_set_id ?? "—"}</dd>
            <dt className="text-muted-foreground">Ad ID</dt>
            <dd className="font-mono text-xs break-all">{result.ad_id ?? "—"}</dd>
          </dl>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {!hasMetaPreview && (
        <Alert>
          <MegaphoneOff />
          <AlertTitle>Not available for this run</AlertTitle>
          <AlertDescription>
            {"No budget was set, so there's no Meta preview to create a campaign from."}
          </AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle>{"Couldn't create the campaign"}</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <AlertDialog open={open} onOpenChange={setOpen}>
        <AlertDialogTrigger asChild>
          <Button disabled={!hasMetaPreview || pending} className="w-full sm:w-auto">
            {pending && <Loader2 className="size-4 animate-spin" />}
            Create paused campaign on Meta
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Create a real campaign on Meta?</AlertDialogTitle>
            <AlertDialogDescription>
              {
                "This creates a real campaign, ad set, and ad on the connected Meta Ads account — not a simulation. It's created "
              }
              <strong>paused</strong>
              {
                ", so it won't spend any money, but the objects themselves are real and will exist on the ad account until someone deletes them."
              }
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={pending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                void handleConfirm();
              }}
              disabled={pending}
            >
              {pending && <Loader2 className="size-4 animate-spin" />}
              Yes, create it
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
