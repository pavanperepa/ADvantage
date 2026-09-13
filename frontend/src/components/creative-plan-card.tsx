import { Lightbulb } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { CreativePlan } from "@/lib/types";

/**
 * Renders the creative plan generation settled on -- the "feel" it aimed
 * for and the individual choices behind it. Meant to read as "here's what
 * the system decided, and why," not just a list of settings.
 */
export function CreativePlanCard({ plan }: { plan: CreativePlan }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Lightbulb className="size-4 text-muted-foreground" />
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Feel
        </span>
        <Badge variant="secondary" className="capitalize">
          {plan.feel.replace(/_/g, " ")}
        </Badge>
      </div>

      {plan.decisions.length > 0 && (
        <>
          <Separator />
          <ul className="space-y-3">
            {plan.decisions.map((decision, i) => (
              <li key={i} className="space-y-0.5">
                <p className="text-sm font-medium">{decision.choice}</p>
                <p className="text-sm text-muted-foreground">{decision.reason}</p>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
