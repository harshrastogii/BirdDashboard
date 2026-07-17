"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { InfoPopover } from "@/components/ui/info-popover";
import { SpectrogramViewer } from "@/components/spectrogram/spectrogram-viewer";
import { Skeleton } from "@/components/ui/skeleton";
import { useDetections, useSpecies } from "@/lib/api/hooks";
import type { Recording } from "@/lib/api/types";
import { groundTruthFor } from "@/lib/ground-truth";
import { formatDuration } from "@/lib/utils";

export function RecordingOverview({
  recording, recordingId, minConfidence,
}: { recording?: Recording; recordingId: string; minConfidence: number }) {
  const detections = useDetections(recordingId, minConfidence);
  const species = useSpecies(200);

  const speciesNames = species.data?.items.map((s) => s.common_name) ?? [];
  const groundTruth = recording ? groundTruthFor(recording.filename, speciesNames) : null;
  const conservation = species.data?.items.find((s) => s.common_name === groundTruth)?.conservation_status;
  const scientific = species.data?.items.find((s) => s.common_name === groundTruth)?.scientific_name;

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Mel spectrogram</CardTitle>
          <InfoPopover title="What is a spectrogram?">
            <p>A visual fingerprint of sound: <strong>time</strong> runs left-to-right, <strong>frequency</strong>
              (pitch) bottom-to-top, and brightness shows <strong>loudness</strong>. Each species produces a
              distinctive pattern researchers use to identify calls.</p>
          </InfoPopover>
        </CardHeader>
        <CardContent><SpectrogramViewer recordingId={recordingId} /></CardContent>
      </Card>

      <Card className="h-fit">
        <CardHeader><CardTitle>Specimen record</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm">
          {!recording ? (
            <Skeleton className="h-48 w-full" />
          ) : (
            <dl className="space-y-3">
              {groundTruth && (
                <div className="pb-1">
                  <p className="specimen-label">Species</p>
                  <p className="font-medium">{groundTruth}</p>
                  {scientific && <p className="text-xs italic text-muted-foreground">{scientific}</p>}
                  {conservation && conservation !== "Least Concern" && (
                    <Badge variant="warning" className="mt-1">{conservation}</Badge>
                  )}
                </div>
              )}
              <Meta label="File" value={recording.filename} mono />
              <Meta label="Format" value={recording.media_type} />
              <Meta label="Duration" value={formatDuration(recording.duration_seconds)} />
              <Meta label="Size" value={recording.size_bytes ? `${Math.round(recording.size_bytes / 1024)} KB` : "—"} />
              <Meta label="BirdNET detections" value={detections.data ? String(detections.data.length) : "—"} />
            </dl>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Meta({ label, value, mono }: { label: string; value?: string | null; mono?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border pb-2 last:border-0">
      <dt className="specimen-label">{label}</dt>
      <dd className={mono ? "text-right font-mono text-xs" : "text-right"}>{value ?? "—"}</dd>
    </div>
  );
}
