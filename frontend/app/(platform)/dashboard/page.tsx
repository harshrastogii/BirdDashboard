"use client";

import Link from "next/link";
import { AudioLines, Bird, Gauge, Leaf, MapPin, ShieldAlert } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/data/stat-card";
import { ErrorState } from "@/components/data/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useBiodiversity, useModelComparison, useRecordings, useSites, useSpecies } from "@/lib/api/hooks";
import { formatConfidence } from "@/lib/utils";

export default function DashboardPage() {
  const recordings = useRecordings(200);
  const species = useSpecies(200);
  const sites = useSites();
  const bio = useBiodiversity(0.25);
  const cmp = useModelComparison();

  const queries = [recordings, species, sites, bio, cmp];
  // Whole-page failure (e.g. the API is unreachable) gets one clear, retryable
  // error rather than a page of broken widgets.
  if (queries.every((q) => q.isError)) {
    return (
      <div className="space-y-6">
        <PageHeader title="Territory Dashboard" description="Aggregate intelligence across the Northern Territory acoustic monitoring programme." />
        <ErrorState onRetry={() => queries.forEach((q) => q.refetch())} />
      </div>
    );
  }

  const threatened = (species.data?.items ?? []).filter(
    (s) => s.conservation_status && s.conservation_status !== "Least Concern",
  );
  const total = cmp.data?.total_with_ground_truth ?? 0;
  const ntPct = total ? cmp.data!.nt_correct / total : 0;
  const bnPct = total ? cmp.data!.birdnet_correct / total : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Territory Dashboard"
        description="Aggregate intelligence across the Northern Territory acoustic monitoring programme — model performance, biodiversity, and species of concern at a glance."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Species tracked" value={species.isLoading ? "—" : species.data?.items.length ?? 0} icon={Bird} hint="NT classifier classes" />
        <StatCard label="Recordings" value={recordings.isLoading ? "—" : recordings.data?.items.length ?? 0} icon={AudioLines} hint="In the acoustic library" />
        <StatCard label="Monitoring sites" value={sites.isLoading ? "—" : sites.data?.length ?? 0} icon={MapPin} hint="Top End & Centre" />
        <StatCard label="Biodiversity (H′)" value={bio.isLoading ? "—" : bio.data?.overall_shannon.toFixed(2) ?? "—"} icon={Leaf} hint="Shannon index" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Model comparison headline — the platform's thesis */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2"><Gauge className="size-4 text-primary" /> NT model vs global BirdNET</CardTitle>
            <Link href="/models" className="text-sm text-primary hover:underline">Details →</Link>
          </CardHeader>
          <CardContent>
            {cmp.isLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
                  <p className="specimen-label">NT Custom Classifier (v5)</p>
                  <p className="mt-1 text-3xl font-semibold tabular-nums text-primary">{formatConfidence(ntPct)}</p>
                  <p className="text-sm text-muted-foreground">{cmp.data?.nt_correct}/{total} NT recordings identified</p>
                </div>
                <div className="rounded-lg border border-border p-4">
                  <p className="specimen-label">BirdNET v2.4 (global)</p>
                  <p className="mt-1 text-3xl font-semibold tabular-nums">{formatConfidence(bnPct)}</p>
                  <p className="text-sm text-muted-foreground">{cmp.data?.birdnet_correct}/{total} NT recordings identified</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Conservation watch */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><ShieldAlert className="size-4 text-accent" /> Species of concern</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {species.isLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : threatened.length ? (
              threatened.map((s) => (
                <div key={s.id} className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                  <span className="text-sm">{s.common_name}</span>
                  <Badge variant="warning">{s.conservation_status}</Badge>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No threatened species in the current catalog.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Biodiversity snapshot */}
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2"><Leaf className="size-4 text-primary" /> Biodiversity snapshot</CardTitle>
          <Link href="/biodiversity" className="text-sm text-primary hover:underline">Full report →</Link>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <Metric label="Species richness" value={bio.data?.overall_richness ?? "—"} />
          <Metric label="Shannon index (H′)" value={bio.data?.overall_shannon.toFixed(3) ?? "—"} />
          <Metric label="Simpson index (D)" value={bio.data?.overall_simpson.toFixed(3) ?? "—"} />
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border p-4 text-center">
      <p className="text-2xl font-semibold tabular-nums">{value}</p>
      <p className="specimen-label mt-0.5">{label}</p>
    </div>
  );
}
