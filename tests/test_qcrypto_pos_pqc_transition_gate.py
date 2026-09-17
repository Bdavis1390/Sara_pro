from __future__ import annotations

from datetime import date

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


def synthetic_production_record() -> ReadinessEvidence:
    return ReadinessEvidence(
        profile_id="SYNTHETIC_PRODUCTION_TEST_ONLY",
        evidence=tuple((axis, EvidenceTier.PRODUCTION) for axis in AXES),
        external_state="SYNTHETIC_TEST_ONLY",
        notes=("Synthetic all-production evidence fixture; not a real network claim.",),
    )


def test_qrl2_mldsa_can_reach_public_testnet_candidate_but_not_production_ready():
    result = assess_transition(
        BENCHMARK_EVIDENCE["QRL2_TESTNET"],
        alg(
            "ML-DSA",
            environment=Environment.TESTNET,
            support=SupportTier.PUBLIC_TESTNET,
        ),
    )
    assert result.verdict == "PUBLIC_TESTNET_PQ_VALIDATOR_AUTH_CANDIDATE"
    assert result.algorithm_policy_pass is True
    assert result.system_evidence_pass is True
    assert result.transition_candidate is True
    assert result.production_integration_review_eligible is False
    assert result.production_pq_consensus_ready is False
    assert result.end_to_end_pq_security_established is False


def test_protocol_testnet_evidence_cannot_bypass_nonfinal_algorithm_policy():
    result = assess_transition(
        BENCHMARK_EVIDENCE["QRL2_TESTNET"],
        alg(
            "FN-DSA",
            environment=Environment.TESTNET,
            support=SupportTier.PUBLIC_TESTNET,
        ),
    )
    assert result.verdict == "BLOCKED_ALGORITHM_POLICY"
    assert result.algorithm_policy_pass is False
    assert result.system_evidence_pass is True
    assert result.transition_candidate is False
    assert "BLOCKED_NOT_FINALIZED" in result.blockers[0]


def test_final_fips_algorithm_cannot_bypass_ethereum_system_readiness():
    result = assess_transition(
        TARGET_EVIDENCE["ETHEREUM"],
        alg(
            "ML-DSA",
            environment=Environment.TESTNET,
            support=SupportTier.PUBLIC_TESTNET,
        ),
    )
    assert result.algorithm_policy_pass is True
    assert result.system_evidence_pass is False
    assert result.verdict == "BLOCKED_SYSTEM_READINESS"
    assert "consensus_signature_acceptance" in result.blocking_system_axes
    assert "protocol_client_support" in result.blocking_system_axes
    assert result.production_pq_consensus_ready is False


def test_algorand_production_pq_account_component_does_not_promote_consensus():
    result = assess_transition(
        TARGET_EVIDENCE["ALGORAND"],
        alg(
            "ML-DSA",
            environment=Environment.PRODUCTION,
            support=SupportTier.PRODUCTION,
        ),
    )
    assert result.algorithm_policy_pass is True
    assert result.system_evidence_pass is False
    assert result.verdict == "BLOCKED_SYSTEM_READINESS"
    assert result.production_integration_review_eligible is False
    assert "consensus_signature_acceptance" in result.blocking_system_axes


def test_hybrid_testnet_candidate_is_explicitly_not_end_to_end_pq_only():
    result = assess_transition(
        BENCHMARK_EVIDENCE["QRL2_TESTNET"],
        alg(
            "ML-DSA",
            environment=Environment.TESTNET,
            support=SupportTier.PUBLIC_TESTNET,
            transition=TransitionMode.HYBRID_TRANSITION,
        ),
    )
    assert result.verdict == "PUBLIC_TESTNET_HYBRID_VALIDATOR_AUTH_CANDIDATE"
    assert result.hybrid_dependency_present is True
    assert result.end_to_end_pq_security_established is False
    assert any("end-to-end PQ-only status is prohibited" in warning for warning in result.warnings)


def test_stale_algorithm_policy_blocks_even_when_protocol_testnet_evidence_exists():
    result = assess_transition(
        BENCHMARK_EVIDENCE["QRL2_TESTNET"],
        alg(
            "ML-DSA",
            environment=Environment.TESTNET,
            support=SupportTier.PUBLIC_TESTNET,
            checked=date(2027, 2, 1),
        ),
    )
    assert result.verdict == "BLOCKED_ALGORITHM_POLICY"
    assert result.system_evidence_pass is True
    assert result.algorithm_policy_pass is False
    assert any("stale" in blocker.lower() for blocker in result.blockers)


def test_unknown_algorithm_blocks_even_when_protocol_evidence_exists():
    result = assess_transition(
        BENCHMARK_EVIDENCE["QRL2_TESTNET"],
        alg(
            "UNREGISTERED-PQC",
            environment=Environment.TESTNET,
            support=SupportTier.PUBLIC_TESTNET,
        ),
    )
    assert result.verdict == "BLOCKED_ALGORITHM_POLICY"
    assert result.algorithm_policy_pass is False
    assert result.transition_candidate is False


def test_synthetic_all_production_evidence_only_reaches_bounded_integration_review():
    result = assess_transition(
        synthetic_production_record(),
        alg(
            "ML-DSA",
            environment=Environment.PRODUCTION,
            support=SupportTier.PRODUCTION,
        ),
    )
    assert result.verdict == "BOUNDED_PRODUCTION_PQ_CONSENSUS_INTEGRATION_REVIEW"
    assert result.algorithm_policy_pass is True
    assert result.system_evidence_pass is True
    assert result.production_integration_review_eligible is True
    assert result.production_pq_consensus_ready is False
    assert result.end_to_end_pq_security_established is False


def test_production_system_readiness_cannot_rescue_withdrawn_algorithm():
    result = assess_transition(
        synthetic_production_record(),
        alg(
            "HAWK",
            environment=Environment.PRODUCTION,
            support=SupportTier.PRODUCTION,
        ),
    )
    assert result.system_evidence_pass is True
    assert result.algorithm_policy_pass is False
    assert result.verdict == "BLOCKED_ALGORITHM_POLICY"
    assert result.production_integration_review_eligible is False


def test_claim_boundary_never_self_certifies():
    result = assess_transition(
        BENCHMARK_EVIDENCE["QRL2_TESTNET"],
        alg(
            "ML-DSA",
            environment=Environment.TESTNET,
            support=SupportTier.PUBLIC_TESTNET,
        ),
    )
    lower = result.claim_boundary.lower()
    assert "does not establish production pq consensus readiness" in lower
    assert "fips module validation" in lower
    assert "federal compliance" in lower
    assert "live-value authorization" in lower
