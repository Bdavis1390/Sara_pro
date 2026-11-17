"""Research-only reference uncertainty metrics from supplied stochastic class scores.

The Shannon predictive entropy (PE) and epistemic mutual information (MI)
definitions are standard and discussed by van Lente et al., Front Oncol 2026,
DOI 10.3389/fonc.2025.1637198, and are also part of broader uncertainty-
quantification literature. This is NOT a reproduction of that paper's
segmentation model, calibration, patient cohort, clinical thresholds or results.

Input is a *single spatial item* / category probability vector from each
stochastic predictive pass; no model inference or imaging occurs here.
No evidence of biological measurement quality, dose calculation, treatment
authorization or vendor superiority is produced by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence, Literal

from .locked_risk_coverage import RiskScore

Metric = Literal["predictive_entropy", "mutual_information"]


@dataclass(frozen=True)
class StochasticUncertainty:
    passes: int
    classes: int
    mean_probabilities: tuple[float, ...]
    predictive_entropy: float
    expected_entropy: float
    mutual_information: float
    predictive_entropy_normalized: float
    mutual_information_normalized: float


def _entropy(probabilities: Sequence[float]) -> float:
    return -math.fsum(float(p) * math.log(float(p)) for p in probabilities if p > 0.0)


def measure_stochastic_uncertainty(
    stochastic_probabilities: Sequence[Sequence[float]],
    *,
    sum_tolerance: float = 1e-9,
) -> StochasticUncertainty:
    """Compute PE=H(E[p]) and MI=H(E[p])-E[H(p)] over stochastic passes.

    The normalization by log(K) is a generic mapping into [0,1] for use in a
    risk-score API. The cited paper's operational thresholding is NOT reproduced.
    """
    if not isinstance(sum_tolerance, (int, float)) or isinstance(sum_tolerance, bool):
        raise ValueError("sum_tolerance must be a finite positive real")
    if not math.isfinite(float(sum_tolerance)) or not 0.0 < float(sum_tolerance) <= 1e-5:
        raise ValueError("sum_tolerance must be a finite positive real <= 1e-5")

    rows = tuple(tuple(v for v in row) for row in stochastic_probabilities)
    if not 2 <= len(rows) <= 10_000:
        raise ValueError("require 2..10000 stochastic predictive passes")
    if not 2 <= len(rows[0]) <= 1024:
        raise ValueError("require 2..1024 prediction classes")
    k = len(rows[0])
    for row in rows:
        if len(row) != k:
            raise ValueError("all stochastic prediction vectors need equal class dimension")
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("each class probability must be a finite number")
            if not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
                raise ValueError("each class probability must be in [0,1]")
        if abs(math.fsum(float(p) for p in row) - 1.0) > sum_tolerance:
            raise ValueError("each class probability vector must sum to one")
    total_passes = len(rows)
    means = tuple(
        math.fsum(float(row[idx]) for row in rows) / total_passes
        for idx in range(k)
    )
    predictive = _entropy(means)
    expected = math.fsum(_entropy(row) for row in rows) / total_passes
    mi = predictive - expected
    if mi < 0.0 and mi > -1e-12:
        mi = 0.0
    if mi < 0.0:
        raise ValueError("negative mutual information beyond numerical tolerance")
    maximum = math.log(k)
    return StochasticUncertainty(
        passes=total_passes,
        classes=k,
        mean_probabilities=means,
        predictive_entropy=predictive,
        expected_entropy=expected,
        mutual_information=mi,
        predictive_entropy_normalized=min(1.0, max(0.0, predictive / maximum)),
        mutual_information_normalized=min(1.0, max(0.0, mi / maximum)),
    )


def as_locked_comparator_risk(
    case_id: str,
    measurement: StochasticUncertainty,
    *,
    metric: Metric,
) -> RiskScore:
    """Map a PRESELECTED entropy/MI metric into the generic risk interface.

    Risk means research uncertainty score, NOT probability of patient harm.
    The evaluator must select the metric and calibration before unblinding.
    """
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("case_id must be a non-empty synthetic or deidentified identifier")
    if metric == "predictive_entropy":
        value = measurement.predictive_entropy_normalized
    elif metric == "mutual_information":
        value = measurement.mutual_information_normalized
    else:
        raise ValueError("metric must be predictive_entropy or mutual_information")
    return RiskScore(case_id=case_id, risk=value)
