#!/usr/bin/env python3
"""Worldshepherd QBL-G2 caller-observed repeatability benchmark.

This benchmark measures the Python caller's end-to-end invocation time around
the QBL-G1B ``lightning.qubit`` QNode. It is not a transport-only, kernel-only,
FPGA, GPU, physical-QPU, or vendor-benchmark latency measurement.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from backline_cpu_cpu import (
    build_ghz_qnode,
    decoder_library_path,
    environment_manifest,
    ghz_samples_valid,
)


def percentile(values: list[int], pct: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    return float(np.percentile(np.asarray(values, dtype=np.float64), pct))


def summarize_ns(values: list[int]) -> dict[str, float | int]:
    if not values:
        raise ValueError("no timing samples collected")
    return {
        "count": len(values),
        "min_ns": min(values),
        "median_ns": statistics.median(values),
        "p95_ns": percentile(values, 95),
        "p99_ns": percentile(values, 99),
        "max_ns": max(values),
        "mean_ns": statistics.fmean(values),
        "stdev_ns": statistics.pstdev(values),
    }


def timed_call(callable_obj) -> tuple[int, Any]:
    start = time.perf_counter_ns()
    result = callable_obj()
    elapsed = time.perf_counter_ns() - start
    return elapsed, result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shots", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.shots < 1 or args.warmup < 0 or args.iterations < 1:
        parser.error("--shots/--iterations must be positive and --warmup non-negative")

    device_name = "lightning.qubit"
    decoder_path = decoder_library_path()
    manifest = environment_manifest(decoder_path, device_name)

    try:
        ghz = build_ghz_qnode(shots=args.shots, device_name=device_name)

        cold_ns, cold_samples = timed_call(ghz)
        validation_failures = 0 if ghz_samples_valid(cold_samples) else 1

        for _ in range(args.warmup):
            samples = ghz()
            if not ghz_samples_valid(samples):
                validation_failures += 1

        timings: list[int] = []
        for _ in range(args.iterations):
            elapsed_ns, samples = timed_call(ghz)
            timings.append(elapsed_ns)
            if not ghz_samples_valid(samples):
                validation_failures += 1

        report = {
            "gate": "QBL-G2",
            "depends_on": "QBL-G1B",
            "status": "PASS" if validation_failures == 0 else "FAIL",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "measurement_scope": (
                "PYTHON_CALLER_OBSERVED_END_TO_END_INCLUDES_QJIT_DISPATCH_AND_RUNTIME_OVERHEAD"
            ),
            "not_transport_only_measurement": True,
            "not_vendor_benchmark_replication": True,
            "manifest": manifest,
            "shots_per_call": args.shots,
            "warmup_calls_after_cold_call": args.warmup,
            "cold_call_ns": cold_ns,
            "warm_statistics": summarize_ns(timings),
            "ghz_validation_failures": validation_failures,
            "claims_boundary": {
                "sub_3us_performance": "NOT_CURRENTLY_CLAIMED",
                "hardware_qpu_integration": "NOT_CURRENTLY_CLAIMED",
                "quantum_advantage": "NOT_CURRENTLY_CLAIMED",
            },
        }
    except Exception as exc:
        report = {
            "gate": "QBL-G2",
            "depends_on": "QBL-G1B",
            "status": "ERROR",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "measurement_scope": (
                "PYTHON_CALLER_OBSERVED_END_TO_END_INCLUDES_QJIT_DISPATCH_AND_RUNTIME_OVERHEAD"
            ),
            "manifest": manifest,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "claims_boundary": {
                "worldshepherd_backline_integration": "REQUIRES_LAB_VALIDATION",
                "sub_3us_performance": "NOT_CURRENTLY_CLAIMED",
                "hardware_qpu_integration": "NOT_CURRENTLY_CLAIMED",
                "quantum_advantage": "NOT_CURRENTLY_CLAIMED",
            },
        }

    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
