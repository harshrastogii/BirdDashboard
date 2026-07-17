"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { API_BASE } from "@/lib/config";
import { apiFetch, qs } from "./client";
import type {
  Biodiversity, Detection, EnvironmentalLayers, MapSites, ModelComparison,
  ModelRegistry, MultiSpecies, NtPredictions, Page, Recording, ResearchMetrics,
  Site, Species, Version,
} from "./types";

/** Query-key factory (mirrors API resources). */
export const keys = {
  version: ["version"] as const,
  recordings: (cursor?: string, limit?: number) => ["recordings", { cursor, limit }] as const,
  recording: (id: string) => ["recording", id] as const,
  detections: (id: string, minConf: number) => ["detections", id, minConf] as const,
  ntPredictions: (id: string) => ["nt-predictions", id] as const,
  multiSpecies: (id: string) => ["multi-species", id] as const,
  species: (cursor?: string, limit?: number) => ["species", { cursor, limit }] as const,
  sites: ["sites"] as const,
  biodiversity: (minConf: number) => ["biodiversity", minConf] as const,
};

export function useVersion() {
  return useQuery({ queryKey: keys.version, queryFn: () => apiFetch<Version>("/api/v1/version") });
}

export function useRecordings(limit = 50, cursor?: string, site?: string) {
  return useQuery({
    queryKey: ["recordings", { cursor, limit, site }] as const,
    queryFn: () => apiFetch<Page<Recording>>(`/api/v1/recordings${qs({ limit, cursor, site })}`),
  });
}

export function useRecording(id: string) {
  return useQuery({
    queryKey: keys.recording(id),
    queryFn: () => apiFetch<Recording>(`/api/v1/recordings/${id}`),
    enabled: !!id,
  });
}

export function useDetections(id: string, minConfidence = 0.25) {
  return useQuery({
    queryKey: keys.detections(id, minConfidence),
    queryFn: () =>
      apiFetch<Detection[]>(
        `/api/v1/recordings/${id}/detections${qs({ min_confidence: minConfidence })}`,
      ),
    enabled: !!id,
  });
}

export function useSpecies(limit = 100, cursor?: string) {
  return useQuery({
    queryKey: keys.species(cursor, limit),
    queryFn: () => apiFetch<Page<Species>>(`/api/v1/species${qs({ limit, cursor })}`),
  });
}

export function useSites() {
  return useQuery({ queryKey: keys.sites, queryFn: () => apiFetch<Site[]>("/api/v1/sites") });
}

export function useMapSites(minConfidence = 0.25, species?: string | null) {
  return useQuery({
    queryKey: ["map-sites", minConfidence, species ?? null] as const,
    queryFn: () => apiFetch<MapSites>(
      `/api/v1/map/sites${qs({ min_confidence: minConfidence, species: species ?? undefined })}`),
  });
}

export function useEnvironmentalLayers() {
  return useQuery({
    queryKey: ["environmental-layers"] as const,
    queryFn: () => apiFetch<EnvironmentalLayers>("/api/v1/environmental/layers"),
  });
}

export function useNtPredictions(id: string) {
  return useQuery({
    queryKey: keys.ntPredictions(id),
    queryFn: () => apiFetch<NtPredictions>(`/api/v1/recordings/${id}/nt-predictions`),
    enabled: !!id,
    staleTime: 5 * 60_000,
  });
}

export interface MultiSpeciesParams {
  force?: boolean;
  primary_conf?: number;
  secondary_conf?: number;
  sensitivity?: number;
  overlap?: number;
  top_k?: number;
  suppress_primary?: boolean;
}

export function useMultiSpecies(id: string, params?: MultiSpeciesParams | null) {
  return useQuery({
    queryKey: ["multi-species", id, params ?? null] as const,
    queryFn: () =>
      apiFetch<MultiSpecies>(`/api/v1/recordings/${id}/multi-species${qs({ ...(params ?? {}) })}`),
    enabled: !!id,
    staleTime: 5 * 60_000,
  });
}

export function useBiodiversity(minConfidence = 0.25) {
  return useQuery({
    queryKey: keys.biodiversity(minConfidence),
    queryFn: () => apiFetch<Biodiversity>(`/api/v1/biodiversity${qs({ min_confidence: minConfidence })}`),
  });
}

export function useModelComparison() {
  return useQuery({
    queryKey: ["model-comparison"],
    queryFn: () => apiFetch<ModelComparison>("/api/v1/models/comparison"),
    staleTime: 5 * 60_000,
  });
}

export function useResearchMetrics() {
  return useQuery({
    queryKey: ["research-metrics"],
    queryFn: () => apiFetch<ResearchMetrics>("/api/v1/models/research-metrics"),
    staleTime: 60 * 60_000,
  });
}

export function useModelRegistry() {
  return useQuery({
    queryKey: ["model-registry"],
    queryFn: () => apiFetch<ModelRegistry>("/api/v1/models/registry"),
    staleTime: 60 * 60_000,
  });
}

/** Upload a recording (restores the original Streamlit upload); analyses it
 *  with BirdNET server-side, then refreshes the library. */
export function useUploadRecording() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File): Promise<Recording> => {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${API_BASE}/api/v1/recordings/upload`, { method: "POST", body: fd });
      if (!res.ok) {
        const p = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(p.detail || "Upload failed");
      }
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recordings"] }),
  });
}
