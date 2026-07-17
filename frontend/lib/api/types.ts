/**
 * API contract types — mirror the FastAPI Pydantic DTOs (api/schemas.py).
 *
 * In production these are generated from the live /openapi.json via
 * openapi-typescript; hand-authored here to keep the frontend build free of a
 * running-server dependency. Keep in sync with the API contract.
 */

export interface Page<T> {
  items: T[];
  next_cursor: string | null;
  limit: number;
}

export interface Recording {
  id: string;
  organisation_id: string;
  site_id: string | null;
  sensor_id: string | null;
  filename: string;
  media_type: string;
  size_bytes: number | null;
  duration_seconds: number | null;
  captured_at: string | null;
  created_at: string;
  latitude: number | null;
  longitude: number | null;
  coordinate_precision: string | null;   // precise | approximate | unknown
  coordinate_source: string | null;
  audio_url: string | null;
  detections_url: string | null;
}

export interface Detection {
  recording_id: string;
  start_seconds: number;
  end_seconds: number;
  common_name: string;
  scientific_name: string | null;
  confidence: number;
  source: string;
}

export interface Species {
  id: string;
  common_name: string;
  scientific_name: string | null;
  class_index: number | null;
  conservation_status: string | null;
}

export interface Site {
  id: string;
  organisation_id: string;
  name: string;
  latitude: number | null;
  longitude: number | null;
  recording_count: number;
}

/** A site rendered as a filterable map point. `coordinate_precision` says
 *  whether the location is precise (per-recording GPS) or approximate (site). */
export interface MapSite {
  id: string;
  name: string;
  latitude: number | null;
  longitude: number | null;
  coordinate_precision: "precise" | "approximate" | "unknown" | string;
  coordinate_source: string;
  recording_count: number;
  species_present: string[];
  matched: boolean;
}

export interface MapSites {
  min_confidence: number;
  species_filter: string | null;
  coordinate_precision_note: string;
  sites: MapSite[];
}

export interface EnvironmentalLayer {
  key: string;
  name: string;
  category: string;
  available: boolean;
  planned_source: string | null;
}

export interface EnvironmentalLayers {
  available: boolean;
  provider: string;
  note: string;
  layers: EnvironmentalLayer[];
}

export interface Job {
  id: string;
  type: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: number;
  result_kind: string | null;
  result_id: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface Model {
  id: string;
  key: string;
  name: string;
  version: string;
  kind: string;
}

export interface Version {
  api_version: string;
  api_major: string;
  environment: string;
  models: Model[];
}

export interface Problem {
  type: string;
  title: string;
  status: number;
  detail: string | null;
  code: string | null;
  request_id: string | null;
}

export interface NtPredictionRow {
  start_seconds: number;
  end_seconds: number;
  species: string;
  confidence: number;
  rank: number;
}

export interface NtPredictions {
  recording_id: string;
  model: string;
  predictions: NtPredictionRow[];
}

export interface MultiSpeciesEvent {
  start: number;
  end: number;
  species: string;
  confidence: number;
  is_primary: boolean;
}

export interface MultiSpecies {
  recording_id: string;
  duration_seconds: number;
  primary_species: string | null;
  num_events: number;
  unique_species: number;
  events: MultiSpeciesEvent[];
  parameters: Record<string, unknown>;
  cached: boolean;
}

export interface BiodiversityRecord {
  recording_id: string | null;
  name: string;
  species_richness: number;
  shannon_index: number;
  simpson_index: number;
  total_detections: number;
}

export interface Biodiversity {
  min_confidence: number;
  overall_richness: number;
  overall_shannon: number;
  overall_simpson: number;
  per_recording: BiodiversityRecord[];
}

export interface ModelComparisonRecord {
  recording_id: string;
  name: string;
  ground_truth: string | null;
  evaluated: boolean;
  birdnet_top: string | null;
  birdnet_confidence: number | null;
  birdnet_correct: boolean | null;
  nt_top: string | null;
  nt_correct: boolean | null;
}

/** A two-sided confidence interval for a reported point estimate. `reliable` is
 *  false when the interval is too wide to interpret the point directly. */
export interface Interval {
  point: number;
  low: number;
  high: number;
  confidence: number;
  method: string;
  width: number;
  reliable: boolean;
}

/** Exact McNemar paired-test result comparing two models on identical items. */
export interface McNemar {
  only_a_correct: number;
  only_b_correct: number;
  n_discordant: number;
  p_value: number;
  significant_at_0_05: boolean;
  method: string;
}

export interface ModelComparison {
  birdnet_correct: number;
  nt_correct: number;
  total_with_ground_truth: number;
  nt_interval: Interval | null;
  birdnet_interval: Interval | null;
  mcnemar: McNemar | null;
  provenance: Record<string, unknown>;
  per_recording: ModelComparisonRecord[];
}

export interface PerSpeciesMetric {
  species: string;
  precision: number;
  recall: number;
  f1: number;
  support: number;
  auroc: number | null;
  auprc: number | null;
  precision_ci: Interval | null;
  recall_ci: Interval | null;
  reliable: boolean | null;
}

export interface CurvePoint {
  x: number;
  y: number;
}

export interface ModelMetrics {
  version: string;
  description: string;
  accuracy: number;
  macro_f1: number;
  weighted_f1: number;
  macro_auroc: number;
  macro_auprc: number;
  per_species: PerSpeciesMetric[];
  roc_curve: CurvePoint[];
  pr_curve: CurvePoint[];
  provenance: Record<string, unknown>;
  macro_intervals: Record<string, Interval> | null;
}

export interface ResearchMetrics {
  cnn: ModelMetrics | null;
  cnn_recording_level_accuracy: number | null;
  v5_metrics: ModelMetrics | null;
  v5_auprc: number | null;
  v5_auroc: number | null;
  v5_verified: boolean;
  v5_note: string;
}

export interface DocumentedMetrics {
  label: string;
  metrics: Record<string, number>;
  source: string;
  note: string;
}

export interface ModelEvaluation {
  id: string;
  type: "original_evaluation" | "independent_reproduction" | string;
  title: string;
  note: string;
  available: boolean;
  metrics: ModelMetrics | null;
}

export interface RegistryModel {
  key: string;
  name: string;
  version: string;
  family: string;
  status: "production" | "baseline" | "historical" | string;
  description: string;
  documented: DocumentedMetrics | null;
  evaluations: ModelEvaluation[];
}

export interface ModelRegistry {
  evaluation_types: Record<string, string>;
  models: RegistryModel[];
}
