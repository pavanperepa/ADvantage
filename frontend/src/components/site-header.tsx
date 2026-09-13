import Link from "next/link";
import { Megaphone } from "lucide-react";

export function SiteHeader() {
  return (
    <header className="border-b border-border/70">
      <div className="mx-auto flex h-14 w-full max-w-3xl items-center px-4 sm:px-6">
        <Link
          href="/"
          className="flex items-center gap-2 text-sm font-medium tracking-tight"
        >
          <Megaphone className="size-4 text-primary" aria-hidden />
          <span>ADvantage</span>
        </Link>
      </div>
    </header>
  );
}
