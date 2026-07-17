"use client";

import { Info } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/** Lightweight click popover — the modern equivalent of Streamlit's
 *  explanatory expanders, without cluttering the layout. */
export function InfoPopover({ title, children }: { title?: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  return (
    <div ref={ref} className="relative inline-block">
      <button
        type="button"
        aria-label={title ? `About ${title}` : "More information"}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "inline-grid size-6 place-items-center rounded-full text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground",
          open && "bg-secondary text-foreground",
        )}
      >
        <Info className="size-4" />
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-80 max-w-[80vw] rounded-lg border border-border bg-popover p-4 text-sm shadow-lg">
          {title && <p className="mb-1.5 font-semibold">{title}</p>}
          <div className="space-y-2 text-muted-foreground [&_strong]:text-foreground">{children}</div>
        </div>
      )}
    </div>
  );
}
