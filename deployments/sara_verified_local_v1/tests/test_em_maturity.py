from worldshepherd_sara.em_maturity import EvidenceState, current_uc06_maturity


def test_uc06_maturity_is_conservative_and_read_only() -> None:
    status = current_uc06_maturity()
    assert status.read_only is True
    assert status.d4_capability_attribution == EvidenceState.ESTABLISHED_DIAGNOSTIC
    assert status.d5_interaction_sparse_analysis == EvidenceState.PENDING
    assert status.recovery_a027_a054_completion == EvidenceState.NOT_INGESTED
    assert status.medium_fine_convergence == EvidenceState.NOT_ADJUDICATED
    assert status.energy_closure == EvidenceState.PENDING
    assert status.physical_validation == EvidenceState.NOT_VALIDATED
    assert status.hardware_action == EvidenceState.NOT_AUTHORIZED
    assert status.software_ci_is_physics_validation is False


def test_missing_recovery_evidence_is_not_mislabeled_as_failure() -> None:
    status = current_uc06_maturity()
    assert "RECOVERY_COMPLETION_NOT_INGESTED_NOT_FAILED" in status.claims_boundary
    assert "CONVERGENCE_NOT_ADJUDICATED_NOT_FAILED" in status.claims_boundary


def test_next_evidence_preserves_prime_separation() -> None:
    status = current_uc06_maturity()
    assert "EXPLICIT_PRIME_RELEASE_BEFORE_ANY_HARDWARE_ACTION" in status.next_required_evidence
    assert "NO_HARDWARE_ACTION" in status.claims_boundary
