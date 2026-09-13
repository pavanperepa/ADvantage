import type { CampaignArtifact } from "@/lib/types";

export function ArtifactViewer({
  artifact,
  src,
}: {
  artifact: CampaignArtifact;
  src: string;
}) {
  return (
    <div
      className="mx-auto w-full max-w-sm overflow-hidden rounded-lg bg-muted ring-1 ring-foreground/10"
      style={{ aspectRatio: `${artifact.width} / ${artifact.height}` }}
    >
      {artifact.format === "poster" ? (
        // eslint-disable-next-line @next/next/no-img-element -- external, dynamic API-served file; next/image would need a remote-pattern config for a variable local backend URL.
        <img
          src={src}
          alt="Generated poster creative"
          width={artifact.width}
          height={artifact.height}
          className="size-full object-cover"
        />
      ) : (
        <video
          src={src}
          controls
          loop
          playsInline
          className="size-full object-cover"
        />
      )}
    </div>
  );
}
