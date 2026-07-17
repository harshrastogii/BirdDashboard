"use client";

import { Download, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/data/stat-card";
import { DetectionTimeline } from "@/components/domain/detection-timeline";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/data/empty-state";
import { useMultiSpecies } from "@/lib/api/hooks";
import { downloadCsv, toCsv } from "@/lib/csv";
import { formatConfidence } from "@/lib/utils";

export function MultiSpeciesPanel({ recordingId }: { recordingId: string }) {
  const { data, isLoading, isError } = useMultiSpecies(recordingId);

  if (isLoading)
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">Running sliding-window multi-species detection…</p>
        <Skeleton className="h-56 w-full" />
      </div>
    );
  if (isError) return <EmptyState icon={Sparkles} title="Detection failed" description="Could not run multi-species detection." />;
  if (!data || data.events.length === 0)
    return <EmptyState icon={Sparkles} title="No multi-species events" description="No secondary species detected above threshold." />;

  const timelineData = data.events.map((e) => ({
    recording_id: recordingId,
    start_seconds: e.start, end_seconds: e.end,
    common_name: e.species, scientific_name: null,
    confidence: e.confidence, source: "multi_species",
  }));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Duration" value={`${data.duration_seconds.toFixed(1)}s`} />
        <StatCard label="Primary species" value={<span className="text-lg">{data.primary_species ?? "—"}</span>} />
        <StatCard label="Total events" value={data.num_events} />
        <StatCard label="Unique species" value={data.unique_species} />
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Detection timeline</CardTitle>
          {data.cached && <Badge variant="secondary">cached</Badge>}
        </CardHeader>
        <CardContent><DetectionTimeline detections={timelineData} /></CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Detected events</CardTitle>
          <Button
            variant="outline" size="sm"
            onClick={() =>
              downloadCsv("multi_species_events.csv",
                toCsv(data.events.map((e) => ({
                  start_s: e.start, end_s: e.end, duration_s: +(e.end - e.start).toFixed(2),
                  species: e.species, confidence: e.confidence, primary: e.is_primary,
                }))))
            }
          >
            <Download /> CSV
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          <div className="max-h-80 overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-card">
                <tr className="border-b border-border text-left specimen-label">
                  <th className="p-3">Time</th><th className="p-3">Duration</th>
                  <th className="p-3">Species</th><th className="p-3 text-right">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {data.events.map((e, i) => (
                  <tr key={i} className="border-b border-border/60">
                    <td className="p-3 tabular-nums">{e.start.toFixed(1)}–{e.end.toFixed(1)}s</td>
                    <td className="p-3 tabular-nums">{(e.end - e.start).toFixed(1)}s</td>
                    <td className="p-3">{e.is_primary && <span className="mr-1">⭐</span>}{e.species}</td>
                    <td className="p-3 text-right tabular-nums">{formatConfidence(e.confidence)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
