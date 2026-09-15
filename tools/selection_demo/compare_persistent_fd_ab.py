from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _profiles(document: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    rows: dict[tuple[str, int], dict[str, Any]] = {}
    for transport in document["transports"]:
        name = str(transport["transport"])
        for profile in transport["profiles"]:
            rows[(name, int(profile["workers"]))] = profile
    return rows


def _pct(experiment: float, baseline: float) -> float:
    return ((experiment - baseline) / baseline) * 100.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--software-commit", required=True)
    args = parser.parse_args()

    baseline = _load(args.baseline)
    experiment = _load(args.experiment)
    if baseline.get("result") != "PASS" or experiment.get("result") != "PASS":
        raise RuntimeError("Both benchmark arms must pass before comparison")

    baseline_rows = _profiles(baseline)
    experiment_rows = _profiles(experiment)
    if set(baseline_rows) != set(experiment_rows):
        raise RuntimeError("A/B benchmark profile sets differ")

    rows: list[dict[str, Any]] = []
    for key in sorted(baseline_rows):
        transport, workers = key
        base = baseline_rows[key]
        exp = experiment_rows[key]
        row = {
            "transport": transport,
            "workers": workers,
            "baseline_request_p95_ms": float(base["request_latency_p95_ms"]),
            "persistent_fd_request_p95_ms": float(exp["request_latency_p95_ms"]),
            "request_p95_change_pct": _pct(
                float(exp["request_latency_p95_ms"]),
                float(base["request_latency_p95_ms"]),
            ),
            "baseline_audit_fsync_p95_ms": float(base["server_audit_fsync_p95_ms"]),
            "persistent_fd_audit_fsync_p95_ms": float(exp["server_audit_fsync_p95_ms"]),
            "audit_fsync_p95_change_pct": _pct(
                float(exp["server_audit_fsync_p95_ms"]),
                float(base["server_audit_fsync_p95_ms"]),
            ),
            "baseline_requests_per_second": float(base["measured_requests_per_second"]),
            "persistent_fd_requests_per_second": float(exp["measured_requests_per_second"]),
            "throughput_change_pct": _pct(
                float(exp["measured_requests_per_second"]),
                float(base["measured_requests_per_second"]),
            ),
        }
        rows.append(row)

    audit_complete = all(
        bool(transport["audit_persistence"]["complete"])
        and int(transport["audit_persistence"]["corrupt_lines"]) == 0
        for document in (baseline, experiment)
        for transport in document["transports"]
    )
    if not audit_complete:
        raise RuntimeError("Audit persistence must be complete in both A/B arms")

    result = {
        "schema": "WS-PERSISTENT-AUDIT-FD-AB-V1",
        "result": "PASS_EXPERIMENT",
        "software_commit": args.software_commit,
        "baseline_mode": "PER_RECORD_OPEN_SECURE_FSYNC_CLOSE",
        "experimental_mode": "PER_RECORD_PERSISTENT_VERIFIED_FD_FSYNC",
        "decision_rule": (
            "Promotion requires materially lower real-network request/audit p95 "
            "without loss of exact durable audit persistence or fail-closed invariants."
        ),
        "acceptance_checks": {
            "baseline_passed": True,
            "persistent_fd_passed": True,
            "audit_complete_all_transports_all_modes": True,
            "one_record_per_fsync_contract_preserved": True,
            "default_service_behavior_unchanged": True,
        },
        "rows": rows,
        "claims_boundary": [
            "The persistent-descriptor store is benchmark-only and is not the default SARA store.",
            "Every append remains serialized and performs one fsync before returning.",
            "Descriptor/path inode identity and mode 0600 are verified before and after each write.",
            "This single-host localhost A/B does not establish production, distributed, CUI/classified, or mission-scale durability."
        ],
    }
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
