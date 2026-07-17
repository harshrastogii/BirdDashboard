import {
  LayoutDashboard, Map, Bird, AudioLines, Leaf, Gauge, Activity, Route, Fish,
  Layers, Radio, type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  status?: "live" | "soon";
}

export interface NavSection {
  title: string;
  items: NavItem[];
}

/**
 * Information architecture — lean and purpose-driven.
 *   Overview  = aggregate intelligence
 *   Explore   = find things (spatial, library, catalog)
 *   Analyze   = cross-cutting analysis (the thesis story + biodiversity)
 *   Roadmap   = genuinely future modules
 * Per-recording analysis (BirdNET, NT, multi-species, Listen & Label) lives
 * inside the Recording workspace, not as separate nav items.
 */
export const NAV: NavSection[] = [
  {
    title: "Overview",
    items: [{ label: "Territory Dashboard", href: "/dashboard", icon: LayoutDashboard, status: "live" }],
  },
  {
    title: "Explore",
    items: [
      { label: "Interactive Map", href: "/map", icon: Map, status: "live" },
      { label: "Recordings", href: "/recordings", icon: AudioLines, status: "live" },
      { label: "Species", href: "/species", icon: Bird, status: "live" },
    ],
  },
  {
    title: "Analyze",
    items: [
      { label: "Model Comparison", href: "/models", icon: Gauge, status: "live" },
      { label: "Biodiversity", href: "/biodiversity", icon: Leaf, status: "live" },
    ],
  },
  {
    title: "Roadmap",
    items: [
      { label: "Behaviour Analysis", href: "/analysis/behaviour", icon: Activity, status: "soon" },
      { label: "Migration Analytics", href: "/migration", icon: Route, status: "soon" },
      { label: "Pelican Intelligence", href: "/pelican", icon: Fish, status: "soon" },
      { label: "Environmental Layers", href: "/environment", icon: Layers, status: "soon" },
      { label: "Sensor Network", href: "/sensors", icon: Radio, status: "soon" },
    ],
  },
];

/**
 * Navigation the user should actually see. Placeholder ("soon") modules are
 * hidden unless the `roadmapModules` feature flag is on, and any section left
 * empty is dropped — so the nav reflects only what is genuinely usable today.
 */
export function visibleSections(showRoadmap: boolean): NavSection[] {
  return NAV
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => showRoadmap || item.status !== "soon"),
    }))
    .filter((section) => section.items.length > 0);
}
