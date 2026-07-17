/** Runtime configuration (public — safe to expose to the browser). */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

/** MapTiler client key. MapTiler keys are client-side by design (restrict by
 *  domain in the MapTiler dashboard for production). Kept in .env.local. */
export const MAPTILER_KEY = process.env.NEXT_PUBLIC_MAPTILER_KEY ?? "";

export const APP_NAME = "Avian Observatory";
export const APP_TAGLINE = "Acoustic intelligence for Northern Territory biodiversity";

/** Feature flags. The navigation should reflect what is genuinely usable today,
 *  so placeholder "Roadmap" modules (Behaviour, Migration, Pelican, Environmental,
 *  Sensors) are hidden by default. Their routes still exist; they are simply not
 *  advertised. Set NEXT_PUBLIC_SHOW_ROADMAP=true to reveal them (e.g. in dev). */
export const FEATURES = {
  roadmapModules: process.env.NEXT_PUBLIC_SHOW_ROADMAP === "true",
};
