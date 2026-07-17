"use client";

import { Download } from "lucide-react";
import {
  Bar, BarChart, Cell, ResponsiveContainer, Scatter, ScatterChart, Tooltip,
  XAxis, YAxis, ZAxis,
} from "recharts";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/data/stat-card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/data/empty-state";
import { useNtPredictions } from "@/lib/api/hooks";
import { downloadCsv, toCsv } from "@/lib/csv";
import { formatConfidence } from "@/lib/utils";

const CHART = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];

export function NtModelPanel({ recordingId, minConfidence }: { recordingId: string; minConfidence: number }) {
  const { data, isLoading, isError } = useNtPredictions(recordingId);

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (isError) return <EmptyState title="NT model unavailable" description="Could not compute NT CNN predictions." />;
  if (!data) return null;

  const top1All = data.predictions.filter((p) => p.rank === 1);
  const top1 = top1All.filter((p) => p.confidence >= minConfidence);

  if (top1All.length === 0)
    return <EmptyState title="No NT predictions" description="This recording produced no non-silent segments." />;

  const uniqueSpecies = new Set(top1.map((p) => p.species)).size;
  const avg = top1.length ? top1.reduce((s, p) => s + p.confidence, 0) / top1.length : 0;
  const best = top1All.reduce((a, b) => (b.confidence > a.confidence ? b : a));
  const bestSegment = data.predictions
    .filter((p) => p.start_seconds === best.start_seconds)
    .sort((a, b) => a.rank - b.rank);

  const speciesColors = new Map<string, string>();
  Array.from(new Set(top1.map((p) => p.species))).forEach((s, i) =>
    speciesColors.set(s, CHART[i % CHART.length]),
  );

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Segments analysed" value={top1.length} hint="Above confidence filter" />
        <StatCard label="Unique species" value={uniqueSpecies} />
        <StatCard label="Avg confidence" value={formatConfidence(avg)} />
        <StatCard label="Top species" value={<span className="text-lg">{best.species}</span>} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Top-5 — highest-confidence segment</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={bestSegment} layout="vertical" margin={{ left: 8, right: 16 }}>
                <XAxis type="number" domain={[0, 1]} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                <YAxis type="category" dataKey="species" width={130} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                <Tooltip formatter={(v: number) => formatConfidence(v)} />
                <Bar dataKey="confidence" radius={[0, 4, 4, 0]}>
                  {bestSegment.map((_, i) => <Cell key={i} fill={CHART[i % CHART.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Confidence across segments</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={230}>
              <ScatterChart margin={{ left: 0, right: 16, top: 8 }}>
                <XAxis type="number" dataKey="start_seconds" name="Time" unit="s" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                <YAxis type="number" dataKey="confidence" domain={[0, 1]} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                <ZAxis range={[60, 60]} />
                <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(v: number) => formatConfidence(v as number)} />
                <Scatter data={top1}>
                  {top1.map((p, i) => <Cell key={i} fill={speciesColors.get(p.species) ?? "var(--primary)"} />)}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>All segment predictions (Top-1)</CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              downloadCsv("nt_model_predictions.csv",
                toCsv(top1All.map((p) => ({
                  start_s: p.start_seconds, end_s: p.end_seconds,
                  species: p.species, confidence: p.confidence,
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
                  <th className="p-3">Start</th><th className="p-3">End</th>
                  <th className="p-3">Species</th><th className="p-3 text-right">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {top1.map((p, i) => (
                  <tr key={i} className="border-b border-border/60">
                    <td className="p-3 tabular-nums">{p.start_seconds.toFixed(1)}s</td>
                    <td className="p-3 tabular-nums">{p.end_seconds.toFixed(1)}s</td>
                    <td className="p-3">{p.species}</td>
                    <td className="p-3 text-right tabular-nums">{formatConfidence(p.confidence)}</td>
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
