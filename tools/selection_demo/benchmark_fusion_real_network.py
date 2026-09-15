from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import os
import platform
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
from cryptography.x509.oid import NameOID


ADMIN_TOKEN = "network-admin-token-0123456789abcdef012345"
RELAY_TOKEN = "network-relay-token-0123456789abcdef012345"
OBSERVATIONS_PER_REQUEST = 64
WORKER_LEVELS = (1, 2, 4, 8)
REQUESTS_PER_WORKER = 8
WARMUP_PER_WORKER = 1
SERVICE_START_TIMEOUT_SECONDS = 20.0
REQUEST_TIMEOUT_SECONDS = 20.0
REQUIRED_SERVER_TIMING = frozenset(
    {"request_digest", "fusion_graph", "audit_fsync", "server_total"}
)


def _nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    rank = max(1, min(len(ordered), int((percentile * len(ordered)) + 0.999999)))
    return ordered[rank - 1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _observations() -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for index in range(OBSERVATIONS_PER_REQUEST):
        cluster = index // 4
        offset = index % 4
        values.append(
            {
                "observation_id": f"NET-OBS-{index:04d}",
                "sensor_id": f"SENSOR-{offset}",
                "t_seconds": float(offset) * 0.05,
                "x": float(cluster * 20) + (float(offset) * 0.2),
                "y": float(cluster * 20) + (float(offset) * 0.2),
                "confidence": 0.85 + (0.01 * offset),
            }
        )
    return values


def _body(transport: str, workers: int, index: int, *, warmup: bool = False) -> dict[str, Any]:
    phase = "WARM" if warmup else "MEASURE"
    return {
        "scenario_id": f"REALNET-{transport.upper()}-{phase}-W{workers:02d}-{index:05d}",
        "observations": _observations(),
        "max_spatial_distance": 2.0,
        "max_time_delta_seconds": 1.0,
    }


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def _parse_server_timing(value: str) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for raw_metric in value.split(","):
        parts = [part.strip() for part in raw_metric.strip().split(";") if part.strip()]
        if not parts:
            continue
        name = parts[0]
        duration: float | None = None
        for parameter in parts[1:]:
            if parameter.startswith("dur="):
                duration = float(parameter[4:])
                break
        if duration is not None:
            metrics[name] = duration
    missing = REQUIRED_SERVER_TIMING - set(metrics)
    if missing:
        raise RuntimeError(
            f"missing required Server-Timing metrics {sorted(missing)} in {value!r}"
        )
    return metrics


def _write_echo_key(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    path = root / "echo-checkpoint-ed25519-private.pem"
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)
    return path


def _write_tls_material(root: Path) -> tuple[Path, Path]:
    key = generate_private_key(public_exponent=65537, key_size=2048)
    key_path = root / "localhost-tls-key.pem"
    cert_path = root / "localhost-tls-cert.pem"
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)

    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]
    )
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=1))
        .not_valid_after(now + dt.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    cert_path.chmod(0o600)
    return cert_path, key_path


def _service_environment(data_dir: Path, echo_key: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "SARA_ADMIN_TOKEN": ADMIN_TOKEN,
            "SARA_RELAY_TOKEN": RELAY_TOKEN,
            "SARA_DATA_DIR": str(data_dir),
            "ECHO_CHECKPOINT_PRIVATE_KEY_FILE": str(echo_key),
            "ECHO_CHECKPOINT_KEY_ID": "ECHO-CHECKPOINT-REALNET-V1",
            "SARA_BENCHMARK_TIMING_HEADERS": "1",
        }
    )
    return env


def _start_service(
    *,
    transport: str,
    root: Path,
    cert_path: Path | None,
    key_path: Path | None,
) -> tuple[subprocess.Popen[str], str, Path]:
    port = _free_port()
    data_dir = root / f"data-{transport}"
    echo_key = _write_echo_key(root / f"echo-{transport}")
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "worldshepherd_sara.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--workers",
        "1",
        "--log-level",
        "warning",
        "--no-access-log",
    ]
    scheme = "http"
    if transport == "https":
        if cert_path is None or key_path is None:
            raise RuntimeError("TLS transport requires certificate and key")
        command.extend(
            [
                "--ssl-certfile",
                str(cert_path),
                "--ssl-keyfile",
                str(key_path),
            ]
        )
        scheme = "https"

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=_service_environment(data_dir, echo_key),
    )
    base_url = f"{scheme}://127.0.0.1:{port}"
    deadline = time.monotonic() + SERVICE_START_TIMEOUT_SECONDS
    last_error: str | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(
                f"uvicorn exited before readiness transport={transport}: {output}"
            )
        try:
            with httpx.Client(verify=False, timeout=1.0, trust_env=False) as client:
                response = client.get(f"{base_url}/livez")
                if response.status_code == 200 and response.json().get("ok") is True:
                    return process, base_url, data_dir
                last_error = f"status={response.status_code} body={response.text[:200]}"
        except Exception as exc:  # readiness loop diagnostic only
            last_error = repr(exc)
        time.sleep(0.05)

    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
    output = process.stdout.read() if process.stdout else ""
    raise RuntimeError(
        f"uvicorn readiness timeout transport={transport}; last_error={last_error}; output={output}"
    )


def _stop_service(process: subprocess.Popen[str]) -> str:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    return process.stdout.read() if process.stdout else ""


def _profile_transport(base_url: str, transport: str) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for workers in WORKER_LEVELS:
        total_requests = workers * REQUESTS_PER_WORKER

        def worker(worker_index: int) -> list[dict[str, Any]]:
            results: list[dict[str, Any]] = []
            limits = httpx.Limits(max_connections=1, max_keepalive_connections=1)
            with httpx.Client(
                base_url=base_url,
                headers=_auth(),
                verify=False,
                timeout=REQUEST_TIMEOUT_SECONDS,
                trust_env=False,
                limits=limits,
            ) as client:
                for warmup_index in range(WARMUP_PER_WORKER):
                    warmup_body = _body(
                        transport,
                        workers,
                        (worker_index * WARMUP_PER_WORKER) + warmup_index,
                        warmup=True,
                    )
                    warmup_response = client.post("/v1/synthetic-fusion", json=warmup_body)
                    if warmup_response.status_code != 200:
                        raise RuntimeError(
                            f"warmup failed transport={transport} workers={workers} "
                            f"worker={worker_index}: {warmup_response.status_code} "
                            f"{warmup_response.text}"
                        )
                    if warmup_response.headers.get("X-Worldshepherd-Benchmark-Timing") != "1":
                        raise RuntimeError("benchmark timing marker missing from warmup response")
                    _parse_server_timing(warmup_response.headers.get("Server-Timing", ""))

                for local_index in range(REQUESTS_PER_WORKER):
                    index = worker_index * REQUESTS_PER_WORKER + local_index
                    body = _body(transport, workers, index)
                    started = time.perf_counter_ns()
                    response = client.post("/v1/synthetic-fusion", json=body)
                    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0
                    if response.status_code != 200:
                        raise RuntimeError(
                            f"network request failed transport={transport} workers={workers} "
                            f"index={index}: {response.status_code} {response.text}"
                        )
                    if response.headers.get("X-Worldshepherd-Benchmark-Timing") != "1":
                        raise RuntimeError("benchmark timing marker missing from measured response")
                    timing = _parse_server_timing(response.headers.get("Server-Timing", ""))
                    payload = response.json()
                    server_total_ms = timing["server_total"]
                    server_accounted_ms = (
                        timing["request_digest"]
                        + timing["fusion_graph"]
                        + timing["audit_fsync"]
                    )
                    results.append(
                        {
                            "elapsed_ms": elapsed_ms,
                            "server_total_ms": server_total_ms,
                            "server_request_digest_ms": timing["request_digest"],
                            "server_fusion_graph_ms": timing["fusion_graph"],
                            "server_audit_fsync_ms": timing["audit_fsync"],
                            "server_unattributed_ms": max(0.0, server_total_ms - server_accounted_ms),
                            "client_transport_residual_ms": max(0.0, elapsed_ms - server_total_ms),
                            "request_digest": str(payload["request_digest"]),
                            "result_digest": str(payload["result_digest"]),
                            "track_count": int(payload["track_count"]),
                        }
                    )
            return results

        batch_started = time.perf_counter_ns()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            nested = list(executor.map(worker, range(workers)))
        batch_elapsed_s = (time.perf_counter_ns() - batch_started) / 1_000_000_000.0
        outcomes = [item for worker_items in nested for item in worker_items]

        def values(name: str) -> list[float]:
            return [float(item[name]) for item in outcomes]

        latencies = values("elapsed_ms")
        server_total = values("server_total_ms")
        request_digest_values = values("server_request_digest_ms")
        fusion_values = values("server_fusion_graph_ms")
        audit_values = values("server_audit_fsync_ms")
        server_unattributed = values("server_unattributed_ms")
        transport_residual = values("client_transport_residual_ms")
        request_digests = {str(item["request_digest"]) for item in outcomes}
        result_digests = {str(item["result_digest"]) for item in outcomes}
        if len(outcomes) != total_requests or len(request_digests) != total_requests:
            raise RuntimeError(
                f"request cardinality failure transport={transport} workers={workers}"
            )
        if not all(
            int(item["track_count"]) == OBSERVATIONS_PER_REQUEST // 4
            for item in outcomes
        ):
            raise RuntimeError("unexpected track count in network benchmark")

        profiles.append(
            {
                "workers": workers,
                "warmup_per_worker": WARMUP_PER_WORKER,
                "requests_per_worker": REQUESTS_PER_WORKER,
                "total_measured_requests": total_requests,
                "observations_per_request": OBSERVATIONS_PER_REQUEST,
                "batch_elapsed_ms": batch_elapsed_s * 1000.0,
                "measured_requests_per_second": total_requests / batch_elapsed_s,
                "request_latency_p50_ms": statistics.median(latencies),
                "request_latency_p95_ms": _nearest_rank(latencies, 0.95),
                "request_latency_p99_ms": _nearest_rank(latencies, 0.99),
                "request_latency_max_ms": max(latencies),
                "server_total_p50_ms": statistics.median(server_total),
                "server_total_p95_ms": _nearest_rank(server_total, 0.95),
                "server_request_digest_p50_ms": statistics.median(request_digest_values),
                "server_request_digest_p95_ms": _nearest_rank(request_digest_values, 0.95),
                "server_fusion_graph_p50_ms": statistics.median(fusion_values),
                "server_fusion_graph_p95_ms": _nearest_rank(fusion_values, 0.95),
                "server_audit_fsync_p50_ms": statistics.median(audit_values),
                "server_audit_fsync_p95_ms": _nearest_rank(audit_values, 0.95),
                "server_unattributed_p50_ms": statistics.median(server_unattributed),
                "server_unattributed_p95_ms": _nearest_rank(server_unattributed, 0.95),
                "client_transport_residual_p50_ms": statistics.median(transport_residual),
                "client_transport_residual_p95_ms": _nearest_rank(transport_residual, 0.95),
                "all_request_digests_unique": True,
                "unique_result_digest_count": len(result_digests),
            }
        )
    return profiles


def _verify_audit(data_dir: Path, expected: int) -> dict[str, Any]:
    audit_path = data_dir / "audit.jsonl"
    fusion_records = 0
    corrupt_lines = 0
    if not audit_path.exists():
        raise RuntimeError(f"audit file missing: {audit_path}")
    for raw_line in audit_path.read_bytes().splitlines():
        if not raw_line:
            corrupt_lines += 1
            continue
        try:
            value = json.loads(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            corrupt_lines += 1
            continue
        if value.get("event") == "synthetic_fusion_completed":
            fusion_records += 1
    if fusion_records != expected or corrupt_lines:
        raise RuntimeError(
            f"audit verification failed path={audit_path}: expected={expected} "
            f"observed={fusion_records} corrupt_lines={corrupt_lines}"
        )
    return {
        "expected_synthetic_fusion_events": expected,
        "observed_synthetic_fusion_events": fusion_records,
        "corrupt_lines": corrupt_lines,
        "complete": True,
    }


def _run_transport(
    *,
    root: Path,
    transport: str,
    cert_path: Path | None,
    key_path: Path | None,
) -> dict[str, Any]:
    process, base_url, data_dir = _start_service(
        transport=transport,
        root=root,
        cert_path=cert_path,
        key_path=key_path,
    )
    service_output = ""
    try:
        profiles = _profile_transport(base_url, transport)
    finally:
        service_output = _stop_service(process)
    expected = sum(
        workers * (REQUESTS_PER_WORKER + WARMUP_PER_WORKER)
        for workers in WORKER_LEVELS
    )
    audit = _verify_audit(data_dir, expected)
    return {
        "transport": transport,
        "server": "uvicorn single worker on 127.0.0.1",
        "profiles": profiles,
        "audit_persistence": audit,
        "service_output_tail": service_output[-2000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--software-commit", default=os.getenv("GITHUB_SHA", "UNKNOWN"))
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="ws-real-network-") as temp:
        root = Path(temp)
        cert_path, key_path = _write_tls_material(root)
        http_result = _run_transport(
            root=root,
            transport="http",
            cert_path=None,
            key_path=None,
        )
        https_result = _run_transport(
            root=root,
            transport="https",
            cert_path=cert_path,
            key_path=key_path,
        )

    result = {
        "schema": "WS-GOVERNED-FUSION-REAL-NETWORK-BENCHMARK-V2",
        "result": "PASS",
        "software_commit": args.software_commit,
        "executed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "request_model": {
            "observations_per_request": OBSERVATIONS_PER_REQUEST,
            "worker_levels": list(WORKER_LEVELS),
            "warmup_per_worker": WARMUP_PER_WORKER,
            "measured_requests_per_worker": REQUESTS_PER_WORKER,
            "clients": "one persistent HTTPX connection per worker, warmed before measured requests",
        },
        "timing_definition": {
            "server_total": "benchmark-only outer HTTP middleware duration through endpoint/response construction on the service process",
            "server_request_digest": "canonical request digest inside the synthetic-fusion endpoint",
            "server_fusion_graph": "synthetic fusion, evidence graph/payload construction, and result digest interval",
            "server_audit_fsync": "real DurableStore.append_audit call including lock wait, write, flush, fsync, and security-mode verification",
            "server_unattributed": "server_total minus the three explicitly timed endpoint stages; includes auth/dependency solving, Pydantic validation, thread scheduling, response-model validation/serialization, middleware, and instrumentation overhead",
            "client_transport_residual": "client wall time minus server_total on the same host; includes HTTPX handling, loopback TCP framing/transfer, and TLS framing/encryption when applicable",
        },
        "transports": [http_result, https_result],
        "acceptance_checks": {
            "http_completed": True,
            "https_completed": True,
            "persistent_connections_warmed_before_measurement": True,
            "benchmark_server_timing_present": True,
            "all_requests_authenticated_and_successful": True,
            "all_request_digests_unique": True,
            "audit_complete_for_each_transport_including_warmups": True,
        },
        "claims_boundary": [
            "This benchmark uses real localhost TCP sockets and a real single-worker Uvicorn service process.",
            "Measured request samples exclude each persistent client's connection-establishment warmup request.",
            "HTTPS uses direct Uvicorn TLS with an ephemeral self-signed localhost certificate and client certificate verification disabled; it does not represent production PKI or a reverse proxy.",
            "Benchmark-only Server-Timing headers are enabled only by SARA_BENCHMARK_TIMING_HEADERS=1 and are not required in normal operation.",
            "The benchmark includes bearer authorization, request validation, fusion/evidence construction, durable audit flush/fsync, response validation/serialization, HTTP framing, TCP loopback, and optional TLS overhead.",
            "It does not include a reverse proxy/service mesh, external database/object store, multi-host load balancer, multimodal decode/inference, CUI/classified controls, production PKI, or WAN conditions.",
            "No production SLA, distributed-scale, mission-scale, or controlled-environment compliance claim follows from these results.",
        ],
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
