from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from worldshepherd_sara.app import app
from worldshepherd_sara.limits import MAX_REQUEST_BYTES
from worldshepherd_sara.synthetic_fusion_api import SYNTHETIC_FUSION_SCOPE


PROFILES = (16, 64, 128)
REPETITIONS = 7
WARMUP = 2
ADMIN_TOKEN = "benchmark-admin-token-0123456789abcdef012345"
RELAY_TOKEN = "benchmark-relay-token-0123456789abcdef012345"


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
                "observation_id": f"API-BENCH-OBS-{index:04d}",
                "sensor_id": f"SENSOR-{offset}",
                "t_seconds": float(offset) * 0.05,
                "x": float(cluster * 20) + (float(offset) * 0.2),
                "y": float(cluster * 20) + (float(offset) * 0.2),
                "confidence": 0.85 + (0.01 * offset),
            }
        )
    return observations


def _request_body(count: int) -> dict[str, Any]:
    return {
        "scenario_id": f"API-PATH-BENCH-{count:04d}",
        "observations": _observations(count),
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
    os.environ["ECHO_CHECKPOINT_KEY_ID"] = "ECHO-CHECKPOINT-API-BENCH-V1"


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def _run_profile(client: TestClient, count: int) -> dict[str, Any]:
    body = _request_body(count)
    request_bytes = len(
        json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    )
    if request_bytes > MAX_REQUEST_BYTES:
        raise RuntimeError(
            f"benchmark request {request_bytes} bytes exceeds service limit {MAX_REQUEST_BYTES}"
        )

    expected_digest: str | None = None
    for _ in range(WARMUP):
        response = client.post("/v1/synthetic-fusion", headers=_auth(), json=body)
        if response.status_code != 200:
            raise RuntimeError(
                f"warmup failed for profile {count}: {response.status_code} {response.text}"
            )
        payload = response.json()
        expected_digest = expected_digest or payload["result_digest"]
        if payload["result_digest"] != expected_digest:
            raise RuntimeError("non-deterministic result digest during warmup")

    elapsed_ms: list[float] = []
    response_bytes: list[int] = []
    server_compute_ms: list[float] = []
    result_digests: set[str] = set()
    request_digests: set[str] = set()
    track_counts: set[int] = set()

    for _ in range(REPETITIONS):
        started = time.perf_counter_ns()
        response = client.post("/v1/synthetic-fusion", headers=_auth(), json=body)
        total_ms = (time.perf_counter_ns() - started) / 1_000_000.0
        if response.status_code != 200:
            raise RuntimeError(
                f"benchmark request failed for profile {count}: {response.status_code} {response.text}"
            )
        payload = response.json()
        if payload["scope"] != SYNTHETIC_FUSION_SCOPE:
            raise RuntimeError("unexpected fusion scope")
        if payload["observation_count"] != count:
            raise RuntimeError("observation count changed across API path")
        elapsed_ms.append(total_ms)
        response_bytes.append(len(response.content))
        server_compute_ms.append(float(payload["elapsed_ms"]))
        result_digests.add(payload["result_digest"])
        request_digests.add(payload["request_digest"])
        track_counts.add(int(payload["track_count"]))

    deterministic = (
        len(result_digests) == 1
        and len(request_digests) == 1
        and len(track_counts) == 1
        and (expected_digest is None or expected_digest in result_digests)
    )
    if not deterministic:
        raise RuntimeError(f"profile {count} was not deterministic")

    p95_ms = _nearest_rank(elapsed_ms, 0.95)
    return {
        "observations": count,
        "request_bytes": request_bytes,
        "response_bytes_median": int(statistics.median(response_bytes)),
        "tracks": next(iter(track_counts)),
        "repetitions": REPETITIONS,
        "warmup": WARMUP,
        "full_application_path_p50_ms": statistics.median(elapsed_ms),
        "full_application_path_p95_ms": p95_ms,
        "server_fusion_graph_p50_ms": statistics.median(server_compute_ms),
        "server_fusion_graph_p95_ms": _nearest_rank(server_compute_ms, 0.95),
        "effective_request_mb_per_min_at_p95": (
            (request_bytes / 1_000_000.0) / (p95_ms / 60_000.0)
        ),
        "deterministic_result_digest": True,
        "request_digest": next(iter(request_digests)),
        "result_digest": next(iter(result_digests)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--software-commit", default=os.getenv("GITHUB_SHA", "UNKNOWN"))
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="ws-api-path-bench-") as temp:
        root = Path(temp)
        _prepare_environment(root)
        with TestClient(app) as client:
            profiles = [_run_profile(client, count) for count in PROFILES]
            audit_records = client.app.state.store.read_audit(500)
            fusion_audits = [
                record
                for record in audit_records
                if record.get("event") == "synthetic_fusion_completed"
            ]
            expected_audits = len(PROFILES) * (WARMUP + REPETITIONS)
            audit_persistence_complete = len(fusion_audits) == expected_audits

    result = {
        "schema": "WS-GOVERNED-FUSION-API-PATH-BENCHMARK-V1",
        "result": "PASS" if audit_persistence_complete else "FAIL",
        "software_commit": args.software_commit,
        "executed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "service_limits": {
            "max_request_bytes": MAX_REQUEST_BYTES,
            "max_synthetic_observations": max(PROFILES),
        },
        "timed_path": [
            "TestClient HTTP request construction/dispatch",
            "FastAPI/Starlette routing and middleware",
            "Bearer-token role resolution and admin authorization",
            "Pydantic request validation",
            "synthetic 2-D fusion and evidence-graph construction",
            "result/request digest generation",
            "durable SARA audit append/fsync",
            "FastAPI response-model validation and JSON serialization",
        ],
        "excluded_from_timed_path": [
            "real network transport, TLS, proxy/service-mesh overhead",
            "multimodal imagery/video/radar decoding",
            "AI/ML inference",
            "external databases/object stores",
            "CUI/classified cross-domain controls",
            "operator UI rendering",
            "distributed concurrency/load-balancer behavior",
        ],
        "profiles": profiles,
        "audit_persistence": {
            "expected_synthetic_fusion_events": expected_audits,
            "observed_synthetic_fusion_events": len(fusion_audits),
            "complete": audit_persistence_complete,
        },
        "claims_boundary": [
            "This is an in-process FastAPI TestClient application-path benchmark on the recorded CI host.",
            "It materially includes service authorization, validation, fusion/evidence construction, response serialization, and durable audit persistence, but it is not a real-network or operational ISR benchmark.",
            "No DIU, DoD, CUI/classified, edge-device, or mission-scale performance compliance is established by this result.",
        ],
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
