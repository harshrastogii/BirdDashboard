"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import { useTheme } from "next-themes";
import { useEffect, useRef } from "react";

import { MAPTILER_KEY } from "@/lib/config";
import type { MapSite } from "@/lib/api/types";

const STYLE = (dark: boolean) =>
  `https://api.maptiler.com/maps/${dark ? "dataviz-dark" : "dataviz"}/style.json?key=${MAPTILER_KEY}`;

/** Interactive NT monitoring-site map (MapLibre GL + MapTiler basemap).
 *
 *  Points are sites (approximate locations until per-recording GPS is recovered
 *  — the marker popup states this). When a species filter is active, sites that
 *  match stay solid and non-matching sites are dimmed rather than removed, so the
 *  network context is preserved. `showSites` toggles the whole layer. */
export function MapView({
  sites, showSites = true, filtering = false, onSelect,
}: {
  sites: MapSite[];
  showSites?: boolean;
  filtering?: boolean;
  onSelect?: (siteId: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { resolvedTheme } = useTheme();
  const dark = resolvedTheme === "dark";

  useEffect(() => {
    if (!MAPTILER_KEY || !containerRef.current) return;
    let map: { remove: () => void } | null = null;
    let disposed = false;

    (async () => {
      const maplibregl = (await import("maplibre-gl")).default;
      if (disposed || !containerRef.current) return;

      const located = sites.filter((s) => s.latitude != null && s.longitude != null);

      const m = new maplibregl.Map({
        container: containerRef.current,
        style: STYLE(dark),
        center: [133.4, -19.0],
        zoom: 4.1,
        attributionControl: { compact: true },
      });
      map = m;
      m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

      const styles = getComputedStyle(document.documentElement);
      const primary = styles.getPropertyValue("--primary").trim() || "#0d6e63";

      if (showSites) {
        for (const s of located) {
          const dim = filtering && !s.matched;
          const size = 20 + Math.min(s.recording_count, 12) * 2;
          const el = document.createElement("div");
          el.style.cssText =
            `width:${size}px;height:${size}px;border-radius:9999px;background:${primary};` +
            `opacity:${dim ? 0.28 : 0.88};border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.35);` +
            `display:grid;place-items:center;color:#fff;font:600 11px/1 ui-sans-serif;cursor:pointer`;
          el.textContent = String(s.recording_count);
          el.title = s.name;
          const speciesList = s.species_present.slice(0, 6).join(", ") || "—";
          const popup = new maplibregl.Popup({ offset: size / 2, closeButton: false }).setHTML(
            `<div style="font:600 13px ui-sans-serif;margin-bottom:2px">${s.name}</div>
             <div style="font:12px ui-sans-serif;color:#666">${s.recording_count} recording(s) · location approximate</div>
             <div style="font:11px ui-sans-serif;color:#888;margin-top:4px;max-width:220px">${speciesList}</div>`,
          );
          const marker = new maplibregl.Marker({ element: el })
            .setLngLat([s.longitude!, s.latitude!])
            .setPopup(popup)
            .addTo(m);
          if (onSelect) el.addEventListener("click", () => onSelect(s.id));
          void marker;
        }
      }

      if (located.length > 1) {
        const b = new maplibregl.LngLatBounds();
        located.forEach((s) => b.extend([s.longitude!, s.latitude!]));
        m.fitBounds(b, { padding: 64, maxZoom: 7, duration: 0 });
      }
    })();

    return () => {
      disposed = true;
      map?.remove();
    };
  }, [sites, dark, showSites, filtering, onSelect]);

  if (!MAPTILER_KEY) {
    return (
      <div className="grid h-full place-items-center rounded-lg border border-dashed border-border text-center text-sm text-muted-foreground p-8">
        Map basemap unavailable — set <code className="mx-1 font-mono">NEXT_PUBLIC_MAPTILER_KEY</code> in
        frontend/.env.local.
      </div>
    );
  }

  return <div ref={containerRef} className="h-full w-full rounded-lg overflow-hidden" />;
}
