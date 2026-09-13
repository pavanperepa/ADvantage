import Link from "next/link";
import { Megaphone } from "lucide-react";

export function SiteHeader() {
  return (
    <header className="border-b border-border/70">
      <div className="mx-auto flex h-16 w-full max-w-3xl items-center px-4 sm:h-18 sm:px-6">
        <Link
          href="/"
          aria-label="ADvantage home"
          className="flex items-center gap-2.5 text-lg font-semibold tracking-tight sm:text-xl"
        >
          <Megaphone
            className="size-6 shrink-0 text-primary sm:size-7"
            strokeWidth={2.25}
            aria-hidden
          />
          <span>ADvantage</span>
        </Link>
      </div>
    </header>
  );
}
