"use client";

import Link from "next/link";
import { Bird, Search } from "lucide-react";
import { useMemo, useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/data/empty-state";
import { useRecordings, useSpecies } from "@/lib/api/hooks";
import { groundTruthFor } from "@/lib/ground-truth";

export default function SpeciesPage() {
  const species = useSpecies(200);
  const recordings = useRecordings(200);
  const [query, setQuery] = useState("");
  const [threatenedOnly, setThreatenedOnly] = useState(false);

  // Map each species -> its reference recordings (by filename ground truth).
  const recsBySpecies = useMemo(() => {
    const names = species.data?.items.map((s) => s.common_name) ?? [];
    const map = new Map<string, { id: string }[]>();
    for (const r of recordings.data?.items ?? []) {
      const gt = groundTruthFor(r.filename, names);
      if (gt) {
        const arr = map.get(gt) ?? [];
        arr.push({ id: r.id });
        map.set(gt, arr);
      }
    }
    return map;
  }, [species.data, recordings.data]);

  const filtered = (species.data?.items ?? []).filter((s) => {
    if (threatenedOnly && (!s.conservation_status || s.conservation_status === "Least Concern")) return false;
    if (query && !s.common_name.toLowerCase().includes(query.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Species"
        description="The Northern Territory species the platform recognises — with conservation status and reference recordings you can open and analyse."
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-56 max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search species…"
            className="h-9 w-full rounded-md border border-input bg-card pl-9 pr-3 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </div>
        <Button variant={threatenedOnly ? "default" : "outline"} size="sm" onClick={() => setThreatenedOnly((v) => !v)}>
          Threatened only
        </Button>
      </div>

      {species.isError ? (
        <ErrorState onRetry={() => { species.refetch(); recordings.refetch(); }} />
      ) : species.isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 9 }).map((_, i) => <Skeleton key={i} className="h-28 w-full" />)}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState icon={Bird} title="No species match"
          description={query || threatenedOnly ? "Adjust your search or the threatened-only filter." : "No species in the catalog yet."} />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((s) => {
            const recs = recsBySpecies.get(s.common_name) ?? [];
            const threatened = s.conservation_status && s.conservation_status !== "Least Concern";
            return (
              <Card key={s.id} className="flex flex-col p-4">
                <div className="flex items-start gap-3">
                  <span className="grid size-10 shrink-0 place-items-center rounded-md bg-primary/10 text-primary">
                    <Bird className="size-5" />
                  </span>
                  <div className="min-w-0">
                    <p className="font-medium leading-tight">{s.common_name}</p>
                    {s.scientific_name && <p className="text-sm italic text-muted-foreground">{s.scientific_name}</p>}
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-2">
                  {threatened && <Badge variant="warning">{s.conservation_status}</Badge>}
                  <span className="specimen-label">{recs.length} recording{recs.length === 1 ? "" : "s"}</span>
                  {recs.length > 0 && (
                    <Link href={`/recordings/${recs[0].id}`} className="ml-auto text-sm text-primary hover:underline">
                      Open →
                    </Link>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
