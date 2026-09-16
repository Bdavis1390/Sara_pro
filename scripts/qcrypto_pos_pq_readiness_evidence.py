#!/usr/bin/env python3
"""Emit claims-controlled PQ readiness evidence for reviewed PoS profiles."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from security.qcrypto.pos_pq_readiness import (
    AXES,
    assess_all_benchmarks,
    assess_all_targets,
    assert_fail_closed_claims,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    assert_fail_closed_claims()
    targets = {key: value.to_dict() for key, value in sorted(assess_all_targets().items())}
    benchmarks = {key: value.to_dict() for key, value in sorted(assess_all_benchmarks().items())}
    target_classes = Counter(item["classification"] for item in targets.values())
    payload = {
        "schema": "WS-QPOS-PQ-READINESS-V1",
        "status": "PASS",
        "claim_state": "FAIL_CLOSED_POST_QUANTUM_CONSENSUS_READINESS_CLASSIFICATION",
        "target_count": len(targets),
        "benchmark_count": len(benchmarks),
        "required_axes": list(AXES),
        "targets": targets,
        "benchmarks": benchmarks,
        "target_classification_counts": dict(sorted(target_classes.items())),
        "production_ready_target_count": sum(1 for item in targets.values() if item["production_ready"]),
        "production_ready_benchmark_count": sum(1 for item in benchmarks.values() if item["production_ready"]),
        "warranted_summary": {
            "production_pq_consensus_ready": False,
            "external_public_pq_validator_testnet_benchmark": True,
            "production_pq_component_evidence": True,
            "external_pq_transition_development": True,
            "internal_family_bound_pq_interop": True,
        },
        "claims_boundary": [
            "A standardized PQ signature round trip does not establish production consensus acceptance.",
            "A PQ account/authentication component does not establish PQ validator consensus.",
            "A public PQ validator testnet does not establish production-mainnet PQ consensus security.",
            "Production readiness requires production-grade evidence across every required system axis.",
            "Unknown or missing evidence fails closed and remains a blocker.",
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["evidence_sha256"] = sha256(canonical).hexdigest()
    Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
