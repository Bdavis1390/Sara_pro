#!/usr/bin/env python3
"""Generate machine-readable evidence for the two-key PoS/PQC transition gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from security.qcrypto.pos_pq_readiness import (
    AXES,
    BENCHMARK_EVIDENCE,
    TARGET_EVIDENCE,
    EvidenceTier,
    ReadinessEvidence,
)
from security.qcrypto.pos_pqc_transition_gate import assess_transition
from security.qcrypto.pqc_algorithm_policy import (
    AlgorithmRequest,
    CryptoRole,
    Environment,
    SupportTier,
    TransitionMode,
)


AS_OF = date(2026, 9, 15)


def alg(
    algorithm_id: str,
    *,
    environment: Environment,
    support: SupportTier,
    transition: TransitionMode = TransitionMode.PQ_ONLY,
    checked: date = AS_OF,
) -> AlgorithmRequest:
    return AlgorithmRequest(
        algorithm_id=algorithm_id,
        role=CryptoRole.CONSENSUS_AUTH,
        environment=environment,
        support_tier=support,
        transition_mode=transition,
        evidence_checked_on=checked,
    )


def synthetic_production() -> ReadinessEvidence:
    return ReadinessEvidence(
        profile_id="SYNTHETIC_PRODUCTION_TEST_ONLY",
        evidence=tuple((axis, EvidenceTier.PRODUCTION) for axis in AXES),
        external_state="SYNTHETIC_TEST_ONLY_NOT_REAL_NETWORK_EVIDENCE",
        notes=("Synthetic gate fixture only; cannot support a real-network claim.",),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    cases = {
        "QRL2_ML_DSA_TESTNET": (
            BENCHMARK_EVIDENCE["QRL2_TESTNET"],
            alg(
                "ML-DSA",
                environment=Environment.TESTNET,
                support=SupportTier.PUBLIC_TESTNET,
            ),
        ),
        "QRL2_FN_DSA_TESTNET": (
            BENCHMARK_EVIDENCE["QRL2_TESTNET"],
            alg(
                "FN-DSA",
                environment=Environment.TESTNET,
                support=SupportTier.PUBLIC_TESTNET,
            ),
        ),
        "ETHEREUM_ML_DSA_TESTNET": (
            TARGET_EVIDENCE["ETHEREUM"],
            alg(
                "ML-DSA",
                environment=Environment.TESTNET,
                support=SupportTier.PUBLIC_TESTNET,
            ),
        ),
        "ALGORAND_ML_DSA_PRODUCTION": (
            TARGET_EVIDENCE["ALGORAND"],
            alg(
                "ML-DSA",
                environment=Environment.PRODUCTION,
                support=SupportTier.PRODUCTION,
            ),
        ),
        "QRL2_STALE_ML_DSA": (
            BENCHMARK_EVIDENCE["QRL2_TESTNET"],
            alg(
                "ML-DSA",
                environment=Environment.TESTNET,
                support=SupportTier.PUBLIC_TESTNET,
                checked=date(2027, 2, 1),
            ),
        ),
        "QRL2_HYBRID_ML_DSA": (
            BENCHMARK_EVIDENCE["QRL2_TESTNET"],
            alg(
                "ML-DSA",
                environment=Environment.TESTNET,
                support=SupportTier.PUBLIC_TESTNET,
                transition=TransitionMode.HYBRID_TRANSITION,
            ),
        ),
        "SYNTHETIC_PRODUCTION_ML_DSA": (
            synthetic_production(),
            alg(
                "ML-DSA",
                environment=Environment.PRODUCTION,
                support=SupportTier.PRODUCTION,
            ),
        ),
        "SYNTHETIC_PRODUCTION_HAWK": (
            synthetic_production(),
            alg(
                "HAWK",
                environment=Environment.PRODUCTION,
                support=SupportTier.PRODUCTION,
            ),
        ),
    }

    results = {
        name: assess_transition(record, request).to_dict()
        for name, (record, request) in cases.items()
    }

    expected = {
        "QRL2_ML_DSA_TESTNET": "PUBLIC_TESTNET_PQ_VALIDATOR_AUTH_CANDIDATE",
        "QRL2_FN_DSA_TESTNET": "BLOCKED_ALGORITHM_POLICY",
        "ETHEREUM_ML_DSA_TESTNET": "BLOCKED_SYSTEM_READINESS",
        "ALGORAND_ML_DSA_PRODUCTION": "BLOCKED_SYSTEM_READINESS",
        "QRL2_STALE_ML_DSA": "BLOCKED_ALGORITHM_POLICY",
        "QRL2_HYBRID_ML_DSA": "PUBLIC_TESTNET_HYBRID_VALIDATOR_AUTH_CANDIDATE",
        "SYNTHETIC_PRODUCTION_ML_DSA": "BOUNDED_PRODUCTION_PQ_CONSENSUS_INTEGRATION_REVIEW",
        "SYNTHETIC_PRODUCTION_HAWK": "BLOCKED_ALGORITHM_POLICY",
    }
    for name, verdict in expected.items():
        if results[name]["verdict"] != verdict:
            raise SystemExit(
                f"{name}: expected {verdict}, got {results[name]['verdict']}"
            )

    real_world = {
        name: result
        for name, result in results.items()
        if not name.startswith("SYNTHETIC_")
    }
    if any(item["production_pq_consensus_ready"] for item in real_world.values()):
        raise SystemExit("real-world scenario was improperly promoted to production PQ consensus")
    if any(item["end_to_end_pq_security_established"] for item in results.values()):
        raise SystemExit("scenario was improperly promoted to end-to-end PQ security")

    evidence = {
        "schema": "WS-POS-PQC-TRANSITION-EVIDENCE-V1",
        "status": "PASS",
        "evidence_as_of": AS_OF.isoformat(),
        "results": results,
        "summary": {
            "scenario_count": len(results),
            "real_world_production_pq_consensus_ready_count": 0,
            "end_to_end_pq_security_established_count": 0,
            "public_testnet_candidates": [
                name
                for name, result in results.items()
                if result["verdict"] in {
                    "PUBLIC_TESTNET_PQ_VALIDATOR_AUTH_CANDIDATE",
                    "PUBLIC_TESTNET_HYBRID_VALIDATOR_AUTH_CANDIDATE",
                }
            ],
            "bounded_production_integration_review": [
                name
                for name, result in results.items()
                if result["production_integration_review_eligible"]
            ],
            "bounded_production_review_is_synthetic_only": True,
        },
        "claim_boundary": (
            "Two-key algorithm-policy plus system-readiness evidence only. Public-testnet "
            "validator-auth candidates are not production-mainnet PQ consensus. The synthetic "
            "all-production fixture tests gating logic only. No end-to-end PQ security, FIPS "
            "module validation, Federal compliance, live-value authority, or deployment authority is established."
        ),
    }
    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    evidence["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
