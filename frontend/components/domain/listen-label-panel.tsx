"use client";

import { Check, ChevronLeft, ChevronRight, Download, HelpCircle, Pause, Play, RotateCcw, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/data/stat-card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/data/empty-state";
import { useMultiSpecies, type MultiSpeciesParams } from "@/lib/api/hooks";
import { useSegmentPlayer } from "@/lib/hooks/use-segment-player";
import { downloadCsv, toCsv } from "@/lib/csv";
import { API_BASE } from "@/lib/config";
import { cn, formatConfidence } from "@/lib/utils";

type Label = "confirm" | "reject" | "uncertain";
const PER_PAGE = 8;

export function ListenLabelPanel({
  recordingId, appliedParams,
}: { recordingId: string; appliedParams?: MultiSpeciesParams | null }) {
  const { data, isLoading } = useMultiSpecies(recordingId, appliedParams);
  const storageKey = `ao-labels-${recordingId}`;

  const [labels, setLabels] = useState<Record<number, Label>>({});
  const [annotator, setAnnotator] = useState("");
  const [page, setPage] = useState(0);
  const { play, playingKey } = useSegmentPlayer(`${API_BASE}/api/v1/recordings/${recordingId}/audio`);

  // Load persisted labels + annotator.
  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) setLabels(JSON.parse(raw));
      setAnnotator(localStorage.getItem("ao-annotator") ?? "");
    } catch {}
  }, [storageKey]);

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(labels));
  }, [labels, storageKey]);

  const events = useMemo(() => data?.events ?? [], [data]);
  const counts = useMemo(() => {
    const vals = Object.values(labels);
    return {
      labelled: vals.length,
      confirm: vals.filter((v) => v === "confirm").length,
      reject: vals.filter((v) => v === "reject").length,
      uncertain: vals.filter((v) => v === "uncertain").length,
    };
  }, [labels]);

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (events.length === 0)
    return <EmptyState title="Nothing to label" description="Run multi-species detection first." />;

  const setLabel = (idx: number, label: Label) =>
    setLabels((prev) => {
      const next = { ...prev };
      if (next[idx] === label) delete next[idx];
      else next[idx] = label;
      return next;
    });

  const pages = Math.ceil(events.length / PER_PAGE);
  const start = page * PER_PAGE;
  const pageEvents = events.slice(start, start + PER_PAGE);

  const exportLabels = () => {
    const rows = Object.entries(labels).map(([idx, label]) => {
      const e = events[Number(idx)];
      return {
        recording_id: recordingId, event_index: idx,
        start_s: e.start, end_s: e.end, predicted_species: e.species,
        predicted_confidence: e.confidence, is_primary: e.is_primary,
        annotator, annotator_label: label, labelled_at: new Date().toISOString(),
      };
    });
    downloadCsv(`labels_${annotator || "anon"}.csv`, toCsv(rows));
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="specimen-label mb-1 block">Annotator</span>
          <input
            value={annotator}
            onChange={(e) => { setAnnotator(e.target.value); localStorage.setItem("ao-annotator", e.target.value); }}
            placeholder="e.g. Jisan, Rafel"
            className="h-9 w-56 rounded-md border border-input bg-card px-3 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </label>
        <Button variant="outline" size="sm" disabled={counts.labelled === 0 || !annotator} onClick={exportLabels}>
          <Download /> Export {counts.labelled} labels
        </Button>
        {counts.labelled > 0 && (
          <Button variant="ghost" size="sm" onClick={() => setLabels({})}>
            <RotateCcw /> Reset
          </Button>
        )}
      </div>

      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        <StatCard label="Labelled" value={`${counts.labelled} / ${events.length}`} />
        <StatCard label="Confirmed" value={counts.confirm} />
        <StatCard label="Rejected" value={counts.reject} />
        <StatCard label="Not sure" value={counts.uncertain} />
      </div>

      {/* Coverage progress */}
      <div>
        <div className="mb-1 flex justify-between specimen-label">
          <span>Labelling coverage</span>
          <span>{events.length ? Math.round((counts.labelled / events.length) * 100) : 0}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-secondary">
          <div className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${events.length ? (counts.labelled / events.length) * 100 : 0}%` }} />
        </div>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Events</CardTitle>
          {pages > 1 && (
            <div className="flex items-center gap-2 text-sm">
              <Button variant="ghost" size="icon" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                <ChevronLeft />
              </Button>
              <span className="tabular-nums">Page {page + 1} / {pages}</span>
              <Button variant="ghost" size="icon" disabled={page === pages - 1} onClick={() => setPage((p) => p + 1)}>
                <ChevronRight />
              </Button>
            </div>
          )}
        </CardHeader>
        <CardContent className="divide-y divide-border p-0">
          {pageEvents.map((e, i) => {
            const idx = start + i;
            const key = `e${idx}`;
            const label = labels[idx];
            return (
              <div key={idx} className="flex flex-wrap items-center gap-3 p-4">
                <Button size="icon" variant="secondary" aria-label="Listen" onClick={() => play(key, e.start, e.end)}>
                  {playingKey === key ? <Pause /> : <Play />}
                </Button>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">
                    {e.is_primary && <span className="mr-1">⭐</span>}{e.species}
                  </p>
                  <p className="specimen-label">
                    {e.start.toFixed(1)}–{e.end.toFixed(1)}s · {formatConfidence(e.confidence)}
                  </p>
                </div>
                <div className="flex gap-1.5">
                  <LabelButton active={label === "confirm"} tone="confirm" onClick={() => setLabel(idx, "confirm")}>
                    <Check /> Confirm
                  </LabelButton>
                  <LabelButton active={label === "reject"} tone="reject" onClick={() => setLabel(idx, "reject")}>
                    <X /> Reject
                  </LabelButton>
                  <LabelButton active={label === "uncertain"} tone="uncertain" onClick={() => setLabel(idx, "uncertain")}>
                    <HelpCircle /> Not sure
                  </LabelButton>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}

function LabelButton({
  active, tone, onClick, children,
}: { active: boolean; tone: "confirm" | "reject" | "uncertain"; onClick: () => void; children: React.ReactNode }) {
  const tones = {
    confirm: "data-[on=true]:bg-success/15 data-[on=true]:text-success data-[on=true]:border-success/40",
    reject: "data-[on=true]:bg-destructive/15 data-[on=true]:text-destructive data-[on=true]:border-destructive/40",
    uncertain: "data-[on=true]:bg-warning/15 data-[on=true]:text-warning data-[on=true]:border-warning/40",
  };
  return (
    <button
      data-on={active}
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground [&_svg]:size-3.5",
        tones[tone],
      )}
    >
      {children}
    </button>
  );
}
