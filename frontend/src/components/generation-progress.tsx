"use client";

import * as React from "react";
import { motion } from "motion/react";
import { Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import type { CreativeFormat } from "@/lib/types";

/**
 * There is no streaming/progress endpoint -- `POST /api/campaigns` blocks
 * until the run finishes (~2-5s for a poster, ~30-100s for a reel). This
 * fakes a progress bar that eases toward (but never quite reaches) 100%,
 * so the wait reads as "working" rather than "stuck", and pairs it with
 * copy that sets real expectations for how long a reel can take.
 */
export function GenerationProgress({ format }: { format: CreativeFormat }) {
  const [elapsedMs, setElapsedMs] = React.useState(0);

  React.useEffect(() => {
    const start = Date.now();
    const id = window.setInterval(() => setElapsedMs(Date.now() - start), 200);
    return () => window.clearInterval(id);
  }, []);

  // Eases toward 92%, calibrated so a poster (~a few seconds) reads as
  // "almost there" quickly, while a reel (up to ~100s) keeps crawling
  // forward for the whole wait instead of stalling early.
  const horizonMs = format === "reel" ? 45_000 : 3_000;
  const progress = 92 * (1 - Math.exp(-elapsedMs / horizonMs));
  const elapsedSeconds = Math.floor(elapsedMs / 1000);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className="flex flex-col items-center gap-4 rounded-xl border border-border/70 bg-card px-6 py-10 text-center"
    >
      <Loader2 className="size-6 animate-spin text-primary" aria-hidden />
      <div className="space-y-1.5">
        <p className="text-sm font-medium">
          {format === "reel" ? "Rendering your reel…" : "Generating your poster…"}
        </p>
        <p className="max-w-sm text-sm text-muted-foreground">
          {format === "reel"
            ? "This usually takes under two minutes — we're stitching your footage, adding copy, and rendering the final video."
            : "This usually only takes a few seconds."}
        </p>
      </div>
      <div className="w-full max-w-xs space-y-1.5">
        <Progress value={progress} />
        <p className="font-mono text-xs text-muted-foreground">{elapsedSeconds}s elapsed</p>
      </div>
    </motion.div>
  );
}
