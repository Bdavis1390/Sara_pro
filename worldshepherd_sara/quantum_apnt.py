"""Truth-referenced evaluation harness for APNT quantum-sensor evidence.

The harness is modality-agnostic and accepts calibrated sensor/reference series.
Synthetic tests validate the software only; mission readiness still requires a named
sensor, calibration, truth reference, degraded-state trials, and environment evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import cos, sin, sqrt
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


@dataclass(frozen=True)
class APNTSyntheticBenchmark:
    benchmark_id: str
    evidence_level: str
    sample_count_total: int
    normalized_units: str
    tolerance: float
    truth_digest: str
    measured_digest: str
    dropout_indices: tuple[int, ...]
    model_parameters: dict[str, float]
    metrics: APNTSensorMetrics
    acceptance_criteria: dict[str, float]
    accepted: bool
    precondition_id: str
    claim_control: str


def _digest_json(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


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


def run_synthetic_apnt_benchmark(*, sample_count: int = 128) -> APNTSyntheticBenchmark:
    """Run a deterministic, normalized APNT sensor/error benchmark.

    This is deliberately not calibrated to any commercial quantum sensor. It exists
    only to freeze Worldshepherd's truth-reference, dropout, bias/drift, residual, and
    acceptance plumbing before external sensor data is admitted.
    """
    if sample_count < 64:
        raise ValueError("synthetic APNT benchmark requires at least 64 samples")

    parameters = {
        "bias": 0.08,
        "drift_per_sample": 0.0007,
        "periodic_error_amplitude": 0.06,
        "secondary_error_amplitude": 0.025,
    }
    truth = [
        2.0 * sin(i / 13.0) + 0.65 * cos(i / 29.0) + 0.003 * i
        for i in range(sample_count)
    ]
    dropout_indices = tuple(i for i in range(sample_count) if i % 37 == 11 or i % 53 == 19)
    dropout_set = set(dropout_indices)
    measured: list[float | None] = []
    for i, reference in enumerate(truth):
        if i in dropout_set:
            measured.append(None)
            continue
        error = (
            parameters["bias"]
            + parameters["drift_per_sample"] * i
            + parameters["periodic_error_amplitude"] * sin(i * 0.71)
            + parameters["secondary_error_amplitude"] * cos(i * 0.19)
        )
        measured.append(reference + error)

    tolerance = 0.25
    metrics = evaluate_sensor_series(measured, truth, tolerance=tolerance)
    criteria = {
        "minimum_availability": 0.95,
        "maximum_rmse": 0.20,
        "maximum_abs_bias": 0.15,
        "minimum_within_tolerance_fraction": 0.98,
        "maximum_abs_drift_per_sample": 0.002,
    }
    accepted = (
        metrics.availability >= criteria["minimum_availability"]
        and metrics.rmse <= criteria["maximum_rmse"]
        and abs(metrics.bias) <= criteria["maximum_abs_bias"]
        and metrics.within_tolerance_fraction >= criteria["minimum_within_tolerance_fraction"]
        and abs(metrics.drift_per_sample) <= criteria["maximum_abs_drift_per_sample"]
    )
    return APNTSyntheticBenchmark(
        benchmark_id="WS-APNT-SYN-001",
        evidence_level="synthetic_surrogate",
        sample_count_total=sample_count,
        normalized_units="normalized_test_units_not_physical_navigation_units",
        tolerance=tolerance,
        truth_digest=_digest_json(truth),
        measured_digest=_digest_json(measured),
        dropout_indices=dropout_indices,
        model_parameters=parameters,
        metrics=metrics,
        acceptance_criteria=criteria,
        accepted=accepted,
        precondition_id="WS-APNT-P0-SIMULATED-SENSOR-BENCHMARK",
        claim_control=(
            "WS-APNT-SYN-001 is a deterministic software/synthetic benchmark in normalized units. "
            "It validates truth-reference metrics, dropout handling, drift/error reporting, digests, and gate plumbing only. "
            "It is not calibrated sensor evidence and cannot establish APNT accuracy, quantum advantage, hardware readiness, or mission suitability."
        ),
    )


def synthetic_apnt_benchmark_as_dict(*, sample_count: int = 128) -> dict[str, object]:
    return asdict(run_synthetic_apnt_benchmark(sample_count=sample_count))
