"use client";

import type { Detection } from "@/lib/api/types";
import { formatConfidence } from "@/lib/utils";

/** Lightweight SVG-free timeline: detections plotted as bars over recording time. */
export function DetectionTimeline({ detections }: { detections: Detection[] }) {
  if (detections.length === 0) {
    return <p className="text-sm text-muted-foreground">No detections above the confidence threshold.</p>;
  }

  const maxTime = Math.max(...detections.map((d) => d.end_seconds), 1);
  // Group by species for lanes.
  const species = Array.from(new Set(detections.map((d) => d.common_name)));

  return (
    <div className="space-y-2">
      {species.map((name) => {
        const lane = detections.filter((d) => d.common_name === name);
        return (
          <div key={name} className="grid grid-cols-[9rem_1fr] items-center gap-3">
            <span className="truncate text-sm">{name}</span>
            <div className="relative h-6 rounded bg-secondary">
              {lane.map((d, i) => (
                <div
                  key={i}
                  title={`${d.start_seconds.toFixed(1)}–${d.end_seconds.toFixed(1)}s · ${formatConfidence(d.confidence)}`}
                  className="absolute top-0 h-full rounded bg-primary"
                  style={{
                    left: `${(d.start_seconds / maxTime) * 100}%`,
                    width: `${Math.max(((d.end_seconds - d.start_seconds) / maxTime) * 100, 1.2)}%`,
                    opacity: 0.35 + d.confidence * 0.65,
                  }}
                />
              ))}
            </div>
          </div>
        );
      })}
      <div className="grid grid-cols-[9rem_1fr] gap-3 pt-1">
        <span />
        <div className="flex justify-between specimen-label">
          <span>0s</span>
          <span>{maxTime.toFixed(0)}s</span>
        </div>
      </div>
    </div>
  );
}
