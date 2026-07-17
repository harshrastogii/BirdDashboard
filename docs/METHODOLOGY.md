# METHODOLOGY.md — Statistical & Nomenclatural Methods

> Phase 7 · Workstream B reference. The **why** and the **citation** behind every
> statistical method and synonym decision the platform uses to report metrics.
> Companion: [../SCIENTIFIC_METHOD.md](../SCIENTIFIC_METHOD.md) ·
> [../MODEL_REGISTRY.md](../MODEL_REGISTRY.md) · [../DECISIONS.md](../DECISIONS.md)
>
> Implementations: `birddash/statistics.py`, `birddash/taxonomy.py` (framework-free
> core). Every method below is exercised by the API (`/models/comparison`,
> `/models/registry`) and the evaluation scripts (`regenerate_cnn_evaluation.py`,
> `evaluate_v5.py`). This document is written to be reusable in Paper 1.

## Principle

Every number the platform reports is a statistic on a **finite** sample, and
several of those samples are small (the operational comparison has n≈23; some
held-out species have support of 1–2 recordings). A bare point estimate in that
regime is misleading because sampling uncertainty dominates. Accordingly, **every
reported estimate carries an appropriate uncertainty statement, and every method
is cited.** No number is presented without (a) its sample size and (b) either a
confidence interval or an explicit small-sample caveat.

---

## 1. Binomial proportion intervals — operational detection rates

**Where:** the NT-vs-BirdNET operational comparison (`/models/comparison`), each
model's "correct-detection rate" over the shared recordings.

**Method:** **Wilson score interval** (95%). `birddash.statistics.wilson_interval`.

**Why Wilson (rationale for Paper 1):** the textbook Wald (normal-approximation)
interval `p ± z·√(p(1−p)/n)` is known to have poor coverage for small n and for
proportions near 0 or 1, where it can fall outside [0, 1] or collapse to zero
width (e.g. at p = 1.0). The Wilson score interval inverts the score test,
stays within [0, 1], and has substantially better small-sample coverage. Brown,
Cai & DasGupta (2001) recommend it precisely for this regime. With n≈23 the
difference from Wald is material, so Wilson is the honest choice.

**Citations:**
- Wilson, E. B. (1927). Probable inference, the law of succession, and
  statistical inference. *JASA*, 22(158), 209–212.
- Brown, L. D., Cai, T. T., & DasGupta, A. (2001). Interval estimation for a
  binomial proportion. *Statistical Science*, 16(2), 101–133.

---

## 2. Paired model comparison — exact McNemar test

**Where:** whether the NT-vs-BirdNET difference in correct-detection rate is
statistically significant (`/models/comparison` → `mcnemar`).

**Method:** **exact (binomial) McNemar test**. `birddash.statistics.mcnemar_exact`.

**Why McNemar, and why exact (rationale):** the two models are evaluated on the
**same** recordings, so the two rates are **paired**, not independent — an
unpaired two-proportion z/χ² test is invalid here. Under McNemar's framing only
the *discordant* recordings (exactly one model correct) carry information about
which model is better; concordant recordings cancel. Under H₀ the number of
discordances of one type is Binomial(b+c, ½). Because the discordant count is
small (here b+c ≈ 7), the χ²-approximation form of McNemar's test is unreliable,
so we use the **exact binomial** two-sided p-value.

**Interpretation adopted:** at n≈23 the test typically returns **not
significant** — the point estimates favour the NT model, but the sample is too
small to rule out sampling variation. The platform surfaces this non-significance
as prominently as it would a significant result: a direction-of-effect claim and
a statistical-significance claim are kept distinct.

**Citations:**
- McNemar, Q. (1947). Note on the sampling error of the difference between
  correlated proportions or percentages. *Psychometrika*, 12(2), 153–157.
- Edwards, A. L. (1948). Note on the "correction for continuity"… *Psychometrika*,
  13(3), 185–187. (Basis for the exact/binomial form.)

---

## 3. Per-class precision & recall — exact (Clopper–Pearson) intervals

**Where:** per-species precision/recall in every held-out evaluation
(`/models/registry` → each model's `per_species`), for both the CNN
(`regenerate_cnn_evaluation.py`) and the v5 reproduction (`evaluate_v5.py`).

**Method:** **Clopper–Pearson "exact" binomial interval** (95%), via the
Beta-quantile form. `birddash.statistics.clopper_pearson`. Recall's denominator
is the class **support** (number of true instances); precision's denominator is
the number **predicted** as that class.

**Why Clopper–Pearson (rationale):** with support of 1–2 recordings a per-class
recall of "1.000" is almost meaningless — one observation cannot establish a rate.
Clopper–Pearson guarantees at-least-nominal coverage (it is deliberately
conservative), so for support = 1 it correctly returns a near-[0, 1] interval.
That enormous width **is the honest signal**: it tells the reader the point
estimate is uninformative, replacing false precision with visible uncertainty.

**Citation:**
- Clopper, C. J., & Pearson, E. S. (1934). The use of confidence or fiducial
  limits illustrated in the case of the binomial. *Biometrika*, 26(4), 404–413.

### 3a. Small-sample reliability flag (a *derived* criterion, not a fixed n)

Each per-class row carries `reliable: bool`. Rather than an arbitrary minimum
sample size (e.g. "hide n < 5"), reliability is defined **by the precision of the
estimate itself**: a class is flagged *not reliable* when its 95% interval is
wider than **0.5** — i.e. it spans more than half of the [0, 1] range and so
conveys little about the true rate (`DEFAULT_MAX_RELIABLE_WIDTH` in
`birddash.statistics`). Sample size enters only through the interval width, so
the rule scales naturally (support 1 → width ≈ 0.97 → unreliable; a class with
many observations and a tight interval → reliable). This is the "justified
threshold rather than a fixed value" the project requires. The UI marks flagged
classes (†) and mutes them; aggregate macro metrics are still reported but read
against the interval below.

---

## 4. Aggregate metrics — percentile bootstrap intervals

**Where:** accuracy and macro-F1 for each held-out evaluation
(`/models/registry` → `macro_intervals`).

**Method:** **percentile bootstrap** (95%, 2,000 resamples, seeded).
`birddash.statistics.bootstrap_ci`.

**Why the bootstrap, and why the resampling unit matters (rationale):** macro-F1
and accuracy have no simple closed-form interval, so we resample the observed
units with replacement and read the 2.5/97.5 percentiles of the statistic's
bootstrap distribution. Crucially, **the resampling unit is the independent unit
of observation**: for the recording-level held-out v5 evaluation that is the
*recording* (each row is a recording-level mean), so the interval reflects
recording-level — not segment-level — sampling variability. Resampling at the
wrong level (segments that share a recording) would understate uncertainty and
repeat the very leakage error that v4 exposed. The interval is seeded, so it is
exactly reproducible.

**Citations:**
- Efron, B. (1979). Bootstrap methods: another look at the jackknife.
  *Annals of Statistics*, 7(1), 1–26.
- Efron, B., & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*.
  Chapman & Hall. (Percentile method, §13.)

---

## 5. Synonym handling — nomenclatural equivalence

**Where:** ground-truth matching in the operational comparison
(`birddash.taxonomy`, mirrored in `frontend/lib/ground-truth.ts`).

**Method:** two-stage name resolution — (1) normalisation collapses orthographic
variants (hyphen/space/case); (2) a small, **sourced** synonym table maps true
cross-checklist synonyms to a study-canonical name. `same_species(a, b)`.

**Why, and why deliberately conservative (rationale):** one biological species can
carry different accepted common names across checklists. The case in this dataset
is the IOC name **"Bush Thick-knee"** for the Australian **"Bush Stone-curlew"**
(*Burhinus grallarius*); BirdNET emits the IOC name, so a naive string match
scored a correct BirdNET detection as a miss. Counting it correctly is more
honest **and slightly reduces the NT model's apparent lead** — which is the point:
the synonym table exists to remove a bias in *our own model's favour*, not to
inflate it. For that reason entries are admitted **only** with a checklist
citation, and BirdNET *misidentifications* (e.g. Azure Kingfisher → "Eurasian
Treecreeper") are never added — they are wrong answers and remain misses. Adding
an unsourced entry would silently inflate measured accuracy, so the table is kept
minimal and sourced.

**Measured effect:** enabling synonym handling moved BirdNET from 17/23 to 18/23
on the current data (one correct detection previously mis-scored); it did not
change the NT model. (The NT model separately rose from 21/23 to **23/23** after a
name-truncation parsing bug was fixed in the SED pipeline — see MODEL_REGISTRY.md
and `tests/test_detection_parsing.py`; that is a parsing fix, not a synonym effect.)

**Sources:**
- Gill, F., Donsker, D., & Rasmussen, P. (Eds). *IOC World Bird List* (v14).
  worldbirdnames.org — "Bush Thick-knee".
- BirdLife Australia, *Working List of Australian Birds* (v4) — "Bush Stone-curlew".
- Kahl, S., et al. (2021). BirdNET: A deep learning solution for avian diversity
  monitoring. *Ecological Informatics*, 61, 101236.

---

## 6. Provenance on every reported metric

Consistent with DECISIONS.md D-12/D-13, each metric surfaced by the API carries an
explicit provenance tag so its epistemic status is never ambiguous:

| Tag | Meaning | Interval method |
|---|---|---|
| `documented` | Reported (thesis/README), no traceable artefact — e.g. v5 AUPRC 0.98/AUROC 0.99 | none (not verified) |
| `original_evaluation` | Recomputed from original saved arrays (CNN) | Clopper–Pearson (per-class) + bootstrap (macro) |
| `independent_reproduction` | New held-out experiment (v5) | Clopper–Pearson (per-class) + bootstrap (macro) |
| `live_comparison` | Per-recording detection test (NT vs BirdNET) | Wilson (rate) + exact McNemar (paired) |

`documented` values are always shown behind a "Documented · not verified" badge in
the UI; they are never presented with a confidence interval, because no evaluation
sample underlies them.

---

## Reproducibility

All intervals are deterministic: closed-form (Wilson, Clopper–Pearson) or seeded
(bootstrap, seed 42). The CNN and v5 statistics are recomputable from persisted
arrays with **no retraining** — `python regenerate_cnn_evaluation.py` and
`python evaluate_v5.py --from-saved` — so every figure and table in Paper 1 can be
regenerated from the repository. The `--from-saved` path was added specifically to
honour the owner's pause on v5 retraining while still producing the uncertainty
statistics from the existing held-out experiment's saved outputs.
