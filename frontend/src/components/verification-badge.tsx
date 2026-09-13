import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function VerificationBadge({ passed }: { passed: boolean }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1",
        passed
          ? "border-emerald-600/30 bg-emerald-600/10 text-emerald-700 dark:border-emerald-400/30 dark:bg-emerald-400/10 dark:text-emerald-400"
          : "border-amber-600/30 bg-amber-600/10 text-amber-700 dark:border-amber-400/30 dark:bg-amber-400/10 dark:text-amber-400",
      )}
    >
      {passed ? <CheckCircle2 className="size-3" /> : <AlertTriangle className="size-3" />}
      {passed ? "Verified" : "Needs review"}
    </Badge>
  );
}
