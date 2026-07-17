"use client";

import Link from "next/link";
import { Telescope } from "lucide-react";

import { ThemeToggle } from "./theme-toggle";
import { AboutDialog } from "./about-dialog";
import { APP_NAME, APP_TAGLINE } from "@/lib/config";

export function TopBar() {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border bg-background/85 px-4 backdrop-blur md:px-6">
      {/* Brand shown on mobile (sidebar hidden). */}
      <Link href="/dashboard" className="flex items-center gap-2 md:hidden">
        <span className="grid place-items-center size-8 rounded-md bg-primary text-primary-foreground">
          <Telescope className="size-5" />
        </span>
        <span className="font-semibold">{APP_NAME}</span>
      </Link>

      {/* Tagline as quiet context on desktop (the sidebar carries the brand). */}
      <p className="hidden text-sm text-muted-foreground md:block">{APP_TAGLINE}</p>

      <div className="ml-auto flex items-center gap-1">
        <AboutDialog />
        <ThemeToggle />
      </div>
    </header>
  );
}
