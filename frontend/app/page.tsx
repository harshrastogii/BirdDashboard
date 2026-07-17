"use client";

import Link from "next/link";
import { ArrowRight, Bird, Layers, LineChart, MapPin, Telescope, Waves } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { MapView } from "@/components/map/map-view";
import { useMapSites, useRecordings, useSpecies } from "@/lib/api/hooks";
import { APP_NAME } from "@/lib/config";

const CAPABILITIES = [
  { icon: Waves, title: "Acoustic detection", text: "Region-specific classifiers identify NT species that global models routinely misidentify." },
  { icon: Layers, title: "Multi-species events", text: "Dual-threshold sound-event detection resolves overlapping calls with timestamps." },
  { icon: Bird, title: "Species intelligence", text: "A curated Northern Territory taxonomy with conservation context." },
  { icon: LineChart, title: "Biodiversity metrics", text: "Shannon and Simpson indices ready for environmental impact assessment." },
];

export default function Home() {
  const species = useSpecies(200);
  const recordings = useRecordings(200);
  const sites = useMapSites();

  const stats = [
    { label: "Species tracked", value: species.data?.items.length ?? "—", icon: Bird },
    { label: "Recordings", value: recordings.data?.items.length ?? "—", icon: Waves },
    { label: "Monitoring sites", value: sites.data?.sites.length ?? "—", icon: MapPin },
  ];

  return (
    <div className="min-h-svh">
      {/* Top nav */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2.5">
          <span className="grid size-9 place-items-center rounded-md bg-primary text-primary-foreground">
            <Telescope className="size-5" />
          </span>
          <span className="text-lg font-semibold tracking-tight">{APP_NAME}</span>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button asChild>
            <Link href="/dashboard">
              Enter the Observatory <ArrowRight />
            </Link>
          </Button>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto grid max-w-6xl items-center gap-10 px-6 pb-8 pt-8 lg:grid-cols-2 lg:pt-16">
        <div>
          <p className="specimen-label mb-4">Northern Territory · Acoustic Wildlife Monitoring</p>
          <h1 className="text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl">
            Environmental intelligence, <span className="text-primary">heard</span> before it&apos;s seen.
          </h1>
          <p className="mt-5 max-w-xl text-lg text-muted-foreground">
            Avian Observatory turns field recordings into biodiversity intelligence — combining
            region-specific AI, multi-species detection, and a GIS-first workspace for researchers,
            conservation scientists, and government agencies.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button asChild size="lg">
              <Link href="/dashboard">
                Explore the platform <ArrowRight />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/map">View the map</Link>
            </Button>
          </div>

          <dl className="mt-10 grid grid-cols-3 gap-4 border-t border-border pt-6">
            {stats.map((s) => (
              <div key={s.label}>
                <dd className="text-2xl font-semibold tabular-nums">{s.value}</dd>
                <dt className="specimen-label mt-0.5">{s.label}</dt>
              </div>
            ))}
          </dl>
        </div>

        <Card className="h-[380px] overflow-hidden p-2 lg:h-[440px]">
          <MapView sites={sites.data?.sites ?? []} />
        </Card>
      </section>

      {/* Capabilities */}
      <section className="mx-auto max-w-6xl px-6 py-14">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CAPABILITIES.map((c) => (
            <Card key={c.title} className="p-5">
              <span className="grid size-10 place-items-center rounded-md bg-primary/10 text-primary">
                <c.icon className="size-5" />
              </span>
              <h3 className="mt-4 font-semibold">{c.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{c.text}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* Credibility */}
      <section className="border-t border-border bg-card">
        <div className="mx-auto max-w-6xl px-6 py-12">
          <p className="specimen-label">Why region-specific models matter</p>
          <p className="mt-3 max-w-3xl text-lg">
            Global models trained on Northern-Hemisphere birdsong routinely misclassify Australian
            species. Avian Observatory pairs the global BirdNET baseline with custom Northern Territory
            classifiers — making the gap visible, and closing it.
          </p>
          <p className="mt-6 specimen-label">
            PRT840 Thesis · Charles Darwin University · Northern Territory, Australia
          </p>
        </div>
      </section>
    </div>
  );
}
