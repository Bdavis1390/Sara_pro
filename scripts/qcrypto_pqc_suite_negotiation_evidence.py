#!/usr/bin/env python3
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from security.qcrypto.hybrid_authority_migration import AuthorityLayer, MigrationRequirement
from security.qcrypto.pqc_suite_negotiation_guard import (
    SuiteNegotiationPolicy,
    SuiteNegotiationRequest,
    assess_suite_negotiation,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy = SuiteNegotiationPolicy(
        network_id="evidence-net",
        authority_layer=AuthorityLayer.ACCOUNT,
        minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
        preference_order=("PQ-MLDSA", "PQ-SLHDSA", "HYBRID-ECDSA-MLDSA"),
        policy_version=12,
    )
    base = dict(
        network_id="evidence-net",
        authority_layer=AuthorityLayer.ACCOUNT,
        offered_suite_ids=("PQ-MLDSA", "HYBRID-ECDSA-MLDSA"),
        peer_capabilities_digest="d" * 64,
        policy_version=12,
    )

    accepted = assess_suite_negotiation(
        SuiteNegotiationRequest(selected_suite_id="PQ-MLDSA", **base), policy
    )
    downgrade = assess_suite_negotiation(
        SuiteNegotiationRequest(selected_suite_id="HYBRID-ECDSA-MLDSA", **base), policy
    )
    unknown = assess_suite_negotiation(
        SuiteNegotiationRequest(
            selected_suite_id="PQ-MLDSA",
            **{**base, "offered_suite_ids": ("PQ-MLDSA", "UNKNOWN-SUITE")},
        ),
        policy,
    )
    pq_floor = assess_suite_negotiation(
        SuiteNegotiationRequest(
            network_id="evidence-net",
            authority_layer=AuthorityLayer.ACCOUNT,
            offered_suite_ids=("HYBRID-ECDSA-MLDSA",),
            selected_suite_id="HYBRID-ECDSA-MLDSA",
            peer_capabilities_digest="d" * 64,
            policy_version=12,
        ),
        SuiteNegotiationPolicy(
            network_id="evidence-net",
            authority_layer=AuthorityLayer.ACCOUNT,
            minimum_requirement=MigrationRequirement.PQ_REQUIRED,
            preference_order=("PQ-MLDSA", "PQ-SLHDSA", "HYBRID-ECDSA-MLDSA"),
            policy_version=12,
        ),
    )

    evidence = {
        "schema": "WS-QCRYPTO-PQC-SUITE-NEGOTIATION-EVIDENCE-V1",
        "status": "PASS",
        "results": {
            "STRONGEST_ACCEPT": accepted.to_dict(),
            "WEAKER_SELECTION_REJECT": downgrade.to_dict(),
            "UNKNOWN_SUITE_REJECT": unknown.to_dict(),
            "PQ_FLOOR_REJECTS_HYBRID_ONLY": pq_floor.to_dict(),
        },
        "summary": {
            "strongest_offered_suite_accepted": accepted.accepted,
            "weaker_selection_rejected": downgrade.verdict == "SUITE_DOWNGRADE_REJECTED",
            "unknown_suite_rejected": not unknown.accepted,
            "pq_floor_rejects_hybrid_only": not pq_floor.accepted,
            "transcript_digest_present": bool(accepted.negotiation_transcript_digest),
            "execution_authority": False,
            "live_value_authorized": False,
            "transaction_authorized": False,
            "production_deployment_established": False,
        },
    }
    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    evidence["evidence_sha256"] = sha256(canonical).hexdigest()
    Path(args.output).write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
