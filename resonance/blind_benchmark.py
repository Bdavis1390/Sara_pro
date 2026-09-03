#!/usr/bin/env python3
"""Blind synthetic benchmark for conventional resonance-frequency diagnostics.

The analyzer receives only sampled time-series data. Ground truth is retained by
the benchmark harness and used only after estimation. This is an internal
synthetic software benchmark, not an instrumented physical test.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

SAMPLE_RATE_HZ = 256.0
DURATION_S = 8.0
FREQ_MIN_HZ = 2.0
FREQ_MAX_HZ = 60.0
TOLERANCE_HZ = 0.25

CASES = [
    {"id": "R01", "truth_hz": 7.0, "seed": 95301},
    {"id": "R02", "truth_hz": 12.5, "seed": 95302},
    {"id": "R03", "truth_hz": 19.0, "seed": 95303},
    {"id": "R04", "truth_hz": 27.5, "seed": 95304},
    {"id": "R05", "truth_hz": 41.0, "seed": 95305},
]


def generate_signal(truth_hz: float, seed: int) -> list[float]:
    rng = random.Random(seed)
    count = int(SAMPLE_RATE_HZ * DURATION_S)
    phase = rng.uniform(0.0, 2.0 * math.pi)
    secondary_hz = max(FREQ_MIN_HZ, truth_hz * 0.57)
    values = []
    for i in range(count):
        t = i / SAMPLE_RATE_HZ
        dominant = 1.0 * math.sin(2.0 * math.pi * truth_hz * t + phase)
        secondary = 0.22 * math.sin(2.0 * math.pi * secondary_hz * t + 0.4)
        noise = rng.gauss(0.0, 0.18)
        values.append(dominant + secondary + noise)
    return values


def estimate_dominant_frequency(samples: list[float]) -> float:
    """Estimate the dominant frequency without access to ground truth."""
    n = len(samples)
    mean = sum(samples) / n
    centered = [x - mean for x in samples]
    resolution_hz = SAMPLE_RATE_HZ / n
    k_min = max(1, math.ceil(FREQ_MIN_HZ / resolution_hz))
    k_max = min(n // 2 - 1, math.floor(FREQ_MAX_HZ / resolution_hz))

    best_k = k_min
    best_power = -1.0
    for k in range(k_min, k_max + 1):
        re = 0.0
        im = 0.0
        step = 2.0 * math.pi * k / n
        for idx, x in enumerate(centered):
            angle = step * idx
            re += x * math.cos(angle)
            im -= x * math.sin(angle)
        power = re * re + im * im
        if power > best_power:
            best_power = power
            best_k = k
    return best_k * resolution_hz


def main() -> int:
    out = Path(__file__).resolve().parent / "evidence"
    out.mkdir(parents=True, exist_ok=True)

    results = []
    errors = []
    for case in CASES:
        samples = generate_signal(case["truth_hz"], case["seed"])
        estimate = estimate_dominant_frequency(samples)
        abs_error = abs(estimate - case["truth_hz"])
        passed = abs_error <= TOLERANCE_HZ
        results.append({
            "case_id": case["id"],
            "estimated_hz": round(estimate, 6),
            "absolute_error_hz": round(abs_error, 6),
            "passed": passed,
        })
        errors.append(abs_error)

    pass_count = sum(1 for r in results if r["passed"])
    ordered = sorted(errors)
    median_error = ordered[len(ordered) // 2]
    report = {
        "schema": "WS-RESONANCE-BLIND-DIAGNOSTIC-BENCHMARK-V1",
        "evidence_class": "INTERNAL_TEST_ON_SYNTHETIC_DATA",
        "blindness_rule": "The estimator receives sampled signal values only; truth frequencies are supplied only to the post-estimation scorer.",
        "case_count": len(CASES),
        "pass_count": pass_count,
        "tolerance_hz": TOLERANCE_HZ,
        "median_absolute_error_hz": round(median_error, 6),
        "max_absolute_error_hz": round(max(errors), 6),
        "results": results,
        "result": "PASS" if pass_count == len(CASES) else "FAIL",
        "claims_boundary": "This closes only a fixture-scoped blind conventional frequency-diagnostic software benchmark. It is not a five-repeat instrumented physical test, structural qualification, anomalous-effect finding, or independent review."
    }
    (out / "blind-benchmark-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
