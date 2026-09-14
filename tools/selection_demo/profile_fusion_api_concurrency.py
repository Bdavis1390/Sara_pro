from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from worldshepherd_sara.app import app


ADMIN_TOKEN = "profile-admin-token-0123456789abcdef012345"
RELAY_TOKEN = "profile-relay-token-0123456789abcdef012345"
OBSERVATIONS_PER_REQUEST = 64
WORKER_LEVELS = (1, 2, 4, 8)
REQUESTS_PER_WORKER = 8


def _nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    rank = max(1, min(len(ordered), int((percentile * len(ordered)) + 0.999999)))
    return ordered[rank - 1]


def _observations(count: int) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for index in range(count):
        cluster = index // 4
        offset = index % 4
        observations.append(
            {
                "observation_id": f"DECOMP-OBS-{index:04d}",
                "sensor_id": f"SENSOR-{offset}",
                "t_seconds": float(offset) * 0.05,
                "x": float(cluster * 20) + (float(offset) * 0.2),
                "y": float(cluster * 20) + (float(offset) * 0.2),
                "confidence": 0.85 + (0.01 * offset),
            }
        )
    return observations


def _body(workers: int, index: int) -> dict[str, Any]:
    return {
        "scenario_id": f"API-DECOMP-W{workers:02d}-{index:05d}",
        "observations": _observations(OBSERVATIONS_PER_REQUEST),
        "max_spatial_distance": 2.0,
        "max_time_delta_seconds": 1.0,
    }


def _prepare_environment(root: Path) -> None:
    os.environ["SARA_ADMIN_TOKEN"] = ADMIN_TOKEN
    os.environ["SARA_RELAY_TOKEN"] = RELAY_TOKEN
    os.environ["SARA_DATA_DIR"] = str(root / "sara-data")
    key = Ed25519PrivateKey.generate()
    key_path = root / "echo-checkpoint-ed25519-private.pem"
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)
    os.environ["ECHO_CHECKPOINT_PRIVATE_KEY_FILE"] = str(key_path)
    os.environ["ECHO_CHECKPOINT_KEY_ID"] = "ECHO-CHECKPOINT-DECOMP-V1"


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def _profile(client: TestClient, workers: int) -> dict[str, Any]:
    store = client.app.state.store
    original_append = store.append_audit
    append_timings_ms: dict[str, float] = {}
    append_timings_lock = threading.Lock()

    def timed_append(record):
        started = time.perf_counter_ns()
        try:
            return original_append(record)
        finally:
            if getattr(record, "event", None) == "synthetic_fusion_completed":
                digest = str(record.payload.get("request_digest", ""))
                elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0
                with append_timings_lock:
                    if digest in append_timings_ms:
                        raise RuntimeError(
                            f"duplicate audit timing for request digest {digest}"
                        )
                    append_timings_ms[digest] = elapsed_ms

    store.append_audit = timed_append
    total_requests = workers * REQUESTS_PER_WORKER

    def one_request(index: int) -> dict[str, Any]:
        body = _body(workers, index)
        started = time.perf_counter_ns()
        response = client.post("/v1/synthetic-fusion", headers=_auth(), json=body)
        total_ms = (time.perf_counter_ns() - started) / 1_000_000.0
        if response.status_code != 200:
            raise RuntimeError(
                f"decomposition request failed workers={workers} index={index}: "
                f"{response.status_code} {response.text}"
            )
        payload = response.json()
        return {
            "total_ms": total_ms,
            "fusion_graph_ms": float(payload["elapsed_ms"]),
            "request_digest": str(payload["request_digest"]),
            "result_digest": str(payload["result_digest"]),
            "track_count": int(payload["track_count"]),
        }

    try:
        batch_started = time.perf_counter_ns()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            outcomes = list(executor.map(one_request, range(total_requests)))
        batch_elapsed_s = (time.perf_counter_ns() - batch_started) / 1_000_000_000.0
    finally:
        store.append_audit = original_append

    request_digests = {item["request_digest"] for item in outcomes}
    if set(append_timings_ms) != request_digests:
        missing = sorted(request_digests - set(append_timings_ms))[:10]
        unexpected = sorted(set(append_timings_ms) - request_digests)[:10]
        raise RuntimeError(
            f"audit/request timing correlation failed workers={workers}: "
            f"missing={missing} unexpected={unexpected}"
        )

    total_values: list[float] = []
    fusion_values: list[float] = []
    audit_values: list[float] = []
    residual_values: list[float] = []
    for item in outcomes:
        audit_ms = append_timings_ms[item["request_digest"]]
        residual_ms = item["total_ms"] - item["fusion_graph_ms"] - audit_ms
        if residual_ms < -0.1:
            raise RuntimeError(
                f"negative decomposition residual workers={workers}: {residual_ms} ms"
            )
        total_values.append(item["total_ms"])
        fusion_values.append(item["fusion_graph_ms"])
        audit_values.append(audit_ms)
        residual_values.append(max(0.0, residual_ms))

    return {
        "workers": workers,
        "requests_per_worker": REQUESTS_PER_WORKER,
        "total_requests": total_requests,
        "observations_per_request": OBSERVATIONS_PER_REQUEST,
        "batch_elapsed_ms": batch_elapsed_s * 1000.0,
        "requests_per_second": total_requests / batch_elapsed_s,
        "total_request_p50_ms": statistics.median(total_values),
        "total_request_p95_ms": _nearest_rank(total_values, 0.95),
        "fusion_graph_p50_ms": statistics.median(fusion_values),
        "fusion_graph_p95_ms": _nearest_rank(fusion_values, 0.95),
        "durable_audit_append_p50_ms": statistics.median(audit_values),
        "durable_audit_append_p95_ms": _nearest_rank(audit_values, 0.95),
        "framework_dispatch_residual_p50_ms": statistics.median(residual_values),
        "framework_dispatch_residual_p95_ms": _nearest_rank(residual_values, 0.95),
        "all_request_digests_unique": len(request_digests) == total_requests,
        "all_audit_timings_correlated": len(append_timings_ms) == total_requests,
        "all_track_counts_expected": all(
            item["track_count"] == OBSERVATIONS_PER_REQUEST // 4
            for item in outcomes
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--software-commit", default=os.getenv("GITHUB_SHA", "UNKNOWN"))
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="ws-api-decomp-") as temp:
        root = Path(temp)
        _prepare_environment(root)
        with TestClient(app) as client:
            profiles = [_profile(client, workers) for workers in WORKER_LEVELS]

    result = {
        "schema": "WS-GOVERNED-API-CONCURRENCY-DECOMPOSITION-V1",
        "result": "PASS",
        "software_commit": args.software_commit,
        "executed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "profiles": profiles,
        "decomposition_definition": {
            "total_request": "TestClient call wall time including dispatch, routing, auth, validation, endpoint work, durable audit, response-model handling, serialization, and thread scheduling",
            "fusion_graph": "endpoint-reported interval covering synthetic fusion, evidence-graph construction, track/graph payload generation, and result digest generation; request digest generation occurs before this timer",
            "durable_audit_append": "instrumented real DurableStore.append_audit call; service behavior and fsync semantics are unchanged",
            "framework_dispatch_residual": "total_request - fusion_graph - durable_audit_append; includes request construction/dispatch, scheduling/queueing, routing/middleware, bearer-role resolution, Pydantic validation, request-digest generation, response-model validation, JSON serialization, and measurement overhead; it is not a single server-stage latency",
        },
        "acceptance_checks": {
            "all_profiles_completed": True,
            "all_request_digests_unique": all(
                profile["all_request_digests_unique"] for profile in profiles
            ),
            "all_audit_timings_correlated": all(
                profile["all_audit_timings_correlated"] for profile in profiles
            ),
            "all_track_counts_expected": all(
                profile["all_track_counts_expected"] for profile in profiles
            ),
        },
        "claims_boundary": [
            "This is a diagnostic decomposition of an in-process TestClient benchmark on one CI host.",
            "The residual is intentionally broad and includes TestClient/thread scheduling; it must not be represented as pure FastAPI server processing time.",
            "Instrumentation wraps the real append_audit method and does not skip, defer, or weaken durable audit fsync behavior.",
            "No distributed, real-network, production-SLA, mission-scale, or controlled-environment performance claim follows from this diagnostic.",
        ],
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
