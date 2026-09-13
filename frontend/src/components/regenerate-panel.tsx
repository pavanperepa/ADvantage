"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Loader2, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ApiError, fetchPalettes, regenerateCampaign } from "@/lib/api";
import type { CreativeFormat, Palette } from "@/lib/types";

const POSTER_STYLES = [
  { value: "photoreal", label: "Photoreal" },
  { value: "bold_graphic", label: "Bold graphic" },
  { value: "warm_lifestyle", label: "Warm lifestyle" },
  { value: "premium_minimal", label: "Premium minimal" },
];

const REEL_FEELS = [
  { value: "high_energy", label: "High energy" },
  { value: "cinematic", label: "Cinematic" },
  { value: "warm_testimonial", label: "Warm testimonial" },
  { value: "urgent_offer", label: "Urgent offer" },
  { value: "clean_explainer", label: "Clean explainer" },
];

/**
 * Regenerate this creative with extra direction and a different colour scheme.
 *
 * A regenerate produces a NEW run rather than overwriting this one, so the
 * owner can try a variation without losing the version they already have --
 * hence navigating to the new id on success.
 */
export function RegeneratePanel({
  runId,
  format,
}: {
  runId: string;
  format: CreativeFormat;
}) {
  const router = useRouter();

  const [notes, setNotes] = React.useState("");
  const [palette, setPalette] = React.useState<string | null>(null);
  const [variant, setVariant] = React.useState<string | null>(null);
  const [palettes, setPalettes] = React.useState<Palette[]>([]);
  const [running, setRunning] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    fetchPalettes()
      .then((data) => {
        if (!cancelled) setPalettes(data);
      })
      .catch(() => {
        // Swatches are a convenience, not a requirement -- regenerating with
        // notes alone must still work if this call fails.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const variants = format === "poster" ? POSTER_STYLES : REEL_FEELS;
  const variantLabel = format === "poster" ? "Art style" : "Reel feel";

  async function handleRegenerate() {
    if (running) return;
    setRunning(true);
    setError(null);
    try {
      const next = await regenerateCampaign(runId, {
        ...(notes.trim() ? { refinement_notes: notes.trim() } : {}),
        ...(palette ? { palette } : {}),
        ...(variant && format === "poster" ? { poster_style: variant } : {}),
        ...(variant && format === "reel" ? { reel_feel: variant } : {}),
      });
      router.push(`/campaigns/${next.id}`);
    } catch (err) {
      setRunning(false);
      setError(
        err instanceof ApiError
          ? err.message
          : "Couldn't reach the backend. Is it running?",
      );
    }
  }

  return (
    <div className="space-y-5">
      <div className="space-y-1.5">
        <Label htmlFor="refinement">What should change?</Label>
        <Textarea
          id="refinement"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="make it less empty, bigger headline, show more players on the field"
          disabled={running}
        />
        <p className="text-xs text-muted-foreground">
          This steers the artwork only. Your copy, phone number, and link stay exactly
          as you entered them.
        </p>
      </div>

      {palettes.length > 0 && (
        <div className="space-y-2">
          <Label>Colour scheme</Label>
          <div className="flex flex-wrap gap-2">
            {palettes.map((p) => (
              <button
                key={p.value}
                type="button"
                onClick={() => setPalette(palette === p.value ? null : p.value)}
                disabled={running}
                className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors disabled:opacity-50 ${
                  palette === p.value
                    ? "border-primary bg-accent"
                    : "border-input hover:bg-accent/50"
                }`}
              >
                <span className="flex gap-0.5">
                  <span
                    className="size-3.5 rounded-sm ring-1 ring-black/10"
                    style={{ backgroundColor: p.primary }}
                  />
                  <span
                    className="size-3.5 rounded-sm ring-1 ring-black/10"
                    style={{ backgroundColor: p.accent }}
                  />
                  <span
                    className="size-3.5 rounded-sm ring-1 ring-black/10"
                    style={{ backgroundColor: p.ink }}
                  />
                </span>
                {p.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-2">
        <Label>{variantLabel}</Label>
        <div className="flex flex-wrap gap-2">
          {variants.map((v) => (
            <button
              key={v.value}
              type="button"
              onClick={() => setVariant(variant === v.value ? null : v.value)}
              disabled={running}
              className={`rounded-md border px-3 py-1.5 text-sm transition-colors disabled:opacity-50 ${
                variant === v.value
                  ? "border-primary bg-accent"
                  : "border-input hover:bg-accent/50"
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={handleRegenerate} disabled={running}>
          {running ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Regenerating…
            </>
          ) : (
            <>
              <RefreshCw className="size-4" />
              Regenerate
            </>
          )}
        </Button>
        <p className="text-xs text-muted-foreground">
          {format === "reel"
            ? "A reel takes a minute or two to re-render."
            : "A poster takes a few seconds."}{" "}
          This version is kept — you&apos;ll get a new one.
        </p>
      </div>
    </div>
  );
}
