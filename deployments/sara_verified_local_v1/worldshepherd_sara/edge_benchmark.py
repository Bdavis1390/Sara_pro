from __future__ import annotations

import statistics
import time
import tracemalloc
from dataclasses import dataclass
from typing import Any, Callable

from .qualification import canonical_digest


@dataclass(frozen=True)
class BenchmarkRun:
    elapsed_ms: float
    peak_python_bytes: int
    output_digest: str


@dataclass(frozen=True)
class BenchmarkSummary:
    runs: tuple[BenchmarkRun, ...]
    median_elapsed_ms: float
    p95_elapsed_ms: float
    max_peak_python_bytes: int
    deterministic_output: bool
    input_digest: str


def _percentile_nearest_rank(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("values required")
    ordered = sorted(values)
    rank = max(1, min(len(ordered), int((percentile * len(ordered)) + 0.999999)))
    return ordered[rank - 1]


def benchmark_callable(
    function: Callable[[Any], Any],
    input_value: Any,
    *,
    repetitions: int = 10,
    warmup: int = 1,
) -> BenchmarkSummary:
    """Benchmark a local Python callable with deterministic input.

    Results are host/runtime specific. They are not edge-device, accelerator,
    real-time, safety, or mission-performance evidence unless run on that exact
    target environment with corresponding qualification controls.
    """
    if repetitions < 1:
        raise ValueError("repetitions must be >= 1")
    if warmup < 0:
        raise ValueError("warmup must be >= 0")

    for _ in range(warmup):
        function(input_value)

    results: list[BenchmarkRun] = []
    for _ in range(repetitions):
        tracemalloc.start()
        start = time.perf_counter_ns()
        output = function(input_value)
        elapsed_ns = time.perf_counter_ns() - start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results.append(
            BenchmarkRun(
                elapsed_ms=elapsed_ns / 1_000_000.0,
                peak_python_bytes=peak,
                output_digest=canonical_digest({"output": output}),
            )
        )

    elapsed = [run.elapsed_ms for run in results]
    digests = {run.output_digest for run in results}
    return BenchmarkSummary(
        runs=tuple(results),
        median_elapsed_ms=statistics.median(elapsed),
        p95_elapsed_ms=_percentile_nearest_rank(elapsed, 0.95),
        max_peak_python_bytes=max(run.peak_python_bytes for run in results),
        deterministic_output=len(digests) == 1,
        input_digest=canonical_digest({"input": input_value}),
    )
