"use client";

import { Download } from "lucide-react";
import { useState } from "react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/data/stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/data/empty-state";
import { InfoPopover } from "@/components/ui/info-popover";
import { useBiodiversity } from "@/lib/api/hooks";
import { downloadCsv, toCsv } from "@/lib/csv";

export default function BiodiversityPage() {
  const [minConf, setMinConf] = useState(0.25);
  const { data, isLoading, isError, refetch } = useBiodiversity(minConf);

  const chartData = (data?.per_recording ?? [])
    .slice()
    .sort((a, b) => b.total_detections - a.total_detections)
    .slice(0, 12);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Biodiversity"
        description="Shannon and Simpson diversity indices and species richness across the recording library — ready for environmental impact assessment and conservation reporting."
        actions={
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              Min confidence
              <input type="range" min={0} max={0.9} step={0.05} value={minConf}
                onChange={(e) => setMinConf(Number(e.target.value))} className="accent-[var(--primary)]" />
              <span className="w-9 tabular-nums">{(minConf * 100).toFixed(0)}%</span>
            </label>
            <InfoPopover title="Biodiversity indices">
              <p><strong>Species richness</strong> — the raw count of distinct species.</p>
              <p><strong>Shannon (H′)</strong> — diversity accounting for abundance; higher means more diverse
                (used in environmental impact assessments).</p>
              <p><strong>Simpson (D)</strong> — probability two random detections are different species; closer
                to 1 means more even.</p>
            </InfoPopover>
          </div>
        }
      />

      {isError && <ErrorState onRetry={() => refetch()} />}

      {isLoading && <Skeleton className="h-32 w-full" />}

      {data && data.per_recording.length === 0 && (
        <EmptyState title="No detections above threshold" description="Lower the confidence filter." />
      )}

      {data && data.per_recording.length > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard label="Overall species richness" value={data.overall_richness} hint="Unique species across all recordings" />
            <StatCard label="Shannon Index (H′)" value={data.overall_shannon.toFixed(3)} hint="Higher = more diverse" />
            <StatCard label="Simpson Index (D)" value={data.overall_simpson.toFixed(3)} hint="Closer to 1 = more even" />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Detections per recording</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={Math.max(240, chartData.length * 26)}>
                  <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
                    <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                    <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 10 }} stroke="var(--muted-foreground)" />
                    <Tooltip />
                    <Bar dataKey="total_detections" radius={[0, 4, 4, 0]}>
                      {chartData.map((_, i) => <Cell key={i} fill="var(--primary)" />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <p className="mt-2 text-[11px] text-muted-foreground">Total BirdNET detections per recording (top 12 by count, above the confidence threshold).</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Species richness per recording</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={Math.max(240, chartData.length * 26)}>
                  <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
                    <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                    <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 10 }} stroke="var(--muted-foreground)" />
                    <Tooltip />
                    <Bar dataKey="species_richness" radius={[0, 4, 4, 0]}>
                      {chartData.map((_, i) => <Cell key={i} fill="var(--chart-2)" />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <p className="mt-2 text-[11px] text-muted-foreground">Distinct species detected per recording (same recordings as at left).</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>Per-recording metrics</CardTitle>
              <Button variant="outline" size="sm"
                onClick={() => downloadCsv("biodiversity_metrics.csv", toCsv(data.per_recording as unknown as Record<string, unknown>[]))}>
                <Download /> CSV
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="max-h-96 overflow-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-card">
                    <tr className="border-b border-border text-left specimen-label">
                      <th className="p-3">Recording</th><th className="p-3 text-right">Richness</th>
                      <th className="p-3 text-right">Shannon</th><th className="p-3 text-right">Simpson</th>
                      <th className="p-3 text-right">Detections</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.per_recording.map((r, i) => (
                      <tr key={i} className="border-b border-border/60">
                        <td className="p-3">{r.name}</td>
                        <td className="p-3 text-right tabular-nums">{r.species_richness}</td>
                        <td className="p-3 text-right tabular-nums">{r.shannon_index.toFixed(3)}</td>
                        <td className="p-3 text-right tabular-nums">{r.simpson_index.toFixed(3)}</td>
                        <td className="p-3 text-right tabular-nums">{r.total_detections}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
