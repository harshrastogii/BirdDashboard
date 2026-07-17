"use client";

import { Play, Settings2, Sparkles, Table2, Tag, Download } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/data/stat-card";
import { InfoPopover } from "@/components/ui/info-popover";
import { DetectionTimeline } from "@/components/domain/detection-timeline";
import { ListenLabelPanel } from "@/components/domain/listen-label-panel";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/data/empty-state";
import { useMultiSpecies, type MultiSpeciesParams } from "@/lib/api/hooks";
import { downloadCsv, toCsv } from "@/lib/csv";
import { cn, formatConfidence } from "@/lib/utils";

const DEFAULTS: Required<Omit<MultiSpeciesParams, "force">> = {
  primary_conf: 0.5, secondary_conf: 0.25, sensitivity: 1.25, overlap: 2.0, top_k: 3, suppress_primary: false,
};

export function EventsLabelling({ recordingId }: { recordingId: string }) {
  const [params, setParams] = useState(DEFAULTS);
  const [applied, setApplied] = useState<MultiSpeciesParams | null>(null); // null = cached default
  const [view, setView] = useState<"interactive" | "compact">("interactive");
  const [showParams, setShowParams] = useState(false);

  const { data, isLoading, isError, isFetching } = useMultiSpecies(recordingId, applied);

  const run = () => setApplied({ ...params, force: true });

  return (
    <div className="space-y-6">
      {/* Controls bar */}
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="outline" size="sm" onClick={() => setShowParams((v) => !v)}>
          <Settings2 /> Detection parameters
        </Button>
        <Button size="sm" onClick={run} disabled={isFetching}>
          <Play /> {isFetching ? "Running…" : "Run detection"}
        </Button>
        <InfoPopover title="Multi-species detection (v5.2)">
          <p>The <strong>NT Custom Classifier (v5)</strong> is run in a sliding window with a dual-threshold
            scheme: a higher bar for the dominant species, a lower bar for background species. Tune the
            parameters and re-run to explore sensitivity.</p>
        </InfoPopover>
        <div className="ml-auto flex rounded-lg border border-border p-1">
          <ToggleBtn active={view === "interactive"} onClick={() => setView("interactive")}><Tag className="size-3.5" /> Listen &amp; Label</ToggleBtn>
          <ToggleBtn active={view === "compact"} onClick={() => setView("compact")}><Table2 className="size-3.5" /> Compact</ToggleBtn>
        </div>
      </div>

      {showParams && (
        <Card>
          <CardContent className="grid gap-4 py-4 sm:grid-cols-2 lg:grid-cols-3">
            <Range label="Primary threshold" min={0.3} max={0.95} step={0.05} value={params.primary_conf}
              onChange={(v) => setParams({ ...params, primary_conf: v })} />
            <Range label="Secondary threshold" min={0.1} max={0.7} step={0.05} value={params.secondary_conf}
              onChange={(v) => setParams({ ...params, secondary_conf: v })} />
            <Range label="BirdNET sensitivity" min={0.75} max={1.5} step={0.05} value={params.sensitivity}
              onChange={(v) => setParams({ ...params, sensitivity: v })} />
            <Range label="Window overlap (s)" min={0} max={2.9} step={0.5} value={params.overlap}
              onChange={(v) => setParams({ ...params, overlap: v })} />
            <Range label="Max secondaries" min={1} max={5} step={1} value={params.top_k}
              onChange={(v) => setParams({ ...params, top_k: v })} />
            <label className="flex items-center gap-2 self-end text-sm">
              <input type="checkbox" checked={params.suppress_primary}
                onChange={(e) => setParams({ ...params, suppress_primary: e.target.checked })} />
              Hide primary species
            </label>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">Running sliding-window multi-species detection…</p>
          <Skeleton className="h-56 w-full" />
        </div>
      ) : isError ? (
        <EmptyState icon={Sparkles} title="Detection failed" description="Could not run multi-species detection." />
      ) : !data || data.events.length === 0 ? (
        <EmptyState icon={Sparkles} title="No multi-species events" description="No secondary species detected above threshold. Lower the secondary threshold and re-run." />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Duration" value={`${data.duration_seconds.toFixed(1)}s`} />
            <StatCard label="Primary species" value={<span className="text-lg">{data.primary_species ?? "—"}</span>} />
            <StatCard label="Total events" value={data.num_events} />
            <StatCard label="Unique species" value={data.unique_species} />
          </div>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>Detection timeline</CardTitle>
              {data.cached && !applied && <Badge variant="secondary">cached</Badge>}
            </CardHeader>
            <CardContent>
              <DetectionTimeline detections={data.events.map((e) => ({
                recording_id: recordingId, start_seconds: e.start, end_seconds: e.end,
                common_name: e.species, scientific_name: null, confidence: e.confidence, source: "v5",
              }))} />
            </CardContent>
          </Card>

          {view === "compact" ? (
            <Card>
              <CardHeader className="flex-row items-center justify-between">
                <CardTitle>Events</CardTitle>
                <Button variant="outline" size="sm" onClick={() => downloadCsv("multi_species_events.csv",
                  toCsv(data.events.map((e) => ({
                    start_s: e.start, end_s: e.end, duration_s: +(e.end - e.start).toFixed(2),
                    species: e.species, confidence: e.confidence, primary: e.is_primary,
                  }))))}>
                  <Download /> CSV
                </Button>
              </CardHeader>
              <CardContent className="p-0">
                <div className="max-h-96 overflow-auto">
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
          ) : (
            <div>
              <h3 className="mb-3 text-base font-semibold">Listen &amp; Label</h3>
              <ListenLabelPanel recordingId={recordingId} appliedParams={applied} />
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ToggleBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick}
      className={cn("inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
        active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground")}>
      {children}
    </button>
  );
}

function Range({ label, min, max, step, value, onChange }: {
  label: string; min: number; max: number; step: number; value: number; onChange: (v: number) => void;
}) {
  return (
    <label className="text-sm">
      <span className="specimen-label mb-1 flex items-center justify-between">
        {label}<span className="tabular-nums">{value}</span>
      </span>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-[var(--primary)]" />
    </label>
  );
}
