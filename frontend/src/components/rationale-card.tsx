import { Info } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { CampaignRationale, RationaleSource } from "@/lib/types";

const SOURCE_LABELS: Record<RationaleSource, string> = {
  meta_insights: "Meta ad-account history",
  meta_defaults: "Platform defaults",
  request: "What you told us",
  creative_plan: "Creative plan",
};

function SourceBadge({ source }: { source: RationaleSource }) {
  const grounded = source === "meta_insights";
  return (
    <Badge
      variant="outline"
      className={cn(
        "shrink-0",
        grounded &&
          "border-emerald-600/30 bg-emerald-600/10 text-emerald-700 dark:border-emerald-400/30 dark:bg-emerald-400/10 dark:text-emerald-400",
      )}
    >
      {SOURCE_LABELS[source]}
    </Badge>
  );
}

/**
 * Renders why the system made the choices it did. `meta_account_grounded`
 * is the honesty signal here: when it's false, none of this reasoning
 * touched real Meta ad-account history -- say so plainly rather than let
 * confident-sounding copy imply otherwise.
 */
export function RationaleCard({ rationale }: { rationale: CampaignRationale }) {
  return (
    <div className="space-y-4">
      <p className="text-sm">{rationale.summary}</p>

      {!rationale.meta_account_grounded && (
        <Alert>
          <Info />
          <AlertTitle>Not grounded in Meta ad-account history</AlertTitle>
          <AlertDescription>
            {
              "No ad-account insights were read for this run. The reasoning below rests on platform defaults and what you supplied, not your account's real performance data."
            }
          </AlertDescription>
        </Alert>
      )}

      {rationale.factors.length > 0 && (
        <>
          <Separator />
          <ul className="space-y-3">
            {rationale.factors.map((factor, i) => (
              <li key={i} className="flex items-start justify-between gap-3">
                <div className="space-y-0.5">
                  <p className="text-sm font-medium">{factor.claim}</p>
                  <p className="text-sm text-muted-foreground">{factor.evidence}</p>
                </div>
                <SourceBadge source={factor.source} />
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
