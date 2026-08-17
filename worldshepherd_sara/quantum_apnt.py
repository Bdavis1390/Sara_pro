"""Truth-referenced evaluation harness for APNT quantum-sensor evidence.

The harness is modality-agnostic and accepts calibrated sensor/reference series.
Synthetic tests validate the software only; mission readiness still requires a named
sensor, calibration, truth reference, degraded-state trials, and environment evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import sqrt
from typing import Sequence


@dataclass(frozen=True)
class APNTSensorMetrics:
    sample_count: int
    availability: float
    bias: float
    rmse: float
    mae: float
    max_abs_error: float
    drift_per_sample: float
    residual_stddev: float
    within_tolerance_fraction: float
    tolerance: float
    evidence_digest: str
    mission_use_decision: str


def evaluate_sensor_series(
    measured: Sequence[float | None],
    truth: Sequence[float],
    *,
    tolerance: float,
) -> APNTSensorMetrics:
    if len(measured) != len(truth) or len(truth) < 3:
        raise ValueError("measured/truth series must have equal length >= 3")
    if tolerance <= 0:
        raise ValueError("tolerance must be positive")

    valid = [(i, float(value), float(truth[i])) for i, value in enumerate(measured) if value is not None]
    if len(valid) < 2:
        raise ValueError("at least two valid sensor samples are required")

    errors = [value - reference for _, value, reference in valid]
    n = len(errors)
    bias = sum(errors) / n
    rmse = sqrt(sum(error * error for error in errors) / n)
    mae = sum(abs(error) for error in errors) / n
    max_abs = max(abs(error) for error in errors)
    residual_stddev = sqrt(sum((error - bias) ** 2 for error in errors) / n)
    within = sum(abs(error) <= tolerance for error in errors) / n

    xs = [float(index) for index, _, _ in valid]
    xbar = sum(xs) / n
    denominator = sum((x - xbar) ** 2 for x in xs)
    drift = 0.0 if denominator == 0 else sum((x - xbar) * (e - bias) for x, e in zip(xs, errors)) / denominator

    payload = {
        "sample_count": n,
        "availability": n / len(truth),
        "bias": bias,
        "rmse": rmse,
        "mae": mae,
        "max_abs_error": max_abs,
        "drift_per_sample": drift,
        "residual_stddev": residual_stddev,
        "within_tolerance_fraction": within,
        "tolerance": tolerance,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return APNTSensorMetrics(
        **payload,
        evidence_digest=f"sha256:{digest}",
        mission_use_decision="NO_GO_BELOW_97_UNTIL_CALIBRATED_EXTERNAL_SENSOR_EVIDENCE",
    )
