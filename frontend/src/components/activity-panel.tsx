import { Check, MinusCircle, X } from "lucide-react";
import type { ActivityStep } from "@/lib/types";

/**
 * A log of what the system actually did while producing the creative.
 * Generation is otherwise an opaque wait -- this is how an owner can tell a
 * slow render apart from a step that silently fell back or was skipped.
 */
export function ActivityPanel({ activity }: { activity: ActivityStep[] }) {
  if (activity.length === 0) return null;

  return (
    <ol className="space-y-3">
      {activity.map((step, i) => (
        <li key={i} className="flex gap-3">
          <StatusDot status={step.status} />
          <div className="min-w-0 flex-1 space-y-0.5">
            <div className="flex flex-wrap items-baseline gap-x-2">
              <p className="text-sm font-medium">{step.label}</p>
              {step.seconds !== null && (
                <span className="text-xs tabular-nums text-muted-foreground">
                  {step.seconds.toFixed(2)}s
                </span>
              )}
            </div>
            {step.detail && (
              <p className="text-sm text-muted-foreground">{step.detail}</p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

function StatusDot({ status }: { status: ActivityStep["status"] }) {
  const shared = "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full";
  if (status === "failed") {
    return (
      <span className={`${shared} bg-destructive/15 text-destructive`}>
        <X className="size-3" />
      </span>
    );
  }
  if (status === "skipped") {
    return (
      <span className={`${shared} bg-muted text-muted-foreground`}>
        <MinusCircle className="size-3" />
      </span>
    );
  }
  return (
    <span className={`${shared} bg-emerald-500/15 text-emerald-600 dark:text-emerald-400`}>
      <Check className="size-3" />
    </span>
  );
}
