"use client";

import { AlertTriangle, type LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

export function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon?: LucideIcon;
  title: string;
  description?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-16 text-center">
      {Icon && <Icon className="size-8 text-muted-foreground" />}
      <p className="mt-3 font-medium">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>}
    </div>
  );
}

/** Consistent error state for failed data loads, with an optional retry. */
export function ErrorState({
  title = "Couldn’t load this",
  description = "The data failed to load. Check that the API is running, then try again.",
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center rounded-lg border border-dashed border-destructive/40 py-16 text-center"
    >
      <AlertTriangle className="size-8 text-destructive" />
      <p className="mt-3 font-medium">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function SampleDataNote({ children }: { children?: React.ReactNode }) {
  return (
    <p className="text-xs italic text-muted-foreground">
      {children ??
        "Site associations shown are illustrative sample deployment data; per-recording GPS is pending the Xeno-canto longitude fix."}
    </p>
  );
}
