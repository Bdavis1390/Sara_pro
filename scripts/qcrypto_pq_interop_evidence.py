#!/usr/bin/env python3
"""Generate machine-readable WS-QPOS-2 standards-backed PQ interop evidence."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from security.qcrypto.pos_family_preservation import PROFILES
from security.qcrypto.pos_pq_benchmarks import BENCHMARKS
from security.qcrypto.pq_signature_interop import (
    SCHEMES,
    run_all_interop_probes,
    run_benchmark_interop_probes,
    run_family_interop_probes,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    baseline_results = [result.to_dict() for result in run_all_interop_probes()]
    family_results = [result.to_dict() for result in run_family_interop_probes()]
    benchmark_results = [result.to_dict() for result in run_benchmark_interop_probes()]
    payload = {
        "schema": "WS-QPOS-2-CONCRETE-PQ-INTEROP-V2",
        "status": "PASS",
        "claim_state": "STANDARDS_BACKED_PQ_SIGNATURE_INTEROPERABILITY_PROVEN_IN_CI",
        "family_binding_state": "19_TARGET_POS_PROFILES_PLUS_QRL2_EXTERNAL_PQ_POS_BENCHMARK_INTEROPERABLE_IN_CI",
        "proof_scope": "EPHEMERAL_ZERO_VALUE_INTEROPERABILITY_ONLY",
        "standards": {
            "ML-DSA-65": "NIST FIPS 204",
            "ML-DSA-87": "NIST FIPS 204",
            "SLH-DSA-SHA2-128s": "NIST FIPS 205",
        },
        "backend": {
            "package": "pqcrypto",
            "pinned_version": "1.0.0",
            "audit_state": "BACKEND_SELF_REPORTS_NOT_FORMALLY_SECURITY_AUDITED",
        },
        "target_profile_count": len(PROFILES),
        "benchmark_profile_count": len(BENCHMARKS),
        "scheme_count": len(SCHEMES),
        "family_probe_count": len(family_results),
        "benchmark_probe_count": len(benchmark_results),
        "baseline_results": baseline_results,
        "family_results": family_results,
        "benchmark_results": benchmark_results,
        "benchmarks": {key: value.to_dict() for key, value in sorted(BENCHMARKS.items())},
        "external_benchmark_environment": "TESTNET_NOT_MAINNET",
        "secret_material_in_evidence": False,
        "production_consensus_security": "NOT_PROVEN_HERE",
        "primitive_security": "RELIES_ON_NIST_STANDARD_AND_BACKEND_IMPLEMENTATION_ASSUMPTIONS",
        "excluded_claims": [
            "No production validator, wallet, staking account, or live network is used.",
            "No claim of backend formal audit or side-channel qualification.",
            "No claim of production consensus correctness, liveness, aggregation scalability, VRF/randomness migration, networking identity migration, or mainnet readiness.",
            "No claim that a family-bound CI signature round trip means that the corresponding production protocol already accepts that PQ signature.",
            "QRL 2.0 public testnet evidence does not establish QRL production-mainnet PQ consensus security or any other chain's mainnet PQ security.",
            "No claim that CI round trips constitute independent cryptographic proof of FIPS 204 or FIPS 205 security.",
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["evidence_sha256"] = sha256(canonical).hexdigest()

    Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
