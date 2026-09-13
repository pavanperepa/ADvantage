import { Info } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { MetaAdPreview } from "@/lib/types";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </p>
      <div className="text-sm">{children}</div>
    </div>
  );
}

export function MetaPreviewCard({ preview }: { preview: MetaAdPreview | null }) {
  if (!preview) {
    return (
      <Alert>
        <Info />
        <AlertTitle>No ad preview for this run</AlertTitle>
        <AlertDescription>
          {
            "No budget was set when this campaign was created, so there's nothing to preview on Meta yet. The creative above is still yours to use."
          }
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <Field label="Campaign name">
        <span className="font-mono text-xs break-all">{preview.campaign_name}</span>
      </Field>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Objective">
          <Badge variant="secondary">{preview.objective}</Badge>
        </Field>
        <Field label="Call to action">
          <Badge variant="secondary">{preview.call_to_action}</Badge>
        </Field>
      </div>

      <Field label="Budget">
        ${preview.daily_budget_usd.toFixed(2)}/day &times; {preview.days} day
        {preview.days === 1 ? "" : "s"}{" "}
        <span className="text-muted-foreground">
          (${(preview.daily_budget_usd * preview.days).toFixed(2)} total)
        </span>
      </Field>

      <Separator />

      <Field label="Headline">
        <p className="font-medium">{preview.headline}</p>
      </Field>

      <Field label="Primary text">
        <p className="text-muted-foreground">{preview.primary_text}</p>
      </Field>

      <Field label="Destination">
        {preview.destination_url ? (
          <a
            href={preview.destination_url}
            target="_blank"
            rel="noopener noreferrer"
            className="break-all text-primary underline underline-offset-2"
          >
            {preview.destination_url}
          </a>
        ) : (
          <span className="text-muted-foreground">Not set</span>
        )}
      </Field>
    </div>
  );
}
