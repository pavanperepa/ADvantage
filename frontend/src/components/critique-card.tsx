import { FileText, Hammer, HelpCircle } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import type { CreativeCritique } from "@/lib/types";

/**
 * Explains the creative to the owner: what the system built, why it made
 * those choices, and exactly which pieces of their information ended up on
 * the artwork.
 *
 * The critique's `struggled` findings are deliberately NOT rendered here.
 * They still drive regeneration hints and the automated checks, but this
 * panel exists to explain the work, not to hand the owner a list of
 * complaints about a creative they are about to use.
 */
export function CritiqueCard({ critique }: { critique: CreativeCritique }) {
  const { summary, did, why, information } = critique;
  const included = information ?? [];

  return (
    <div className="space-y-4">
      {summary && <p className="text-sm">{summary}</p>}

      {(did.length > 0 || why.length > 0) && (
        <div className="grid gap-4 sm:grid-cols-2">
          <FindingGroup icon={<Hammer className="size-4" />} title="What I made" items={did} />
          <FindingGroup icon={<HelpCircle className="size-4" />} title="Why" items={why} />
        </div>
      )}

      {included.length > 0 && (
        <>
          <Separator />
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-muted-foreground">
              <FileText className="size-4" />
              <span className="text-xs font-medium uppercase tracking-wide">
                Information included
              </span>
            </div>
            <ul className="space-y-1.5">
              {included.map((item, i) => (
                <li key={i} className="flex gap-2 text-sm">
                  <span aria-hidden className="text-muted-foreground">
                    &bull;
                  </span>
                  <span className="min-w-0 break-words">{item}</span>
                </li>
              ))}
            </ul>
            <p className="text-xs text-muted-foreground">
              Every line above is on the creative exactly as you supplied it.
            </p>
          </div>
        </>
      )}
    </div>
  );
}

function FindingGroup({
  icon,
  title,
  items,
}: {
  icon: React.ReactNode;
  title: string;
  items: string[];
}) {
  if (items.length === 0) return null;
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-muted-foreground">
        {icon}
        <span className="text-xs font-medium uppercase tracking-wide">{title}</span>
      </div>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-muted-foreground">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
