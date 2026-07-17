"""
Small-sample statistics for honest metric reporting — framework-free core.

Every estimate the platform reports (a detection rate, a per-class precision or
recall) is a statistic computed on a *finite* sample, and several of those
samples are small (the operational comparison has n≈23; some held-out species
have support of 1–2 recordings). Reporting a bare point estimate in that regime
is misleading: the sampling uncertainty dominates. This module supplies the
interval estimators and paired-difference test used throughout the platform so
that every reported number can carry an appropriate uncertainty statement.

Each function documents the methodology and its citation. Implementations use
only NumPy + SciPy (already dependencies); no `statsmodels` is required.

References
----------
Wilson, E. B. (1927). "Probable inference, the law of succession, and
    statistical inference." *Journal of the American Statistical Association*,
    22(158), 209–212. https://doi.org/10.2307/2276774
Clopper, C. J., & Pearson, E. S. (1934). "The use of confidence or fiducial
    limits illustrated in the case of the binomial." *Biometrika*, 26(4),
    404–413. https://doi.org/10.2307/2331986
McNemar, Q. (1947). "Note on the sampling error of the difference between
    correlated proportions or percentages." *Psychometrika*, 12(2), 153–157.
    https://doi.org/10.1007/BF02295996
Edwards, A. L. (1948). "Note on the 'correction for continuity' in testing the
    significance of the difference between correlated proportions."
    *Psychometrika*, 13(3), 185–187. (Exact/binomial form of McNemar's test.)
Efron, B. (1979). "Bootstrap methods: another look at the jackknife."
    *The Annals of Statistics*, 7(1), 1–26.
Efron, B., & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*.
    Chapman & Hall. (Percentile-interval method, §13.)
Brown, L. D., Cai, T. T., & DasGupta, A. (2001). "Interval estimation for a
    binomial proportion." *Statistical Science*, 16(2), 101–133. (Reviews why
    Wilson is preferred over the Wald interval for small n.)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
from scipy import stats

# The default reliability guard for a per-class interval. A 95% interval wider
# than this (i.e. spanning more than half of the [0,1] range) conveys almost no
# information about the true rate, so the point estimate should be treated as
# indicative only. This is a *derived* precision criterion, not an arbitrary
# minimum sample size: n enters only through the interval width. See
# docs/METHODOLOGY.md §"Small-sample reliability".
DEFAULT_MAX_RELIABLE_WIDTH = 0.5


@dataclass(frozen=True)
class Interval:
    """A two-sided confidence interval for a point estimate."""
    point: float
    low: float
    high: float
    confidence: float
    method: str

    @property
    def width(self) -> float:
        return self.high - self.low

    def reliable(self, max_width: float = DEFAULT_MAX_RELIABLE_WIDTH) -> bool:
        """True when the interval is tight enough for the point estimate to be
        interpreted directly (see DEFAULT_MAX_RELIABLE_WIDTH)."""
        return bool(self.width <= max_width)

    def as_dict(self) -> dict:
        # Cast to native Python types so the result is JSON-serialisable
        # (SciPy/NumPy return np.float64, which json.dumps cannot encode).
        return {
            "point": round(float(self.point), 4),
            "low": round(float(self.low), 4),
            "high": round(float(self.high), 4),
            "confidence": float(self.confidence),
            "method": self.method,
            "width": round(float(self.width), 4),
            "reliable": self.reliable(),
        }


def _z(confidence: float) -> float:
    return float(stats.norm.ppf(1 - (1 - confidence) / 2))


def wilson_interval(successes: int, n: int, confidence: float = 0.95) -> Interval:
    """Wilson score interval for a binomial proportion (Wilson, 1927).

    Preferred over the Wald (normal-approximation) interval for small n and for
    proportions near 0 or 1: it stays within [0, 1], has better coverage, and is
    never degenerate (a Wald interval collapses to zero width at p=0 or p=1).
    Used for the operational NT-vs-BirdNET detection rates (small n). See Brown,
    Cai & DasGupta (2001) for the coverage comparison.
    """
    if n <= 0:
        return Interval(0.0, 0.0, 1.0, confidence, "wilson")
    z = _z(confidence)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return Interval(p, max(0.0, center - half), min(1.0, center + half), confidence, "wilson")


def clopper_pearson(successes: int, n: int, confidence: float = 0.95) -> Interval:
    """Clopper–Pearson 'exact' binomial confidence interval (Clopper & Pearson,
    1934), computed via the Beta-quantile form.

    Guarantees at-least-nominal coverage (conservative). Used for per-class
    precision/recall where support is small: with support of 1–2 the interval is
    correctly enormous, which is exactly the honest signal we want to surface
    rather than a falsely precise 1.000.
    """
    if n <= 0:
        return Interval(0.0, 0.0, 1.0, confidence, "clopper_pearson")
    alpha = 1 - confidence
    p = successes / n
    low = 0.0 if successes == 0 else float(stats.beta.ppf(alpha / 2, successes, n - successes + 1))
    high = 1.0 if successes == n else float(stats.beta.ppf(1 - alpha / 2, successes + 1, n - successes))
    return Interval(p, low, high, confidence, "clopper_pearson")


@dataclass(frozen=True)
class McNemarResult:
    """Outcome of an exact McNemar paired test on two models' correctness."""
    n_discordant: int          # b + c: recordings where the models disagreed
    only_a_correct: int        # b: model A correct, model B wrong
    only_b_correct: int        # c: model B correct, model A wrong
    p_value: float
    method: str = "mcnemar_exact_binomial"

    def as_dict(self) -> dict:
        return {
            "only_a_correct": self.only_a_correct,
            "only_b_correct": self.only_b_correct,
            "n_discordant": self.n_discordant,
            "p_value": round(self.p_value, 4),
            "significant_at_0_05": self.p_value < 0.05,
            "method": self.method,
        }


def mcnemar_exact(only_a_correct: int, only_b_correct: int) -> McNemarResult:
    """Exact (binomial) McNemar test for two models scored on the SAME items
    (McNemar, 1947; exact form per Edwards, 1948).

    When comparing two classifiers on identical recordings the observations are
    *paired*, so an unpaired two-proportion test is invalid — only the discordant
    pairs (one model right, the other wrong) carry information about which is
    better. Under H0 (the two models are equally likely to be the one that's
    right on a discordant pair) the count of one type of discordance is
    Binomial(b+c, 0.5); the exact two-sided p-value avoids the chi-square
    approximation, which is unreliable for the small discordant counts here.
    """
    b, c = only_a_correct, only_b_correct
    n = b + c
    if n == 0:
        return McNemarResult(0, b, c, 1.0)
    p = float(stats.binomtest(min(b, c), n, 0.5, alternative="two-sided").pvalue)
    return McNemarResult(n, b, c, p)


def bootstrap_ci(
    values: Sequence[float] | np.ndarray,
    statistic: Callable[[np.ndarray], float],
    confidence: float = 0.95,
    n_resamples: int = 2000,
    seed: int = 42,
) -> Interval:
    """Percentile bootstrap confidence interval (Efron, 1979; Efron &
    Tibshirani, 1993, §13).

    A distribution-free interval for an aggregate statistic (e.g. a macro-average
    over per-recording results) obtained by resampling the observed units with
    replacement. Used for macro metrics where no closed-form interval exists.
    The resampling unit must be the independent unit of observation — for
    recording-level held-out evaluation that is the *recording*, so that the
    interval reflects recording-level (not segment-level) sampling variability.
    Deterministic given `seed`, so the interval is reproducible.
    """
    arr = np.asarray(values, dtype=float)
    point = float(statistic(arr))
    if arr.size == 0:
        return Interval(point, 0.0, 1.0, confidence, "bootstrap_percentile")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, arr.size, size=(n_resamples, arr.size))
    stats_dist = np.array([statistic(arr[i]) for i in idx])
    alpha = 1 - confidence
    low = float(np.quantile(stats_dist, alpha / 2))
    high = float(np.quantile(stats_dist, 1 - alpha / 2))
    return Interval(point, low, high, confidence, "bootstrap_percentile")
