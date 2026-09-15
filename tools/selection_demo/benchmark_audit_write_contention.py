from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.storage import DurableStore


WORKER_LEVELS = (1, 2, 4, 8, 16)
APPENDS_PER_WORKER = 16


def _nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    rank = max(1, min(len(ordered), int((percentile * len(ordered)) + 0.999999)))
    return ordered[rank - 1]


def _profile(root: Path, workers: int) -> dict[str, Any]:
    store = DurableStore(root / f"writers-{workers}")
    total_appends = workers * APPENDS_PER_WORKER

    def append_one(index: int) -> dict[str, Any]:
        record_id = f"AUDIT-W{workers:02d}-{index:05d}"
        record = AuditRecord.create(
            event="audit_write_contention_benchmark",
            actor="benchmark",
            payload={
                "record_id": record_id,
                "workers": workers,
                "index": index,
            },
        )
        started = time.perf_counter_ns()
        store.append_audit(record)
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0
        return {"record_id": record_id, "elapsed_ms": elapsed_ms}

    batch_started = time.perf_counter_ns()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        outcomes = list(executor.map(append_one, range(total_appends)))
    batch_elapsed_s = (time.perf_counter_ns() - batch_started) / 1_000_000_000.0

    latencies = [float(item["elapsed_ms"]) for item in outcomes]
    expected_ids = {str(item["record_id"]) for item in outcomes}
    records = store.read_audit(total_appends + 8)
    benchmark_records = [
        record
        for record in records
        if record.get("event") == "audit_write_contention_benchmark"
    ]
    observed_ids = {
        str(record.get("payload", {}).get("record_id"))
        for record in benchmark_records
    }
    corruption_markers = [
        record for record in records if record.get("event") == "audit_corruption_detected"
    ]

    exact_once = (
        len(benchmark_records) == total_appends
        and len(observed_ids) == total_appends
        and observed_ids == expected_ids
    )
    if not exact_once:
        missing = sorted(expected_ids - observed_ids)[:10]
        unexpected = sorted(observed_ids - expected_ids)[:10]
        raise RuntimeError(
            f"audit exact-once verification failed workers={workers}: "
            f"expected={total_appends} observed={len(benchmark_records)} "
            f"missing={missing} unexpected={unexpected}"
        )
    if corruption_markers:
        raise RuntimeError(
            f"audit corruption marker observed workers={workers}: {corruption_markers[:3]}"
        )

    file_bytes = store.audit_path.stat().st_size
    return {
        "workers": workers,
        "appends_per_worker": APPENDS_PER_WORKER,
        "total_appends": total_appends,
        "batch_elapsed_ms": batch_elapsed_s * 1000.0,
        "durable_appends_per_second": total_appends / batch_elapsed_s,
        "append_latency_p50_ms": statistics.median(latencies),
        "append_latency_p95_ms": _nearest_rank(latencies, 0.95),
        "append_latency_p99_ms": _nearest_rank(latencies, 0.99),
        "append_latency_max_ms": max(latencies),
        "audit_file_bytes": file_bytes,
        "exact_once_records": True,
        "corruption_markers": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--software-commit", default="UNKNOWN")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="ws-audit-write-bench-") as temp:
        root = Path(temp)
        profiles = [_profile(root, workers) for workers in WORKER_LEVELS]

    one_worker = profiles[0]
    highest = profiles[-1]
    result = {
        "schema": "WS-DURABLE-AUDIT-WRITE-CONTENTION-V1",
        "result": "PASS",
        "software_commit": args.software_commit,
        "executed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "implementation_under_test": {
            "store": "DurableStore.append_audit",
            "durability": "each append flushes and fsyncs before returning",
            "serialization": "single DurableStore process-wide RLock protects each append",
            "security": "audit descriptor uses O_APPEND and O_NOFOLLOW where available; mode 0600 is enforced",
        },
        "profiles": profiles,
        "observed_contention": {
            "one_worker_p95_ms": one_worker["append_latency_p95_ms"],
            "highest_worker_count": highest["workers"],
            "highest_workers_p95_ms": highest["append_latency_p95_ms"],
            "one_worker_durable_appends_per_second": one_worker["durable_appends_per_second"],
            "highest_workers_durable_appends_per_second": highest["durable_appends_per_second"],
        },
        "acceptance_checks": {
            "all_append_calls_returned": True,
            "all_profiles_exact_once": True,
            "all_profiles_no_corruption_markers": True,
        },
        "claims_boundary": [
            "This benchmark measures local DurableStore.append_audit calls on one CI host and one process per profile.",
            "Each measured call returns only after the current implementation flushes and fsyncs its audit record.",
            "The benchmark does not establish distributed durability, external-database performance, production request-rate SLA, or mission-scale capacity.",
            "Results are intended to decide whether a semantics-preserving synchronous group-commit experiment is warranted; they do not authorize weakening durable-before-response behavior.",
        ],
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
