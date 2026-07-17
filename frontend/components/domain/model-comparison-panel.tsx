"use client";

import { AlertTriangle, CheckCircle2, Download, Globe, MapPin } from "lucide-react";
import {
  Cell, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from "recharts";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { InfoPopover } from "@/components/ui/info-popover";
import { SpeciesBarChart } from "@/components/data/species-bar-chart";
import { useDetections, useMultiSpecies, useSpecies } from "@/lib/api/hooks";
import type { Recording } from "@/lib/api/types";
import { downloadCsv, toCsv } from "@/lib/csv";
import { groundTruthFor, speciesMatches } from "@/lib/ground-truth";
import { formatConfidence } from "@/lib/utils";

export function ModelComparisonPanel({
  recordingId, recording, minConfidence,
}: { recordingId: string; recording?: Recording; minConfidence: number }) {
  const detections = useDetections(recordingId, minConfidence);
  const nt = useMultiSpecies(recordingId);
  const species = useSpecies(200);

  if (nt.isLoading || detections.isLoading || species.isLoading)
    return <Skeleton className="h-72 w-full" />;

  const speciesNames = species.data?.items.map((s) => s.common_name) ?? [];
  const groundTruth = recording ? groundTruthFor(recording.filename, speciesNames) : null;

  // NT Custom Classifier (v5) — from the v5.2 SED events.
  const events = nt.data?.events ?? [];
  const ntTopBySpecies = topByConfidence(events.map((e) => ({ name: e.species, confidence: e.confidence })));
  const ntPrimary = nt.data?.primary_species ?? null;

  // BirdNET v2.4 global baseline.
  const bn = detections.data ?? [];
  const bnTopBySpecies = topByConfidence(bn.map((d) => ({ name: d.common_name, confidence: d.confidence })));

  const ntCorrect = groundTruth
    ? events.some((e) => speciesMatches(e.species, groundTruth)) || speciesMatches(ntPrimary, groundTruth)
    : null;
  const bnCorrect = groundTruth ? bn.some((d) => speciesMatches(d.common_name, groundTruth)) : null;

  return (
    <div className="space-y-6">
      {/* Verdict */}
      <Card>
        <CardContent className="flex flex-wrap items-center gap-x-8 gap-y-3 py-4">
          <div>
            <p className="specimen-label">Actual species</p>
            <p className="text-lg font-semibold">{groundTruth ?? "Unknown"}</p>
          </div>
          <Verdict label="NT Custom Classifier (v5)" correct={ntCorrect} predicted={ntPrimary} />
          <Verdict label="BirdNET v2.4 (global)" correct={bnCorrect} predicted={bnTopBySpecies[0]?.name} />
          <div className="ml-auto">
            <InfoPopover title="How this comparison works">
              <p>
                The <strong>NT Custom Classifier (v5)</strong> — BirdNET-v2.4 embeddings with a custom
                Northern-Territory head, run through the v5.2 sound-event-detection pipeline — is the
                production model.
              </p>
              <p>
                <strong>BirdNET v2.4 (global)</strong> is the baseline. A model is “correct” when it
                detects the recording’s actual species. Global BirdNET routinely misidentifies NT birds;
                the NT model closes that gap.
              </p>
            </InfoPopover>
          </div>
        </CardContent>
      </Card>

      {/* Side-by-side, shared visual language */}
      <div className="grid gap-6 lg:grid-cols-2">
        <ModelCard
          icon={<MapPin className="size-4 text-primary" />}
          title="NT Custom Classifier (v5)" tag="Region-specific · production"
          metrics={[
            ["Events", events.length],
            ["Species", new Set(events.map((e) => e.species)).size],
            // Top (primary) detection confidence — a mean over many SED events
            // reads misleadingly low for a correct call, so show the peak.
            ["Top conf", events.length ? formatConfidence(Math.max(...events.map((e) => e.confidence))) : "—"],
          ]}
          chart={<SpeciesBarChart data={ntTopBySpecies} color="var(--chart-1)" highlight={groundTruth} />}
        />
        <ModelCard
          icon={<Globe className="size-4 text-muted-foreground" />}
          title="BirdNET v2.4" tag="Global baseline"
          metrics={[
            ["Detections", bn.length],
            ["Species", new Set(bn.map((d) => d.common_name)).size],
            ["Top conf", bn.length ? formatConfidence(Math.max(...bn.map((d) => d.confidence))) : "—"],
          ]}
          chart={bnTopBySpecies.length
            ? <SpeciesBarChart data={bnTopBySpecies} color="var(--chart-3)" highlight={groundTruth} />
            : <Empty />}
        />
      </div>

      {/* Temporal confidence, both models */}
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Confidence across the recording</CardTitle>
          <InfoPopover title="Reading this chart">
            <p>Each point is a detection: its time (x) and confidence (y). Compare how consistently each
              model detects across the recording.</p>
          </InfoPopover>
        </CardHeader>
        <CardContent className="grid gap-6 lg:grid-cols-2">
          <TemporalScatter title="NT Custom Classifier (v5)"
            points={events.map((e) => ({ t: e.start, c: e.confidence }))} color="var(--chart-1)" />
          <TemporalScatter title="BirdNET v2.4"
            points={bn.map((d) => ({ t: d.start_seconds, c: d.confidence }))} color="var(--chart-3)" />
        </CardContent>
      </Card>

      {/* Detail tables (progressive disclosure) */}
      <div className="grid gap-6 lg:grid-cols-2">
        <DetailTable
          title="NT (v5) detections" rows={events.map((e) => ({
            start: e.start, end: e.end, species: e.species, confidence: e.confidence,
          }))}
          onExport={() => downloadCsv("nt_v5_detections.csv", toCsv(events.map((e) => ({
            start_s: e.start, end_s: e.end, species: e.species, confidence: e.confidence, primary: e.is_primary,
          }))))}
        />
        <DetailTable
          title="BirdNET detections" rows={bn.map((d) => ({
            start: d.start_seconds, end: d.end_seconds, species: d.common_name, confidence: d.confidence,
          }))}
          onExport={() => downloadCsv("birdnet_detections.csv", toCsv(bn.map((d) => ({
            start_s: d.start_seconds, end_s: d.end_seconds, common_name: d.common_name,
            scientific_name: d.scientific_name, confidence: d.confidence,
          }))))}
        />
      </div>

      {/* Methodology */}
      <Card>
        <CardHeader><CardTitle>Why a region-specific model</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left specimen-label">
                <th className="py-2 pr-4">Model</th><th className="py-2 pr-4">Approach</th>
                <th className="py-2 pr-4">NT species</th><th className="py-2">Best for</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border/60">
                <td className="py-2 pr-4 font-medium">BirdNET v2.4</td>
                <td className="py-2 pr-4">~6,000 global species</td>
                <td className="py-2 pr-4">Often misidentified</td>
                <td className="py-2">Northern-hemisphere birds</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-medium">NT Custom Classifier (v5)</td>
                <td className="py-2 pr-4">BirdNET embeddings + NT head, v5.2 SED</td>
                <td className="py-2 pr-4">
                  <span className="whitespace-nowrap">AUPRC 0.98 · AUROC 0.99</span>{" "}
                  <Badge variant="warning" className="align-middle">Documented · not verified</Badge>
                  <span className="mt-0.5 block text-xs text-muted-foreground">
                    Reproduced held-out estimate: accuracy 0.88. See Model Performance → Research Metrics.
                  </span>
                </td>
                <td className="py-2">Northern Territory birds</td>
              </tr>
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

function topByConfidence(rows: { name: string; confidence: number }[]) {
  const byName = new Map<string, number>();
  for (const r of rows) byName.set(r.name, Math.max(byName.get(r.name) ?? 0, r.confidence));
  return Array.from(byName, ([name, confidence]) => ({ name, confidence }))
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 5);
}

function ModelCard({ icon, title, tag, metrics, chart }: {
  icon: React.ReactNode; title: string; tag: string;
  metrics: [string, React.ReactNode][]; chart: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-center gap-2">
        {icon}<CardTitle>{title}</CardTitle>
        <span className="specimen-label ml-auto">{tag}</span>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-2 text-center">
          {metrics.map(([label, value]) => (
            <div key={label} className="rounded-md border border-border py-2">
              <p className="text-lg font-semibold tabular-nums">{value}</p>
              <p className="specimen-label">{label}</p>
            </div>
          ))}
        </div>
        <div>
          <p className="specimen-label mb-2">Top species by confidence</p>
          {chart}
        </div>
      </CardContent>
    </Card>
  );
}

function TemporalScatter({ title, points, color }: { title: string; points: { t: number; c: number }[]; color: string }) {
  return (
    <div>
      <p className="specimen-label mb-2">{title}</p>
      {points.length ? (
        <ResponsiveContainer width="100%" height={200}>
          <ScatterChart margin={{ left: 0, right: 12, top: 8 }}>
            <XAxis type="number" dataKey="t" name="Time" unit="s" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
            <YAxis type="number" dataKey="c" domain={[0, 1]} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
            <ZAxis range={[50, 50]} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(v: number) => formatConfidence(v as number)} />
            <Scatter data={points}><Cell fill={color} /></Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      ) : <Empty />}
    </div>
  );
}

function DetailTable({ title, rows, onExport }: {
  title: string; rows: { start: number; end: number; species: string; confidence: number }[]; onExport: () => void;
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="text-sm">{title}</CardTitle>
        <Button variant="outline" size="sm" disabled={!rows.length} onClick={onExport}><Download /> CSV</Button>
      </CardHeader>
      <CardContent className="p-0">
        <div className="max-h-64 overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-card">
              <tr className="border-b border-border text-left specimen-label">
                <th className="p-3">Time</th><th className="p-3">Species</th><th className="p-3 text-right">Conf</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-b border-border/60">
                  <td className="p-3 tabular-nums">{r.start.toFixed(1)}–{r.end.toFixed(1)}s</td>
                  <td className="p-3">{r.species}</td>
                  <td className="p-3 text-right tabular-nums">{formatConfidence(r.confidence)}</td>
                </tr>
              ))}
              {!rows.length && <tr><td colSpan={3} className="p-6 text-center text-muted-foreground">No detections.</td></tr>}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function Verdict({ label, correct, predicted }: { label: string; correct: boolean | null; predicted?: string | null }) {
  return (
    <div className="flex items-center gap-2">
      {correct === true && <CheckCircle2 className="size-5 text-success" />}
      {correct === false && <AlertTriangle className="size-5 text-warning" />}
      <div>
        <p className="specimen-label">{label}</p>
        <p className="text-sm">
          {predicted ?? "—"}
          {correct === true && <span className="ml-1.5 text-success">correct</span>}
          {correct === false && <span className="ml-1.5 text-warning">missed</span>}
        </p>
      </div>
    </div>
  );
}

function Empty() {
  return <p className="py-8 text-center text-sm text-muted-foreground">No detections above threshold.</p>;
}
