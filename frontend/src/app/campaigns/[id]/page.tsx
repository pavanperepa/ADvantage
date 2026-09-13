"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertTriangle, ArrowLeft, Loader2 } from "lucide-react";

import { PageSection } from "@/components/page-section";
import { ArtifactViewer } from "@/components/artifact-viewer";
import { VerificationBadge } from "@/components/verification-badge";
import { MetaPreviewCard } from "@/components/meta-preview-card";
import { CreatePausedCampaign } from "@/components/create-paused-campaign";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ApiError, artifactUrl, getCampaign } from "@/lib/api";
import type { CampaignRun } from "@/lib/types";

export default function CampaignReviewPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [run, setRun] = React.useState<CampaignRun | null>(null);
  const [error, setError] = React.useState<{ status: number; message: string } | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;
    // Resetting to a loading state here (rather than only in the .then/.catch
    // callbacks below) is deliberate: it's what makes re-fetching correct if
    // `id` ever changes on an already-mounted page.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setError(null);
    getCampaign(id)
      .then((data) => {
        if (!cancelled) setRun(data);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError) {
          setError({ status: err.status, message: err.message });
        } else {
          setError({ status: 0, message: "Couldn't reach the backend. Is it running?" });
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col items-center gap-3 px-4 py-24 text-muted-foreground">
        <Loader2 className="size-5 animate-spin" />
        <p className="text-sm">Loading campaign…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-14 sm:px-6">
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle>
            {error.status === 404 ? "This run is gone" : "Couldn't load this campaign"}
          </AlertTitle>
          <AlertDescription>{error.message}</AlertDescription>
        </Alert>
        <Button asChild variant="outline" className="mt-4 gap-1.5">
          <Link href="/">
            <ArrowLeft className="size-4" /> Start a new campaign
          </Link>
        </Button>
      </div>
    );
  }

  if (!run) return null;

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-10 sm:px-6 sm:py-14">
      <PageSection delay={0} className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">Campaign run</p>
          <p className="font-mono text-sm">{run.id}</p>
        </div>
        <Badge variant="secondary" className="capitalize">
          {run.artifact.format}
        </Badge>
      </PageSection>

      <PageSection delay={0.05}>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <CardTitle>Creative</CardTitle>
            <VerificationBadge passed={run.verification.passed} />
          </CardHeader>
          <CardContent className="space-y-4">
            <ArtifactViewer artifact={run.artifact} src={artifactUrl(run.id)} />
            {run.artifact.duration_seconds != null && (
              <p className="text-center text-xs text-muted-foreground">
                {run.artifact.duration_seconds.toFixed(1)}s &middot; {run.artifact.width}&times;
                {run.artifact.height}
              </p>
            )}
            {!run.verification.passed && run.verification.findings.length > 0 && (
              <Alert variant="destructive">
                <AlertTriangle />
                <AlertTitle>Flagged during verification</AlertTitle>
                <AlertDescription>
                  <ul className="list-inside list-disc space-y-0.5">
                    {run.verification.findings.map((finding, i) => (
                      <li key={i}>{finding}</li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </PageSection>

      <PageSection delay={0.1}>
        <Card>
          <CardHeader>
            <CardTitle>Meta ad preview</CardTitle>
            <CardDescription>What would be created on Meta Ads, if you proceed.</CardDescription>
          </CardHeader>
          <CardContent>
            <MetaPreviewCard preview={run.meta_preview} />
          </CardContent>
        </Card>
      </PageSection>

      <PageSection delay={0.15}>
        <Card>
          <CardHeader>
            <CardTitle>Publish</CardTitle>
            <CardDescription>
              Create the campaign on Meta, paused. Nothing spends until someone
              unpauses it.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CreatePausedCampaign runId={run.id} hasMetaPreview={run.meta_preview != null} />
          </CardContent>
        </Card>
      </PageSection>
    </div>
  );
}
