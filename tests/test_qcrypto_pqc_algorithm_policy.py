from datetime import date

import pytest

from security.qcrypto.pqc_algorithm_policy import (
    AlgorithmRequest,
    CryptoRole,
    Environment,
    REGISTRY,
    StandardizationState,
    SupportTier,
    TransitionMode,
    assess,
    assert_fail_closed_registry,
    validate_registry,
)


def request(
    algorithm_id: str,
    *,
    role: CryptoRole,
    environment: Environment = Environment.PRODUCTION,
    support: SupportTier = SupportTier.PRODUCTION,
    transition: TransitionMode = TransitionMode.PQ_ONLY,
    checked: date = date(2026, 9, 15),
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


def test_registry_has_finalized_nist_pqc_core_and_fail_closed_candidates():
    validate_registry()
    assert REGISTRY["ML-KEM"].standardization_state is StandardizationState.FINAL_FIPS
    assert REGISTRY["ML-DSA"].standardization_state is StandardizationState.FINAL_FIPS
    assert REGISTRY["SLH-DSA"].standardization_state is StandardizationState.FINAL_FIPS
    assert REGISTRY["FN-DSA"].standardization_state is StandardizationState.FIPS_IN_DEVELOPMENT
    assert REGISTRY["HQC"].standardization_state is StandardizationState.SELECTED_FOR_STANDARDIZATION
    assert REGISTRY["HAWK"].standardization_state is StandardizationState.WITHDRAWN
    assert_fail_closed_registry()


def test_ml_kem_requires_key_establishment_role():
    allowed = assess(request("ML-KEM", role=CryptoRole.KEY_ESTABLISHMENT))
    assert allowed.standards_eligible is True
    assert allowed.deployment_eligible is True
    assert allowed.verdict == "ELIGIBLE_FOR_BOUNDED_PRODUCTION_INTEGRATION_REVIEW"

    blocked = assess(request("ML-KEM", role=CryptoRole.DIGITAL_SIGNATURE))
    assert blocked.standards_eligible is False
    assert blocked.deployment_eligible is False
    assert blocked.verdict == "BLOCKED_ROLE_MISMATCH"
    assert any("not registered for role" in item for item in blocked.blockers)


def test_final_fips_does_not_bypass_protocol_support_requirement():
    result = assess(
        request(
            "ML-DSA",
            role=CryptoRole.CONSENSUS_AUTH,
            environment=Environment.PRODUCTION,
            support=SupportTier.INTERNAL,
        )
    )
    assert result.standards_eligible is True
    assert result.deployment_eligible is False
    assert result.verdict == "BLOCKED_DEPLOYMENT_EVIDENCE"
    assert any("PRODUCTION protocol/client support" in item for item in result.blockers)


def test_public_testnet_requires_public_testnet_support():
    blocked = assess(
        request(
            "SLH-DSA",
            role=CryptoRole.NODE_IDENTITY,
            environment=Environment.TESTNET,
            support=SupportTier.INTERNAL,
        )
    )
    assert blocked.deployment_eligible is False

    allowed = assess(
        request(
            "SLH-DSA",
            role=CryptoRole.NODE_IDENTITY,
            environment=Environment.TESTNET,
            support=SupportTier.PUBLIC_TESTNET,
        )
    )
    assert allowed.deployment_eligible is True
    assert allowed.verdict == "ELIGIBLE_FOR_PUBLIC_TESTNET_IMPLEMENTATION"


@pytest.mark.parametrize(
    ("algorithm_id", "role", "expected"),
    [
        ("FN-DSA", CryptoRole.DIGITAL_SIGNATURE, "BLOCKED_NOT_FINALIZED"),
        ("HQC", CryptoRole.KEY_ESTABLISHMENT, "BLOCKED_NOT_FINALIZED"),
        ("HAWK", CryptoRole.DIGITAL_SIGNATURE, "BLOCKED_WITHDRAWN"),
        ("ED25519", CryptoRole.DIGITAL_SIGNATURE, "BLOCKED_CLASSICAL_ONLY"),
        ("ECDSA", CryptoRole.DIGITAL_SIGNATURE, "BLOCKED_CLASSICAL_ONLY"),
    ],
)
def test_nonfinal_or_classical_algorithms_never_promote_to_pq_production(
    algorithm_id, role, expected
):
    transition = (
        TransitionMode.HYBRID_TRANSITION
        if algorithm_id in {"ED25519", "ECDSA"}
        else TransitionMode.PQ_ONLY
    )
    result = assess(request(algorithm_id, role=role, transition=transition))
    assert result.deployment_eligible is False
    assert result.verdict == expected


def test_stale_algorithm_policy_evidence_blocks_even_final_fips():
    result = assess(
        request(
            "ML-KEM",
            role=CryptoRole.KEY_ESTABLISHMENT,
            checked=date(2027, 2, 1),
            max_age=120,
        )
    )
    assert result.standards_eligible is True
    assert result.deployment_eligible is False
    assert result.verdict == "BLOCKED_POLICY_EVIDENCE"
    assert any("stale" in item.lower() for item in result.blockers)


def test_hybrid_transition_never_claims_end_to_end_pq_only():
    result = assess(
        request(
            "ML-DSA",
            role=CryptoRole.DIGITAL_SIGNATURE,
            transition=TransitionMode.HYBRID_TRANSITION,
        )
    )
    assert result.deployment_eligible is True
    assert result.pq_posture == "HYBRID_PQ_TRANSITION_COMPONENT"
    assert any("do not label the end-to-end system PQ-only" in item for item in result.warnings)


def test_unknown_algorithm_fails_closed():
    result = assess(request("UNREGISTERED-PQC", role=CryptoRole.DIGITAL_SIGNATURE))
    assert result.verdict == "BLOCKED_UNKNOWN_ALGORITHM"
    assert result.standards_eligible is False
    assert result.deployment_eligible is False
    assert result.pq_posture == "UNKNOWN"


def test_claim_boundary_does_not_self_certify():
    result = assess(request("ML-DSA", role=CryptoRole.DIGITAL_SIGNATURE))
    lower = result.claim_boundary.lower()
    assert "does not establish fips module validation" in lower
    assert "federal compliance" in lower
    assert "end-to-end post-quantum security" in lower
