import hashlib

from worldshepherd_sara.em_d5 import (
    D5EvidencePackage,
    D5InteractionEffect,
    D5_CONTRACT_VERSION,
)
from worldshepherd_sara.em_maturity_reducer import (
    ReducedEvidenceState,
    reduce_uc06_maturity,
)
from worldshepherd_sara.em_recovery import RecoveryReceipt, RECOVERY_CONTRACT_VERSION
from worldshepherd_sara.em_sealed_receipts import (
    SealedEvidenceKind,
    VerifiedD5Evidence,
    VerifiedRecoveryEvidence,
    verify_sealed_receipt_bytes,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _verified_d5() -> VerifiedD5Evidence:
    data = b"sealed-d5\n"
    path = "/sealed/d5.txt"
    digest = _sha(data)
    effects = []
    names = [
        "STATE",
        "POLARIZATION",
        "ANGLE",
        "STATE_X_POLARIZATION",
        "STATE_X_ANGLE",
        "POLARIZATION_X_ANGLE",
        "STATE_X_POLARIZATION_X_ANGLE",
    ]
    for pc in (1, 2, 3):
        for name in names:
            effects.append(
                D5InteractionEffect(
                    principal_component=pc,
                    effect=name,
                    fraction_of_pc_variance=1.0 / 7.0,
                )
            )
    package = D5EvidencePackage(
        source_receipt=path,
        source_receipt_sha256=digest,
        interaction_effects=effects,
        claims_boundary=["DIAGNOSTIC_ONLY"],
    )
    receipt = verify_sealed_receipt_bytes(
        evidence_kind=SealedEvidenceKind.D5_DIAGNOSTIC,
        evidence_contract_version=D5_CONTRACT_VERSION,
        source_receipt=path,
        expected_sha256=digest,
        receipt_bytes=data,
    )
    return VerifiedD5Evidence(receipt=receipt, package=package)


def _verified_recovery(
    *,
    completed: int,
    zero: int,
    nonzero: int,
    checkpoints: int,
) -> VerifiedRecoveryEvidence:
    data = f"sealed-recovery:{completed}:{zero}:{nonzero}:{checkpoints}\n".encode()
    path = "/sealed/recovery.txt"
    digest = _sha(data)
    package = RecoveryReceipt(
        source_receipt=path,
        source_receipt_sha256=digest,
        completed_job_count=completed,
        exit_zero_count=zero,
        nonzero_exit_count=nonzero,
        durable_checkpoint_count=checkpoints,
        replacement_a027_fresh_output=True,
        direct_mpi_binary_topology=True,
        mpi_stdin_none=True,
        palace_stdin_dev_null=True,
        sleep_inhibitor_used=True,
    )
    receipt = verify_sealed_receipt_bytes(
        evidence_kind=SealedEvidenceKind.POWER_RECOVERY,
        evidence_contract_version=RECOVERY_CONTRACT_VERSION,
        source_receipt=path,
        expected_sha256=digest,
        receipt_bytes=data,
    )
    return VerifiedRecoveryEvidence(receipt=receipt, package=package)


def test_default_reducer_matches_conservative_repository_state():
    state = reduce_uc06_maturity()
    assert state.d5_interaction_sparse_analysis == ReducedEvidenceState.PENDING
    assert state.recovery_a027_a054_completion == ReducedEvidenceState.NOT_INGESTED
    assert state.medium_fine_convergence == ReducedEvidenceState.NOT_ADJUDICATED
    assert state.energy_closure == ReducedEvidenceState.PENDING
    assert state.hardware_action == ReducedEvidenceState.NOT_AUTHORIZED
    assert state.persisted_state_mutation is False


def test_verified_d5_advances_only_d5_diagnostic_state():
    state = reduce_uc06_maturity(d5=_verified_d5())
    assert state.d5_interaction_sparse_analysis == ReducedEvidenceState.INGESTED_DIAGNOSTIC
    assert state.medium_fine_convergence == ReducedEvidenceState.NOT_ADJUDICATED
    assert state.energy_closure == ReducedEvidenceState.PENDING
    assert state.hardware_action == ReducedEvidenceState.NOT_AUTHORIZED
    assert "SEALED_D5_RESULT_RECEIPT" not in state.next_required_evidence


def test_complete_verified_recovery_establishes_execution_only():
    state = reduce_uc06_maturity(
        recovery=_verified_recovery(completed=28, zero=28, nonzero=0, checkpoints=28)
    )
    assert state.recovery_a027_a054_completion == ReducedEvidenceState.EXECUTION_COMPLETE
    assert state.medium_fine_convergence == ReducedEvidenceState.NOT_ADJUDICATED
    assert state.energy_closure == ReducedEvidenceState.PENDING
    assert state.hardware_action == ReducedEvidenceState.NOT_AUTHORIZED
    assert "SEALED_A027_A054_RECOVERY_COMPLETION_RECEIPT" not in state.next_required_evidence


def test_incomplete_verified_recovery_stays_incomplete_not_failed():
    state = reduce_uc06_maturity(
        recovery=_verified_recovery(completed=10, zero=10, nonzero=0, checkpoints=10)
    )
    assert state.recovery_a027_a054_completion == ReducedEvidenceState.INCOMPLETE
    assert "RECOVERY_INCOMPLETE_NOT_MISLABELED_AS_FAILURE" in state.claims_boundary
    assert "SEALED_A027_A054_RECOVERY_COMPLETION_RECEIPT" in state.next_required_evidence


def test_known_nonzero_exit_is_retained_as_failure():
    state = reduce_uc06_maturity(
        recovery=_verified_recovery(completed=28, zero=27, nonzero=1, checkpoints=28)
    )
    assert state.recovery_a027_a054_completion == ReducedEvidenceState.FAIL
    assert "RECOVERY_FAILURE_RETAINED_VISIBLE" in state.claims_boundary
    assert state.hardware_action == ReducedEvidenceState.NOT_AUTHORIZED


def test_d5_plus_complete_recovery_still_does_not_close_science():
    state = reduce_uc06_maturity(
        d5=_verified_d5(),
        recovery=_verified_recovery(completed=28, zero=28, nonzero=0, checkpoints=28),
    )
    assert state.d5_interaction_sparse_analysis == ReducedEvidenceState.INGESTED_DIAGNOSTIC
    assert state.recovery_a027_a054_completion == ReducedEvidenceState.EXECUTION_COMPLETE
    assert state.medium_fine_convergence == ReducedEvidenceState.NOT_ADJUDICATED
    assert state.physical_validation == ReducedEvidenceState.NOT_VALIDATED
    assert state.full_campaign == ReducedEvidenceState.NOT_AUTHORIZED
    assert state.hardware_action == ReducedEvidenceState.NOT_AUTHORIZED
