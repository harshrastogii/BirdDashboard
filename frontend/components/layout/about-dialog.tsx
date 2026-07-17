"use client";

import { HelpCircle, X, Telescope } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { APP_NAME } from "@/lib/config";

const SEEN_KEY = "ao_about_seen_v1";

/**
 * About / onboarding drawer — the platform's answer to "what is this and how do I
 * read it?". It replaces the original Streamlit "About this Dashboard" expander,
 * updated for the layered platform (v5.2 production model, metric provenance,
 * honest significance). Opens automatically the first time a browser visits, and
 * on demand via the top-bar Help button. Accessible: role=dialog, aria-modal,
 * Esc + backdrop close, focus moved in and restored on close.
 */
export function AboutDialog() {
  const [open, setOpen] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const openerRef = useRef<HTMLElement | null>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  const show = useCallback(() => {
    openerRef.current = document.activeElement as HTMLElement;
    setOpen(true);
  }, []);

  const hide = useCallback(() => {
    setOpen(false);
    openerRef.current?.focus?.();
  }, []);

  // First-run auto-open. Reading localStorage is client-only, and opening is
  // deferred to the next frame (after mount/paint) so it neither triggers a
  // cascading render in the same commit nor risks an SSR hydration mismatch.
  useEffect(() => {
    let firstRun = false;
    try {
      firstRun = !localStorage.getItem(SEEN_KEY);
    } catch {
      /* localStorage unavailable — skip auto-open */
    }
    if (!firstRun) return;
    const id = requestAnimationFrame(() => setOpen(true));
    return () => cancelAnimationFrame(id);
  }, []);

  // Mark seen + move focus into the dialog whenever it opens.
  useEffect(() => {
    if (!open) return;
    try {
      localStorage.setItem(SEEN_KEY, "1");
    } catch {
      /* ignore */
    }
    closeBtnRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        hide();
        return;
      }
      // Focus trap: keep Tab / Shift+Tab cycling inside the dialog (WCAG 2.4.3).
      if (e.key !== "Tab") return;
      const root = dialogRef.current;
      if (!root) return;
      const focusable = root.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), textarea, select, [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (e.shiftKey && (active === first || !root.contains(active))) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && (active === last || !root.contains(active))) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, hide]);

  return (
    <>
      <Button variant="ghost" size="icon" aria-label="About Avian Observatory" onClick={show}>
        <HelpCircle />
      </Button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-sm"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) hide();
          }}
        >
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="about-title"
            className="flex h-full w-full max-w-xl flex-col overflow-hidden border-l border-border bg-background shadow-2xl"
          >
            <div className="flex items-center gap-2.5 border-b border-border px-6 py-4">
              <span className="grid size-8 place-items-center rounded-md bg-primary text-primary-foreground">
                <Telescope className="size-5" />
              </span>
              <h2 id="about-title" className="text-lg font-semibold">About {APP_NAME}</h2>
              <Button
                ref={closeBtnRef}
                variant="ghost"
                size="icon"
                aria-label="Close"
                className="ml-auto"
                onClick={hide}
              >
                <X />
              </Button>
            </div>

            <div className="min-h-0 flex-1 space-y-6 overflow-y-auto px-6 py-5 text-sm leading-relaxed">
              <Section title="What is Avian Observatory?">
                <p>
                  An environmental-intelligence platform for <strong>acoustic bird monitoring</strong> in
                  the Northern Territory. It analyses audio recordings with region-specific AI to identify
                  species, then fuses those detections with spatial and biodiversity context — moving from
                  “what species is this?” toward “<strong>where, when, and what does it mean for
                  conservation?</strong>”
                </p>
              </Section>

              <Section title="What questions can it answer?">
                <ul className="ml-4 list-disc space-y-1">
                  <li>Which Northern Territory species are present in a recording, and when?</li>
                  <li>Does a region-specific model detect NT species that the global BirdNET model misses?</li>
                  <li>How diverse is a site (species richness, Shannon, Simpson)?</li>
                  <li>Where are recordings concentrated across the monitoring network?</li>
                </ul>
              </Section>

              <Section title="How the analysis works">
                <p>
                  Audio is split into <strong>3-second windows</strong>. Two models score each window and
                  return a species with a <strong>confidence</strong> (0–100%):
                </p>
                <ul className="ml-4 mt-1 list-disc space-y-1">
                  <li><strong>NT Custom Classifier (v5)</strong> — the production model: BirdNET embeddings
                    with a Northern-Territory-specific head, run through the v5.2 multi-species
                    sound-event-detection pipeline.</li>
                  <li><strong>BirdNET v2.4 (global)</strong> — the comparison baseline (~6,000 species,
                    trained mostly on Northern-Hemisphere birds).</li>
                </ul>
              </Section>

              <Section title="Why BirdNET gets NT species wrong">
                <p>
                  BirdNET routinely misidentifies Australian birds as European or North American species
                  (e.g. Azure Kingfisher → “Eurasian Treecreeper”). This is <strong>expected, and is a key
                  finding</strong> — it is why a region-specific model matters. The Model Comparison shows
                  each model’s prediction per recording so every success and failure is transparent.
                </p>
              </Section>

              <Section title="How to read the outputs">
                <dl className="space-y-2">
                  <Term term="Confidence">How sure a model is (0% = guessing, 100% = certain). Use the
                    threshold sliders to hide low-confidence detections.</Term>
                  <Term term="Spectrogram">A visual “fingerprint” of sound — time (x), frequency (y),
                    loudness (brightness). Each species has a distinctive pattern.</Term>
                  <Term term="Biodiversity indices">Species richness, Shannon (H′) and Simpson (D)
                    summarise how diverse a site is — used in impact assessment and conservation reporting.</Term>
                  <Term term="Confidence intervals & significance">Metrics show their sampling uncertainty
                    (95% intervals), and the model comparison reports whether a difference is
                    statistically significant. A lead can be real in direction yet not yet significant at a
                    small sample size — both are shown honestly.</Term>
                  <Term term="Provenance badges">“Documented · not verified” marks reported values with no
                    traceable evaluation; verified/reproduced metrics come from persisted artefacts. These
                    are never conflated.</Term>
                  <Term term="Approximate locations">Map points are site-level approximations until precise
                    per-recording GPS is recovered — the map says so rather than fabricating coordinates.</Term>
                </dl>
              </Section>

              <Section title="Who is it for?">
                <ul className="ml-4 list-disc space-y-1">
                  <li><strong>Field ecologists</strong> — scan recordings for species presence.</li>
                  <li><strong>Conservation managers</strong> — track species and diversity across sites.</li>
                  <li><strong>Policy makers</strong> — exportable biodiversity summaries for assessments.</li>
                  <li><strong>Researchers</strong> — compare a region-specific model against a global one,
                    reproducibly.</li>
                </ul>
              </Section>

              <p className="border-t border-border pt-4 text-xs text-muted-foreground">
                PRT840 IT Thesis · Charles Darwin University · Supervisor: Dr. Md Rafiqul Islam.
              </p>
            </div>

            <div className="border-t border-border px-6 py-3 text-right">
              <Button onClick={hide}>Start exploring</Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-1.5">
      <h3 className="font-semibold text-foreground">{title}</h3>
      <div className="space-y-2 text-muted-foreground [&_strong]:text-foreground">{children}</div>
    </section>
  );
}

function Term({ term, children }: { term: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="font-medium text-foreground">{term}</dt>
      <dd className="text-muted-foreground">{children}</dd>
    </div>
  );
}
