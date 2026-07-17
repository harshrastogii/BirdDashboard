import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind class names, resolving conflicts. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Human-readable recording label from a filename/source path. */
export function prettyRecordingName(name: string): string {
  return name
    .replace(/\.(mp3|wav|flac|ogg)$/i, "")
    .replace(/_/g, " ")
    .replace(/\bXC\d+\b/g, "")
    .trim();
}

export function formatConfidence(v: number): string {
  return `${(v * 100).toFixed(0)}%`;
}

export function formatDuration(seconds?: number | null): string {
  if (!seconds && seconds !== 0) return "—";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}
