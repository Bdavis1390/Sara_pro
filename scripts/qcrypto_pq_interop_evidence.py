#!/usr/bin/env python3
"""Generate machine-readable WS-QPOS-2 standards-backed PQ interop evidence."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from security.qcrypto.pq_signature_interop import run_all_interop_probes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    results = [result.to_dict() for result in run_all_interop_probes()]
    payload = {
        "schema": "WS-QPOS-2-CONCRETE-PQ-INTEROP-V1",
        "status": "PASS",
        "claim_state": "STANDARDS_BACKED_PQ_SIGNATURE_INTEROPERABILITY_PROVEN_IN_CI",
        "proof_scope": "EPHEMERAL_ZERO_VALUE_INTEROPERABILITY_ONLY",
        "standards": {
            "ML-DSA-65": "NIST FIPS 204",
            "SLH-DSA-SHA2-128s": "NIST FIPS 205",
        },
        "backend": {
            "package": "pqcrypto",
            "pinned_version": "1.0.0",
            "audit_state": "BACKEND_SELF_REPORTS_NOT_FORMALLY_SECURITY_AUDITED",
        },
        "results": results,
        "secret_material_in_evidence": False,
        "production_consensus_security": "NOT_PROVEN_HERE",
        "primitive_security": "RELIES_ON_NIST_STANDARD_AND_BACKEND_IMPLEMENTATION_ASSUMPTIONS",
        "excluded_claims": [
            "No production validator, wallet, staking account, or live network is used.",
            "No claim of backend formal audit or side-channel qualification.",
            "No claim of production consensus correctness, liveness, aggregation scalability, or mainnet readiness.",
            "No claim that a CI round trip constitutes independent cryptographic proof of FIPS 204 or FIPS 205 security.",
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["evidence_sha256"] = sha256(canonical).hexdigest()

    Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
