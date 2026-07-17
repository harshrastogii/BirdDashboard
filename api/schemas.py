"""
Pydantic DTOs — the stable API contract.

These are deliberately separate from the ORM models and from birddash's
internal shapes (DataFrames). Clients depend on THESE; internals can change
freely as long as the DTOs stay backwards-compatible (additive evolution).
"""

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# --- Pagination envelope -------------------------------------------------
class Page(BaseModel, Generic[T]):
    """Cursor-paginated collection. `next_cursor` is opaque; pass it back as
    ?cursor= to fetch the next page. Null when there are no more items."""
    items: list[T]
    next_cursor: str | None = None
    limit: int


# --- Problem Details (RFC 9457) ------------------------------------------
class FieldError(BaseModel):
    field: str
    message: str


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    code: str | None = None
    errors: list[FieldError] | None = None
    request_id: str | None = None


# --- Resource DTOs -------------------------------------------------------
class SpeciesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    common_name: str
    scientific_name: str | None = None
    class_index: int | None = None
    conservation_status: str | None = None


class ModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    key: str
    name: str
    version: str
    kind: str


class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organisation_id: UUID
    name: str
    latitude: float | None = None
    longitude: float | None = None
    recording_count: int = 0


# --- Map / GIS DTOs ------------------------------------------------------
class MapSiteOut(BaseModel):
    """A monitoring site as a map point, with the species detected there so the
    map can be filtered. `coordinate_precision` says whether the point is precise
    (per-recording GPS) or approximate (the site location)."""
    id: UUID
    name: str
    latitude: float | None
    longitude: float | None
    coordinate_precision: str            # precise | approximate | unknown
    coordinate_source: str               # recording_gps | site_association | none
    recording_count: int
    species_present: list[str]
    matched: bool                        # matches the active species filter (if any)


class MapSitesOut(BaseModel):
    min_confidence: float
    species_filter: str | None
    coordinate_precision_note: str
    sites: list[MapSiteOut]


# --- Environmental-layer DTOs (Stage 2 boundary; inert scaffold) ---------
class EnvironmentalLayer(BaseModel):
    key: str
    name: str
    category: str                        # fire | weather | vegetation | protected | ...
    available: bool
    planned_source: str | None = None    # e.g. "NAFI", "DEA Land Cover", "TerraIQ"


class EnvironmentalLayersOut(BaseModel):
    """Environmental map layers. The boundary exists so Stage-2 sources (open data
    now, TerraIQ later) plug in with no frontend change; today it is inert
    (`available=false`, empty layers). See DECISIONS.md D-21."""
    available: bool
    provider: str
    note: str
    layers: list[EnvironmentalLayer]


class EnvironmentalContextOut(BaseModel):
    """Environmental context for a site/region (fire history, weather, …).
    Inert until a provider is wired; returns `available=false` today."""
    available: bool
    provider: str
    note: str
    site_id: UUID | None = None
    context: dict = Field(default_factory=dict)


class RecordingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organisation_id: UUID
    site_id: UUID | None = None
    sensor_id: UUID | None = None
    filename: str
    media_type: str
    size_bytes: int | None = None
    duration_seconds: float | None = None
    captured_at: datetime | None = None
    created_at: datetime
    # Location, resolved by the coordinate provider (api/services/geospatial.py).
    # `coordinate_precision` is precise (per-recording GPS) | approximate (falls
    # back to the site) | unknown; additive fields, so older clients are unaffected.
    latitude: float | None = None
    longitude: float | None = None
    coordinate_precision: str | None = None
    coordinate_source: str | None = None
    # Convenience hypermedia links for clients.
    audio_url: str | None = None
    detections_url: str | None = None


class DetectionOut(BaseModel):
    """A single BirdNET detection window (read from filesystem in Phase 3a)."""
    recording_id: UUID
    start_seconds: float
    end_seconds: float
    common_name: str
    scientific_name: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = "birdnet"


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    recording_id: UUID
    model_id: UUID
    type: str
    params: dict
    status: str
    created_at: datetime


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    type: str
    status: str
    progress: int
    result_kind: str | None = None
    result_id: UUID | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class VersionOut(BaseModel):
    api_version: str          # package version
    api_major: str            # URL major, e.g. "v1"
    environment: str
    models: list[ModelOut]


# --- Analysis DTOs -------------------------------------------------------
class NtPredictionRow(BaseModel):
    """One NT CNN prediction: a species candidate for a 3s segment."""
    start_seconds: float
    end_seconds: float
    species: str
    confidence: float = Field(ge=0.0, le=1.0)
    rank: int


class NtPredictionsOut(BaseModel):
    recording_id: UUID
    model: str = "nt_cnn"
    predictions: list[NtPredictionRow]   # all top-5 rows per segment


class MultiSpeciesEvent(BaseModel):
    start: float
    end: float
    species: str
    confidence: float
    is_primary: bool


class MultiSpeciesOut(BaseModel):
    recording_id: UUID
    duration_seconds: float
    primary_species: str | None
    num_events: int
    unique_species: int
    events: list[MultiSpeciesEvent]
    parameters: dict
    cached: bool


class BiodiversityRecord(BaseModel):
    recording_id: UUID | None
    name: str
    species_richness: int
    shannon_index: float
    simpson_index: float
    total_detections: int


class BiodiversityOut(BaseModel):
    min_confidence: float
    overall_richness: int
    overall_shannon: float
    overall_simpson: float
    per_recording: list[BiodiversityRecord]


# --- Statistics DTOs (uncertainty on every reported estimate) ------------
class IntervalOut(BaseModel):
    """A two-sided confidence interval for a reported point estimate. `method`
    names the estimator (wilson | clopper_pearson | bootstrap_percentile);
    `reliable` is false when the interval is too wide to interpret the point
    estimate directly (see birddash.statistics / docs/METHODOLOGY.md)."""
    point: float
    low: float
    high: float
    confidence: float
    method: str
    width: float
    reliable: bool


class McNemarOut(BaseModel):
    """Exact McNemar paired-test result comparing two models on identical items.
    Only discordant pairs are informative; `significant_at_0_05` flags whether
    the difference is statistically significant."""
    only_a_correct: int            # a = NT correct, BirdNET wrong
    only_b_correct: int            # b = BirdNET correct, NT wrong
    n_discordant: int
    p_value: float
    significant_at_0_05: bool
    method: str


class ModelComparisonRecord(BaseModel):
    recording_id: UUID
    name: str
    ground_truth: str | None
    evaluated: bool                # scored (verified label + both models ran)
    birdnet_top: str | None
    birdnet_confidence: float | None
    birdnet_correct: bool | None
    nt_top: str | None             # NT Custom Classifier (v5) primary species
    nt_correct: bool | None


class ModelComparisonOut(BaseModel):
    """Aggregate story: the production NT Custom Classifier (v5, via the v5.2
    SED pipeline) vs the global BirdNET v2.4 baseline, both scored on exactly
    the same recordings by whether they detect each recording's true species.

    Every rate carries a Wilson confidence interval, the paired difference a
    McNemar test, and `provenance` records the sample size, ground-truth source,
    synonym handling, and method citations (additive fields; older clients that
    read only the counts keep working)."""
    birdnet_correct: int
    nt_correct: int
    total_with_ground_truth: int   # = recordings scored for BOTH models
    nt_interval: IntervalOut | None = None
    birdnet_interval: IntervalOut | None = None
    mcnemar: McNemarOut | None = None
    provenance: dict = Field(default_factory=dict)
    per_recording: list[ModelComparisonRecord]


class PerSpeciesMetric(BaseModel):
    species: str
    precision: float
    recall: float
    f1: float
    support: int
    auroc: float | None = None
    auprc: float | None = None
    # Exact (Clopper–Pearson) intervals + reliability flag — additive, present
    # once the evaluation artefacts include them.
    precision_ci: IntervalOut | None = None
    recall_ci: IntervalOut | None = None
    reliable: bool | None = None


class CurvePoint(BaseModel):
    x: float
    y: float


class ModelMetrics(BaseModel):
    """Fully reproducible, artefact-backed metrics for a model version — every
    value regenerated from persisted evaluation artefacts (traceable)."""
    version: str
    description: str
    accuracy: float
    macro_f1: float
    weighted_f1: float
    macro_auroc: float
    macro_auprc: float
    per_species: list[PerSpeciesMetric]
    roc_curve: list[CurvePoint]
    pr_curve: list[CurvePoint]
    provenance: dict
    # Bootstrap confidence intervals for the macro/aggregate metrics, keyed by
    # metric name (e.g. "accuracy", "macro_f1"). Additive; present once the
    # evaluation artefacts include them.
    macro_intervals: dict[str, IntervalOut] | None = None


class DocumentedMetrics(BaseModel):
    """Reported research values with NO traceable evaluation artefact."""
    label: str
    metrics: dict          # {metric name: value}
    source: str
    note: str


class ModelEvaluation(BaseModel):
    """One evaluation record for a model version."""
    id: str
    type: str              # original_evaluation | independent_reproduction
    title: str
    note: str
    available: bool        # whether the artefacts exist on disk
    metrics: ModelMetrics | None


class RegistryModel(BaseModel):
    key: str
    name: str
    version: str
    family: str
    status: str            # production | baseline | historical
    description: str
    documented: DocumentedMetrics | None
    evaluations: list[ModelEvaluation]


class ModelRegistryOut(BaseModel):
    """The versioned model registry: each model with its metadata, documented
    values, and evaluation history (original + independent reproductions),
    kept strictly distinct."""
    evaluation_types: dict
    models: list[RegistryModel]


class ResearchMetricsOut(BaseModel):
    """Research metrics with explicit provenance.

    - `cnn` and (when available) `v5_metrics` are VERIFIED — reproduced from
      persisted evaluation artefacts.
    - When no v5 evaluation artefact exists yet, `v5_metrics` is null and the
      DOCUMENTED thesis values (`v5_auprc`/`v5_auroc`, `v5_verified=False`) are
      returned instead, clearly flagged as not experimentally reproduced.

    The app automatically switches to `v5_metrics` once evaluation/v5/ exists."""
    cnn: ModelMetrics | None
    cnn_recording_level_accuracy: float | None   # v4 honest split, for context
    v5_metrics: ModelMetrics | None              # verified, when artefacts exist
    v5_auprc: float | None                        # documented fallback
    v5_auroc: float | None
    v5_verified: bool
    v5_note: str
