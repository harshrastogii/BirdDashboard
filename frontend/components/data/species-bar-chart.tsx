"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatConfidence } from "@/lib/utils";

/**
 * Shared horizontal confidence bar chart — one visual language for both the
 * NT model and BirdNET so the two are directly comparable. `highlight` marks
 * a row (e.g. the ground-truth species) in the accent colour.
 */
export function SpeciesBarChart({
  data, color = "var(--primary)", highlight,
}: {
  data: { name: string; confidence: number }[];
  color?: string;
  highlight?: string | null;
}) {
  const normalize = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, "");
  const hl = highlight ? normalize(highlight) : null;

  return (
    <ResponsiveContainer width="100%" height={Math.max(160, data.length * 34)}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
        <XAxis type="number" domain={[0, 1]} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
        <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
        <Tooltip formatter={(v: number) => formatConfidence(v)} cursor={{ fill: "var(--secondary)" }} />
        <Bar dataKey="confidence" radius={[0, 4, 4, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={hl && normalize(d.name) === hl ? "var(--accent)" : color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
