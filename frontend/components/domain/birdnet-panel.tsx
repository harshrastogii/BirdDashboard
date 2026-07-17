"use client";

import { Download } from "lucide-react";
import {
  Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/data/stat-card";
import { DetectionTimeline } from "@/components/domain/detection-timeline";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/data/empty-state";
import { useDetections } from "@/lib/api/hooks";
import { downloadCsv, toCsv } from "@/lib/csv";
import { formatConfidence } from "@/lib/utils";

export function BirdnetPanel({ recordingId, minConfidence }: { recordingId: string; minConfidence: number }) {
  const { data, isLoading } = useDetections(recordingId, minConfidence);

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!data || data.length === 0)
    return <EmptyState title="No BirdNET detections above threshold" description="Lower the confidence filter to see more." />;

  const species = Array.from(new Set(data.map((d) => d.common_name)));
  const avg = data.reduce((s, d) => s + d.confidence, 0) / data.length;
  const top = data.reduce((a, b) => (b.confidence > a.confidence ? b : a));

  // Max confidence per species (top 10) for the bar chart.
  const byspecies = species
    .map((name) => ({
      name,
      confidence: Math.max(...data.filter((d) => d.common_name === name).map((d) => d.confidence)),
    }))
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 10);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total detections" value={data.length} />
        <StatCard label="Unique species" value={species.length} />
        <StatCard label="Avg confidence" value={formatConfidence(avg)} />
        <StatCard label="Top species" value={<span className="text-lg">{top.common_name}</span>} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Detection timeline</CardTitle></CardHeader>
          <CardContent><DetectionTimeline detections={data} /></CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Species by confidence</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={Math.max(220, byspecies.length * 30)}>
              <BarChart data={byspecies} layout="vertical" margin={{ left: 8, right: 16 }}>
                <XAxis type="number" domain={[0, 1]} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                <Tooltip formatter={(v: number) => formatConfidence(v)} />
                <Bar dataKey="confidence" radius={[0, 4, 4, 0]}>
                  {byspecies.map((_, i) => <Cell key={i} fill="var(--primary)" />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Detections</CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              downloadCsv(
                "birdnet_detections.csv",
                toCsv(data.map((d) => ({
                  start_s: d.start_seconds, end_s: d.end_seconds,
                  common_name: d.common_name, scientific_name: d.scientific_name,
                  confidence: d.confidence,
                }))),
              )
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
                  <th className="p-3">Start</th><th className="p-3">End</th>
                  <th className="p-3">Species</th><th className="p-3 text-right">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {data.map((d, i) => (
                  <tr key={i} className="border-b border-border/60">
                    <td className="p-3 tabular-nums">{d.start_seconds.toFixed(1)}s</td>
                    <td className="p-3 tabular-nums">{d.end_seconds.toFixed(1)}s</td>
                    <td className="p-3">
                      {d.common_name}
                      {d.scientific_name && <span className="ml-2 italic text-muted-foreground">{d.scientific_name}</span>}
                    </td>
                    <td className="p-3 text-right tabular-nums">{formatConfidence(d.confidence)}</td>
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
