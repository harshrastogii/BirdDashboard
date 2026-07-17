"use client";

import Link from "next/link";
import { AudioLines, Layers, MapPin } from "lucide-react";
import { useMemo, useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { MapView } from "@/components/map/map-view";
import { ErrorState, SampleDataNote } from "@/components/data/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { InfoPopover } from "@/components/ui/info-popover";
import { useEnvironmentalLayers, useMapSites, useRecordings } from "@/lib/api/hooks";
import { cn, prettyRecordingName } from "@/lib/utils";

export default function MapPage() {
  const [minConf, setMinConf] = useState(0.25);
  const [species, setSpecies] = useState<string>("");     // "" = all
  const [showSites, setShowSites] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);

  const map = useMapSites(minConf, species || undefined);
  const env = useEnvironmentalLayers();
  const siteRecordings = useRecordings(200, undefined, selected ?? undefined);
  const sites = useMemo(() => map.data?.sites ?? [], [map.data]);
  const selectedSite = sites.find((s) => s.id === selected);
  const filtering = species !== "";

  // Species options = union of species detected across sites at this threshold.
  const speciesOptions = useMemo(() => {
    const set = new Set<string>();
    sites.forEach((s) => s.species_present.forEach((sp) => set.add(sp)));
    return Array.from(set).sort();
  }, [sites]);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Interactive Map"
        description="Spatially explore the Northern Territory monitoring network. Filter by species and confidence; select a site to drill into its recordings."
        actions={<SampleDataNote />}
      />

      {/* Filter + layer controls */}
      <Card>
        <CardContent className="flex flex-wrap items-center gap-x-6 gap-y-3 py-3">
          <label className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Species</span>
            <select
              value={species}
              onChange={(e) => setSpecies(e.target.value)}
              aria-label="Filter sites by species"
              className="rounded-md border border-border bg-background px-2 py-1 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="">All species</option>
              {speciesOptions.map((sp) => <option key={sp} value={sp}>{sp}</option>)}
            </select>
          </label>

          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            Min confidence
            <input type="range" min={0} max={0.9} step={0.05} value={minConf}
              onChange={(e) => setMinConf(Number(e.target.value))} className="accent-[var(--primary)]" />
            <span className="w-9 tabular-nums">{(minConf * 100).toFixed(0)}%</span>
          </label>

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={showSites} onChange={(e) => setShowSites(e.target.checked)} />
              <MapPin className="size-4 text-primary" /> Monitoring sites
            </label>
            <span className="flex items-center gap-2 text-sm text-muted-foreground" title={env.data?.note ?? ""}>
              <input type="checkbox" checked={false} disabled />
              <Layers className="size-4" /> Environmental layers
              <span className="specimen-label">soon</span>
              <InfoPopover title="Environmental layers">
                <p>{env.data?.note ?? "Fire, weather, vegetation, protected areas and more will overlay here."}</p>
                {env.data?.layers?.length ? (
                  <p className="mt-1">Planned: {env.data.layers.map((l) => l.name).join(", ")}.</p>
                ) : null}
              </InfoPopover>
            </span>
          </div>

          <span className="ml-auto specimen-label" title={map.data?.coordinate_precision_note ?? ""}>
            Locations approximate
          </span>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Map */}
        <div className="h-[68svh] lg:col-span-2">
          {map.isError
            ? <ErrorState onRetry={() => map.refetch()} />
            : map.isLoading
            ? <Skeleton className="h-full w-full" />
            : <MapView sites={sites} showSites={showSites} filtering={filtering} onSelect={setSelected} />}
        </div>

        {/* Site drill-down panel */}
        <Card className="flex h-[68svh] flex-col">
          <CardHeader>
            <CardTitle className="text-sm">
              {selectedSite ? selectedSite.name : filtering ? `Sites with ${species}` : "Monitoring sites"}
            </CardTitle>
          </CardHeader>
          <CardContent className="min-h-0 flex-1 overflow-y-auto">
            {!selected ? (
              <ul className="space-y-1">
                {sites
                  .filter((s) => !filtering || s.matched)
                  .map((s) => (
                    <li key={s.id}>
                      <button
                        onClick={() => setSelected(s.id)}
                        className={cn(
                          "flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-secondary",
                        )}
                      >
                        <span className="flex items-center gap-2">
                          <MapPin className="size-4 text-primary" /> {s.name}
                        </span>
                        <span className="specimen-label">{s.recording_count}</span>
                      </button>
                    </li>
                  ))}
                {filtering && !sites.some((s) => s.matched) && (
                  <li className="px-3 py-2 text-sm text-muted-foreground">No sites with {species} above this confidence.</li>
                )}
              </ul>
            ) : (
              <div className="space-y-2">
                <button onClick={() => setSelected(null)} className="text-sm text-primary hover:underline">
                  ← All sites
                </button>
                {siteRecordings.isLoading ? (
                  <Skeleton className="h-40 w-full" />
                ) : siteRecordings.data?.items.length ? (
                  siteRecordings.data.items.map((r) => (
                    <Link
                      key={r.id}
                      href={`/recordings/${r.id}`}
                      className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm hover:border-primary/40"
                    >
                      <AudioLines className="size-4 text-primary" />
                      <span className="truncate">{prettyRecordingName(r.filename)}</span>
                    </Link>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">No recordings at this site.</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
