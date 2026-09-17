#!/usr/bin/env python3
"""Bind independent PRIME and governed-QCRYPTO artifacts into a human-review package."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from security.qcrypto.prime_governed_release_review import (
    BRIDGE_SCHEMA,
    assess_prime_governed_release_review,
)


def _read_json(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"evidence file must contain a JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prime", required=True)
    parser.add_argument("--governed", required=True)
    parser.add_argument("--output", default="prime-governed-release-review-evidence.json")
    args = parser.parse_args()

    prime = _read_json(args.prime)
    governed = _read_json(args.governed)
    decision = assess_prime_governed_release_review(prime, governed)
    if not decision.ready_for_human_release_review:
        raise SystemExit("cross-boundary PRIME/QCRYPTO evidence did not reach human release review")

    evidence = {
        "schema": BRIDGE_SCHEMA,
        "status": "PASS",
        "claim_state": "PRIME_AND_QCRYPTO_EVIDENCE_BOUND_FOR_HUMAN_REVIEW_ONLY",
        "proof_scope": "CROSS_BOUNDARY_REVIEW_PACKAGE_NO_EXECUTION_AUTHORITY",
        "decision": decision.to_dict(),
        "source_evidence": {
            "prime_evidence_sha256": decision.prime_evidence_sha256,
            "governed_evidence_sha256": decision.governed_evidence_sha256,
        },
        "summary": {
            "ready_for_human_release_review": decision.ready_for_human_release_review,
            "human_release_required": decision.human_release_required,
            "human_release_recorded": decision.human_release_recorded,
            "prime_signing_algorithm": decision.prime_signing_algorithm,
            "prime_signature_context": decision.prime_signature_context,
            "prime_activation_disposition": decision.prime_activation_disposition,
            "prime_authorization_registry_status": decision.prime_authorization_registry_status,
            "governed_terminal_state": decision.governed_terminal_state,
            "governed_selected_suite_id": decision.governed_selected_suite_id,
            "governed_pq_algorithm_id": decision.governed_pq_algorithm_id,
            "review_package_sha256": decision.review_package_sha256,
            "execution_authority": False,
            "live_value_authorized": False,
            "live_transaction_signed": False,
            "production_protocol_integration": False,
            "end_to_end_pq_security_established": False,
        },
    }
    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    evidence["evidence_sha256"] = sha256(canonical).hexdigest()
    Path(args.output).write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("prime_governed_release_review_status: PASS")
    print("review_package_sha256:", decision.review_package_sha256)
    print("evidence_sha256:", evidence["evidence_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
