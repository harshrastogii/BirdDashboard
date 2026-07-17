"use client";

import Link from "next/link";
import { AlertTriangle, CheckCircle2, Globe, MapPin } from "lucide-react";
import {
  Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ErrorState } from "@/components/data/empty-state";
import { useModelComparison, useModelRegistry } from "@/lib/api/hooks";
import type {
  DocumentedMetrics, Interval, McNemar, ModelEvaluation, ModelMetrics, RegistryModel,
} from "@/lib/api/types";
import { formatConfidence } from "@/lib/utils";

const EVOLUTION = [
  { v: "v2 / v3", name: "Custom CNN (mel-spectrograms)", result: "92.7% segment-level",
    note: "Baseline NT classifier. The high accuracy was later found to be inflated by segment-level data leakage.", status: "superseded" },
  { v: "v4", name: "Same CNN, recording-level split", result: "66.6% recording-level",
    note: "Exposed the leakage: honest accuracy was far lower once segments from one recording couldn't appear in both train and test.", status: "superseded" },
  { v: "v5", name: "NT Custom Classifier (BirdNET embeddings + NT head)", result: "AUPRC 0.98 · AUROC 0.99",
    documented: true,
    note: "Transfer learning on BirdNET v2.4 embeddings bypasses the leakage at the representational level. The current production classifier. The 0.98/0.99 are documented thesis values (not independently verified); the reproducible recording-level held-out estimate is accuracy 0.88 (see Research Metrics).", status: "production" },
  { v: "v5.2", name: "Multi-Species Sound Event Detection", result: "Multi-species + timestamps",
    note: "Sliding-window, dual-threshold detection over the v5 classifier. The operational pipeline used throughout Avian Observatory.", status: "production" },
];

export default function ModelComparisonPage() {
  const cmp = useModelComparison();
  const registry = useModelRegistry();
  const total = cmp.data?.total_with_ground_truth ?? 0;
  const ntPct = total ? cmp.data!.nt_correct / total : 0;
  const bnPct = total ? cmp.data!.birdnet_correct / total : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Model Performance"
        description="The production NT Custom Classifier (v5) against the global BirdNET baseline — plus published research metrics and the model's evolution."
      />

      <Tabs defaultValue="comparison">
        <TabsList>
          <TabsTrigger value="comparison">Comparison</TabsTrigger>
          <TabsTrigger value="research">Research Metrics</TabsTrigger>
          <TabsTrigger value="evolution">Model Evolution</TabsTrigger>
        </TabsList>

        {/* Operational, data-driven comparison */}
        <TabsContent value="comparison" className="space-y-6">
          {cmp.isError && <ErrorState onRetry={() => cmp.refetch()} />}
          {cmp.isLoading && <Skeleton className="h-40 w-full" />}
          {cmp.data && (
            <>
              <div className="grid gap-4 md:grid-cols-2">
                <Card className="border-primary/30">
                  <CardHeader className="flex-row items-center gap-2">
                    <MapPin className="size-5 text-primary" /><CardTitle>NT Custom Classifier (v5)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-4xl font-semibold tabular-nums text-primary">{formatConfidence(ntPct)}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{cmp.data.nt_correct} of {total} correctly identified · v5.2 SED</p>
                    {cmp.data.nt_interval && <CiLine ci={cmp.data.nt_interval} />}
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="flex-row items-center gap-2">
                    <Globe className="size-5 text-muted-foreground" /><CardTitle>BirdNET v2.4 (global)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-4xl font-semibold tabular-nums">{formatConfidence(bnPct)}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{cmp.data.birdnet_correct} of {total} correctly identified</p>
                    {cmp.data.birdnet_interval && <CiLine ci={cmp.data.birdnet_interval} />}
                  </CardContent>
                </Card>
              </div>

              {cmp.data.mcnemar && <SignificanceNote m={cmp.data.mcnemar} total={total} />}

              <p className="text-sm text-muted-foreground">
                Both models are scored on <strong>exactly the same {total} recordings</strong>, using the verified
                species label for each (synonym-aware, so a correct detection under a synonymous name is not counted
                as a miss). A model is “correct” when it detects that species. The predicted species is shown so
                every success and failure is transparent. Rates carry Wilson 95% intervals; the paired difference is
                assessed with an exact McNemar test.
              </p>

              <Card>
                <CardHeader><CardTitle>Per-recording results</CardTitle></CardHeader>
                <CardContent className="p-0">
                  <div className="max-h-[30rem] overflow-auto">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-card">
                        <tr className="border-b border-border text-left specimen-label">
                          <th className="p-3">Recording</th><th className="p-3">Actual</th>
                          <th className="p-3">NT (v5) predicted</th><th className="p-3">BirdNET predicted</th>
                        </tr>
                      </thead>
                      <tbody>
                        {cmp.data.per_recording.map((r) => (
                          <tr key={r.recording_id} className={"border-b border-border/60" + (r.evaluated ? "" : " opacity-50")}>
                            <td className="p-3">
                              <Link href={`/recordings/${r.recording_id}`} className="text-primary hover:underline">{r.name}</Link>
                            </td>
                            <td className="p-3">{r.ground_truth ?? <span className="text-muted-foreground">not labelled</span>}</td>
                            <td className="p-3"><Predicted top={r.nt_top} correct={r.nt_correct} /></td>
                            <td className="p-3"><Predicted top={r.birdnet_top} correct={r.birdnet_correct} conf={r.birdnet_confidence} /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>

        {/* Research metrics — registry-driven; documented vs reproduced kept distinct */}
        <TabsContent value="research" className="space-y-4">
          {registry.isError && <ErrorState onRetry={() => registry.refetch()} />}
          {registry.isLoading && <Skeleton className="h-40 w-full" />}
          {registry.data && (
            <>
              <p className="max-w-3xl text-sm text-muted-foreground">
                Each model is a versioned scientific artefact. <strong>Documented</strong> values are reported in
                the thesis but not traceable to an evaluation artefact; <strong>original evaluations</strong> are
                reproduced from the original saved artefacts; <strong>independent reproductions</strong> are new
                experiments. These are never presented as the same experiment.
              </p>
              {registry.data.models.map((m) => <ModelRegistryCard key={m.key} model={m} />)}
            </>
          )}
        </TabsContent>

        {/* History */}
        <TabsContent value="evolution" className="space-y-4">
          <p className="max-w-3xl text-sm text-muted-foreground">
            The production model is the result of five research iterations. The early CNN models are retained
            here as documented history — they are <strong>not</strong> the operational system.
          </p>
          {EVOLUTION.map((m) => (
            <Card key={m.v} className={m.status === "production" ? "border-primary/30" : undefined}>
              <CardContent className="flex flex-wrap items-start gap-4 py-4">
                <div className="w-16 shrink-0">
                  <p className="font-mono text-lg font-semibold">{m.v}</p>
                  <Badge variant={m.status === "production" ? "default" : "secondary"} className="mt-1">{m.status}</Badge>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{m.name}</p>
                  <p className="specimen-label mt-0.5 flex flex-wrap items-center gap-2">
                    {m.result}
                    {m.documented && <Badge variant="warning">Documented · not verified</Badge>}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">{m.note}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Predicted({ top, correct, conf }: { top: string | null; correct: boolean | null; conf?: number | null }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      {correct === true && <CheckCircle2 className="size-4 shrink-0 text-success" />}
      {correct === false && <AlertTriangle className="size-4 shrink-0 text-warning" />}
      <span className={correct === false ? "text-warning" : undefined}>
        {top ?? "—"}
        {conf != null && <span className="ml-1 text-xs text-muted-foreground">{formatConfidence(conf)}</span>}
      </span>
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variant = status === "production" ? "default" : status === "baseline" ? "secondary" : "outline";
  return <Badge variant={variant as "default" | "secondary" | "outline"}>{status}</Badge>;
}

function typeLabel(type: string): string {
  if (type === "original_evaluation") return "Original evaluation · traceable";
  if (type === "independent_reproduction") return "Independent reproduction · not the original experiment";
  return type;
}

function ModelRegistryCard({ model }: { model: RegistryModel }) {
  return (
    <section className="space-y-4 rounded-lg border border-border p-5">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold">{model.name}</h2>
        <span className="specimen-label">v{model.version}</span>
        <StatusBadge status={model.status} />
      </div>
      <p className="max-w-3xl text-sm text-muted-foreground">{model.description}</p>
      {model.documented && <DocumentedBlock d={model.documented} />}
      {model.evaluations.map((e) => <EvaluationBlock key={e.id} e={e} />)}
      {!model.documented && model.evaluations.length === 0 && (
        <p className="text-sm text-muted-foreground">No research evaluation on this model (comparison baseline).</p>
      )}
    </section>
  );
}

function DocumentedBlock({ d }: { d: DocumentedMetrics }) {
  return (
    <Card className="border-warning/40">
      <CardHeader className="flex-row flex-wrap items-center gap-2">
        <CardTitle className="text-base">{d.label}</CardTitle>
        <Badge variant="warning">Documented · not verified</Badge>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-8">
          {Object.entries(d.metrics).map(([k, v]) => (
            <Figure key={k} label={k} value={typeof v === "number" ? v.toFixed(2) : String(v)} />
          ))}
        </div>
        <p className="mt-3 max-w-3xl text-xs text-muted-foreground">
          {d.note} <span className="italic">Source: {d.source}.</span>
        </p>
      </CardContent>
    </Card>
  );
}

function EvaluationBlock({ e }: { e: ModelEvaluation }) {
  if (!e.available || !e.metrics) {
    return (
      <div className="rounded-md border border-dashed border-border p-4">
        <p className="flex flex-wrap items-center gap-2 font-medium">
          {e.title} <Badge variant="secondary">{typeLabel(e.type)}</Badge>
        </p>
        <p className="mt-1 text-sm text-muted-foreground">{e.note}</p>
        <p className="mt-2 text-xs text-muted-foreground">
          Not yet generated — run <code className="font-mono">evaluate_v5.py</code> to produce this reproducible evaluation.
        </p>
      </div>
    );
  }
  return (
    <VerifiedMetrics
      title={e.title}
      metrics={e.metrics}
      badge={typeLabel(e.type)}
      badgeVariant={e.type === "original_evaluation" ? "success" : "accent"}
      note={e.note}
    />
  );
}

function VerifiedMetrics({
  title, metrics, badge, badgeVariant = "success", note,
}: { title: string; metrics: ModelMetrics; badge: string; badgeVariant?: "success" | "accent"; note: string }) {
  const provenance = Object.entries(metrics.provenance)
    .map(([k, v]) => `${k}: ${String(v)}`)
    .join(" · ");
  return (
    <div className="space-y-6">
      <Card className={badgeVariant === "accent" ? "border-accent/40" : "border-success/30"}>
        <CardHeader className="flex-row flex-wrap items-center gap-2">
          <CardTitle>{title}</CardTitle>
          <Badge variant={badgeVariant}>{badge}</Badge>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-8">
            <Figure label="Accuracy" value={pct(metrics.accuracy)}
              ciText={metrics.macro_intervals?.accuracy
                ? `${pct(metrics.macro_intervals.accuracy.low)}–${pct(metrics.macro_intervals.accuracy.high)}`
                : null} />
            <Figure label="Macro F1" value={metrics.macro_f1.toFixed(3)}
              ciText={metrics.macro_intervals?.macro_f1 ? ci3(metrics.macro_intervals.macro_f1) : null} />
            <Figure label="AUROC" value={metrics.macro_auroc.toFixed(3)} />
            <Figure label="AUPRC" value={metrics.macro_auprc.toFixed(3)} />
          </div>
          {metrics.macro_intervals && (
            <p className="text-[11px] text-muted-foreground/80">
              Aggregate 95% CIs by the percentile bootstrap (2,000 resamples of the test units). AUROC/AUPRC point
              estimates shown without CIs.
            </p>
          )}
          <p className="max-w-3xl text-xs text-muted-foreground">{note}</p>
          <p className="max-w-3xl font-mono text-[11px] text-muted-foreground/80">{provenance}</p>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>ROC curve (micro-average)</CardTitle></CardHeader>
          <CardContent>
            <Curve data={metrics.roc_curve} diagonal />
            <p className="mt-2 text-[11px] text-muted-foreground">x: false-positive rate · y: true-positive rate · dashed line = chance (no skill).</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Precision–Recall curve (micro-average)</CardTitle></CardHeader>
          <CardContent>
            <Curve data={metrics.pr_curve} />
            <p className="mt-2 text-[11px] text-muted-foreground">x: recall · y: precision. Higher and further right is better.</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Per-species metrics</CardTitle></CardHeader>
        <CardContent className="p-0">
          <div className="max-h-[26rem] overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-card">
                <tr className="border-b border-border text-left specimen-label">
                  <th className="p-3">Species</th><th className="p-3 text-right">Precision</th>
                  <th className="p-3 text-right">Recall</th><th className="p-3 text-right">F1</th>
                  <th className="p-3 text-right">AUROC</th><th className="p-3 text-right">AUPRC</th>
                  <th className="p-3 text-right">Support</th>
                </tr>
              </thead>
              <tbody>
                {metrics.per_species.map((m) => (
                  <tr key={m.species}
                    className={"border-b border-border/60" + (m.reliable === false ? " text-muted-foreground" : "")}>
                    <td className="p-3">
                      {m.species}
                      {m.reliable === false && (
                        <span className="ml-1 text-warning"
                          title="Support too small for a reliable per-class estimate — the 95% CI is too wide to interpret the point value directly.">†</span>
                      )}
                    </td>
                    <td className="p-3 text-right tabular-nums">
                      {m.precision.toFixed(3)}
                      {m.precision_ci && <CiSub ci={m.precision_ci} />}
                    </td>
                    <td className="p-3 text-right tabular-nums">
                      {m.recall.toFixed(3)}
                      {m.recall_ci && <CiSub ci={m.recall_ci} />}
                    </td>
                    <td className="p-3 text-right tabular-nums align-top">{m.f1.toFixed(3)}</td>
                    <td className="p-3 text-right tabular-nums align-top">{m.auroc?.toFixed(3) ?? "—"}</td>
                    <td className="p-3 text-right tabular-nums align-top">{m.auprc?.toFixed(3) ?? "—"}</td>
                    <td className="p-3 text-right tabular-nums align-top">{m.support}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {metrics.per_species.some((m) => m.recall_ci) && (
            <p className="border-t border-border p-3 text-[11px] text-muted-foreground">
              Precision/recall show the point estimate with its exact (Clopper–Pearson) 95% CI in brackets.
              <span className="text-warning"> †</span> marks classes whose support is too small for a reliable
              per-class estimate. See the Methodology reference for details.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/** Tiny exact-CI range shown beneath a per-class point estimate. */
function CiSub({ ci }: { ci: Interval }) {
  return (
    <span className="block text-[10px] font-normal text-muted-foreground/70">
      [{ci.low.toFixed(2)}–{ci.high.toFixed(2)}]
    </span>
  );
}

function Curve({ data, diagonal }: { data: { x: number; y: number }[]; diagonal?: boolean }) {
  if (!data.length) return <p className="py-8 text-center text-sm text-muted-foreground">No curve data.</p>;
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ left: 0, right: 12, top: 8, bottom: 4 }}>
        <XAxis type="number" dataKey="x" domain={[0, 1]} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
        <YAxis type="number" domain={[0, 1]} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
        <Tooltip formatter={(v: number) => (v as number).toFixed(3)} />
        {diagonal && <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="var(--muted-foreground)" strokeDasharray="4 4" />}
        <Line type="monotone" dataKey="y" stroke="var(--primary)" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function Figure({ label, value, ciText }: { label: string; value?: string | null; ciText?: string | null }) {
  return (
    <div>
      <p className="text-3xl font-semibold tabular-nums">{value ?? "—"}</p>
      <p className="specimen-label">{label}</p>
      {ciText && <p className="mt-0.5 text-[11px] text-muted-foreground">95% CI {ciText}</p>}
    </div>
  );
}

/** One-line Wilson interval under an operational detection rate. */
function CiLine({ ci }: { ci: Interval }) {
  return (
    <p className="mt-0.5 text-xs text-muted-foreground">
      95% CI {pct(ci.low)}–{pct(ci.high)} <span className="text-muted-foreground/70">· Wilson score</span>
    </p>
  );
}

/** Surfaces the exact McNemar paired-test result. A non-significant result is
 *  shown as prominently as a significant one — with n≈23 the honest finding is
 *  usually that the gap is not yet statistically distinguishable. */
function SignificanceNote({ m, total }: { m: McNemar; total: number }) {
  const sig = m.significant_at_0_05;
  return (
    <Card className={sig ? "border-success/30" : "border-warning/40"}>
      <CardContent className="flex items-start gap-3 py-4">
        {sig
          ? <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-success" />
          : <AlertTriangle className="mt-0.5 size-5 shrink-0 text-warning" />}
        <div className="text-sm">
          <p className="font-medium">
            {sig
              ? "The difference is statistically significant (p < 0.05)"
              : "The difference is not statistically significant at this sample size"}
          </p>
          <p className="mt-1 text-muted-foreground">
            Exact McNemar paired test over the {m.n_discordant} of {total} recordings where exactly one model was
            correct: {m.only_a_correct} favour the NT model, {m.only_b_correct} favour BirdNET (p = {m.p_value.toFixed(3)}).
            {!sig && " With this few labelled recordings the observed lead could reflect sampling variation — a larger labelled set is needed to confirm it. The point estimates still favour the NT model; this is about statistical certainty, not direction."}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

const pct = (v?: number | null) => (v != null ? `${(v * 100).toFixed(1)}%` : "—");
const ci3 = (ci: Interval) => `${ci.low.toFixed(3)}–${ci.high.toFixed(3)}`;
