#!/usr/bin/env python3
"""Generate machine-readable WS Applied Work -> Post-Work stake proof evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from security.qcrypto.applied_work_postwork import run_bounded_post_work_proof


def canonical_sha256(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run_bounded_post_work_proof().to_dict()
    evidence = {
        "schema": "WS-APPLIED-WORK-POST-WORK-POS-V1",
        "status": report["status"],
        "claim_state": report["claim_state"],
        "receipts_checked": report["receipts_checked"],
        "applications_checked": report["applications_checked"],
        "application_semantics": "PoS consumes validated applied-work evidence; it does not create or rewrite that evidence",
        "proven_properties": report["proven_properties"],
        "excluded_claims": report["excluded_claims"],
        "claims_boundary": {
            "proof_of_applied_work_value": False,
            "production_pos_adoption": False,
            "post_quantum_primitive_security": False,
            "production_consensus_security": False,
        },
    }
    evidence["evidence_sha256"] = canonical_sha256(evidence)
    Path(args.output).write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
