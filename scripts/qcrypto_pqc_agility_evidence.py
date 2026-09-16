#!/usr/bin/env python3
"""Generate deterministic evidence for the Worldshepherd PQC agility policy.

The output is claims-control evidence only. It does not exercise cryptographic
primitives or claim protocol/FIPS module validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from security.qcrypto.pqc_algorithm_policy import (
    AlgorithmRequest,
    CryptoRole,
    Environment,
    REGISTRY,
    SupportTier,
    TransitionMode,
    assess,
    assert_fail_closed_registry,
)


AS_OF = date(2026, 9, 15)


def req(
    algorithm_id: str,
    role: CryptoRole,
    *,
    environment: Environment = Environment.PRODUCTION,
    support: SupportTier = SupportTier.PRODUCTION,
    transition: TransitionMode = TransitionMode.PQ_ONLY,
    checked: date = AS_OF,
    max_age: int = 120,
) -> AlgorithmRequest:
    return AlgorithmRequest(
        algorithm_id=algorithm_id,
        role=role,
        environment=environment,
        support_tier=support,
        transition_mode=transition,
        evidence_checked_on=checked,
        max_evidence_age_days=max_age,
    )


def scenarios() -> dict[str, AlgorithmRequest]:
    return {
        "ML_KEM_PRODUCTION_KEY_ESTABLISHMENT": req(
            "ML-KEM", CryptoRole.KEY_ESTABLISHMENT
        ),
        "ML_DSA_PRODUCTION_SIGNATURE_HYBRID": req(
            "ML-DSA",
            CryptoRole.DIGITAL_SIGNATURE,
            transition=TransitionMode.HYBRID_TRANSITION,
        ),
        "ML_DSA_CONSENSUS_INTERNAL_SUPPORT_ONLY": req(
            "ML-DSA",
            CryptoRole.CONSENSUS_AUTH,
            support=SupportTier.INTERNAL,
        ),
        "SLH_DSA_PUBLIC_TESTNET_NODE_IDENTITY": req(
            "SLH-DSA",
            CryptoRole.NODE_IDENTITY,
            environment=Environment.TESTNET,
            support=SupportTier.PUBLIC_TESTNET,
        ),
        "FN_DSA_PRODUCTION_SIGNATURE": req(
            "FN-DSA", CryptoRole.DIGITAL_SIGNATURE
        ),
        "HQC_PRODUCTION_KEY_ESTABLISHMENT": req(
            "HQC", CryptoRole.KEY_ESTABLISHMENT
        ),
        "HAWK_PRODUCTION_SIGNATURE": req(
            "HAWK", CryptoRole.DIGITAL_SIGNATURE
        ),
        "ECDSA_HYBRID_MIGRATION_COMPONENT": req(
            "ECDSA",
            CryptoRole.DIGITAL_SIGNATURE,
            transition=TransitionMode.HYBRID_TRANSITION,
        ),
        "ML_KEM_STALE_POLICY_EVIDENCE": req(
            "ML-KEM",
            CryptoRole.KEY_ESTABLISHMENT,
            checked=date(2027, 2, 1),
            max_age=120,
        ),
        "UNKNOWN_PQC_PRODUCTION_SIGNATURE": req(
            "UNREGISTERED-PQC", CryptoRole.DIGITAL_SIGNATURE
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    assert_fail_closed_registry()
    evaluated = {name: assess(request) for name, request in scenarios().items()}

    expected = {
        "ML_KEM_PRODUCTION_KEY_ESTABLISHMENT": "ELIGIBLE_FOR_BOUNDED_PRODUCTION_INTEGRATION_REVIEW",
        "ML_DSA_PRODUCTION_SIGNATURE_HYBRID": "ELIGIBLE_FOR_BOUNDED_PRODUCTION_INTEGRATION_REVIEW",
        "ML_DSA_CONSENSUS_INTERNAL_SUPPORT_ONLY": "BLOCKED_DEPLOYMENT_EVIDENCE",
        "SLH_DSA_PUBLIC_TESTNET_NODE_IDENTITY": "ELIGIBLE_FOR_PUBLIC_TESTNET_IMPLEMENTATION",
        "FN_DSA_PRODUCTION_SIGNATURE": "BLOCKED_NOT_FINALIZED",
        "HQC_PRODUCTION_KEY_ESTABLISHMENT": "BLOCKED_NOT_FINALIZED",
        "HAWK_PRODUCTION_SIGNATURE": "BLOCKED_WITHDRAWN",
        "ECDSA_HYBRID_MIGRATION_COMPONENT": "BLOCKED_CLASSICAL_ONLY",
        "ML_KEM_STALE_POLICY_EVIDENCE": "BLOCKED_POLICY_EVIDENCE",
        "UNKNOWN_PQC_PRODUCTION_SIGNATURE": "BLOCKED_UNKNOWN_ALGORITHM",
    }
    for name, verdict in expected.items():
        actual = evaluated[name].verdict
        if actual != verdict:
            raise SystemExit(f"{name}: expected {verdict}, got {actual}")

    registry = {
        algorithm_id: {
            "display_name": policy.display_name,
            "standardization_state": policy.standardization_state.value,
            "standard_reference": policy.standard_reference,
            "pq_resistant": policy.pq_resistant,
            "roles": [role.value for role in policy.roles],
            "source_urls": list(policy.source_urls),
            "evidence_as_of": policy.evidence_as_of.isoformat(),
            "notes": list(policy.notes),
        }
        for algorithm_id, policy in sorted(REGISTRY.items())
    }
    decisions = {name: result.to_dict() for name, result in sorted(evaluated.items())}

    body = {
        "schema": "WS-PQC-AGILITY-POLICY-EVIDENCE-V1",
        "status": "PASS",
        "evidence_as_of": AS_OF.isoformat(),
        "registry": registry,
        "scenarios": decisions,
        "summary": {
            "registered_algorithm_count": len(registry),
            "final_fips_pq_algorithms": [
                key
                for key, value in registry.items()
                if value["standardization_state"] == "FINAL_FIPS"
            ],
            "production_integration_review_eligible_scenarios": [
                name
                for name, decision in decisions.items()
                if decision["verdict"]
                == "ELIGIBLE_FOR_BOUNDED_PRODUCTION_INTEGRATION_REVIEW"
            ],
            "blocked_scenarios": [
                name
                for name, decision in decisions.items()
                if decision["deployment_eligible"] is False
            ],
            "production_pq_consensus_ready": False,
            "fips_module_validation_established": False,
            "federal_compliance_established": False,
            "end_to_end_pq_security_established": False,
        },
        "claim_boundary": (
            "Standards-aware algorithm lifecycle and deployment-evidence classification only; "
            "no cryptographic execution, FIPS module validation, protocol conformance, "
            "production deployment, Federal compliance, or end-to-end PQ security is established."
        ),
    }

    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    body["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
    args.output.write_text(json.dumps(body, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
