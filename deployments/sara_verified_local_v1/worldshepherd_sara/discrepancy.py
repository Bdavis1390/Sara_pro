from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


@dataclass(frozen=True)
class PairedMeasurement:
    key: str
    predicted: float
    measured: float
    uncertainty: float | None = None
    units: str | None = None


@dataclass(frozen=True)
class DiscrepancyMetric:
    key: str
    absolute_error: float
    relative_error: float | None
    normalized_error: float | None
    units: str | None


@dataclass(frozen=True)
class DiscrepancySummary:
    metrics: tuple[DiscrepancyMetric, ...]
    mean_absolute_error: float
    max_absolute_error: float
    mean_relative_error: float | None
    within_uncertainty_fraction: float | None


def compare_prediction_to_measurement(
    pairs: Iterable[PairedMeasurement],
) -> DiscrepancySummary:
    """Compare predicted vs measured values without upgrading either evidence class.

    This records discrepancy only. It does not establish model validity unless an
    external requirement defines acceptable thresholds and the measurement itself
    is trustworthy for the intended scope.
    """
    values = tuple(pairs)
    if not values:
        raise ValueError("at least one prediction/measurement pair is required")

    metrics: list[DiscrepancyMetric] = []
    relative_values: list[float] = []
    uncertainty_checks: list[bool] = []
    for pair in values:
        if not isfinite(pair.predicted) or not isfinite(pair.measured):
            raise ValueError(f"non-finite value for {pair.key}")
        error = abs(pair.predicted - pair.measured)
        relative = None if pair.measured == 0 else error / abs(pair.measured)
        normalized = None
        if pair.uncertainty is not None:
            if pair.uncertainty < 0 or not isfinite(pair.uncertainty):
                raise ValueError(f"invalid uncertainty for {pair.key}")
            normalized = 0.0 if pair.uncertainty == 0 and error == 0 else (
                None if pair.uncertainty == 0 else error / pair.uncertainty
            )
            uncertainty_checks.append(error <= pair.uncertainty)
        if relative is not None:
            relative_values.append(relative)
        metrics.append(
            DiscrepancyMetric(
                key=pair.key,
                absolute_error=error,
                relative_error=relative,
                normalized_error=normalized,
                units=pair.units,
            )
        )

    absolute = [metric.absolute_error for metric in metrics]
    return DiscrepancySummary(
        metrics=tuple(metrics),
        mean_absolute_error=sum(absolute) / len(absolute),
        max_absolute_error=max(absolute),
        mean_relative_error=(sum(relative_values) / len(relative_values)) if relative_values else None,
        within_uncertainty_fraction=(sum(1 for value in uncertainty_checks if value) / len(uncertainty_checks)) if uncertainty_checks else None,
    )
