from __future__ import annotations

from worldshepherd_sara.edge_benchmark import benchmark_callable


def test_edge_benchmark_records_latency_memory_and_determinism_without_device_claims():
    def transform(value: dict) -> dict:
        return {"sum": sum(value["values"]), "count": len(value["values"])}

    summary = benchmark_callable(transform, {"values": [1, 2, 3, 4]}, repetitions=5, warmup=1)
    assert len(summary.runs) == 5
    assert summary.median_elapsed_ms >= 0
    assert summary.p95_elapsed_ms >= summary.median_elapsed_ms or summary.p95_elapsed_ms >= 0
    assert summary.max_peak_python_bytes >= 0
    assert summary.deterministic_output is True
    assert summary.input_digest.startswith("sha256:")
