from worldshepherd_sara.em_recovery import (
    RecoveryReceipt,
    RecoveryStatus,
    current_recovery_status,
    evaluate_recovery_receipt,
)


def _receipt(**overrides) -> RecoveryReceipt:
    data = dict(
        source_receipt="local:r2r-a-r1-r1-example",
        source_receipt_sha256="a" * 64,
        completed_job_count=28,
        exit_zero_count=28,
        nonzero_exit_count=0,
        retained_output_count=28,
        durable_checkpoint_count=28,
        replacement_a027_fresh_output=True,
        direct_mpi_binary_topology=True,
        mpi_stdin_none=True,
        palace_stdin_dev_null=True,
        sleep_inhibitor_used=True,
    )
    data.update(overrides)
    return RecoveryReceipt(**data)


def test_repository_recovery_status_is_not_ingested() -> None:
    status = current_recovery_status()
    assert status["status"] == "NOT_INGESTED"
    assert status["sealed_completion_receipt_ingested"] is False
    assert status["scientific_convergence"] == "NOT_ADJUDICATED"
    assert status["hardware_actions"] is False


def test_complete_conforming_recovery_establishes_execution_coverage_only() -> None:
    decision = evaluate_recovery_receipt(_receipt())
    assert decision.status == RecoveryStatus.EXECUTION_COMPLETE
    assert decision.combined_anchor_coverage == 54
    assert decision.scientific_convergence == "NOT_ADJUDICATED"
    assert decision.hardware_action_authorized is False
    assert decision.unresolved_protocol_requirements == []


def test_incomplete_recovery_remains_incomplete_not_failed() -> None:
    decision = evaluate_recovery_receipt(
        _receipt(
            completed_job_count=20,
            exit_zero_count=20,
            retained_output_count=20,
            durable_checkpoint_count=20,
        )
    )
    assert decision.status == RecoveryStatus.INCOMPLETE
    assert decision.combined_anchor_coverage == 46
    assert "A027_A054_COMPLETION" in decision.unresolved_protocol_requirements


def test_known_nonzero_exit_is_failure_even_before_segment_completion() -> None:
    decision = evaluate_recovery_receipt(
        _receipt(
            completed_job_count=20,
            exit_zero_count=19,
            nonzero_exit_count=1,
            retained_output_count=20,
            durable_checkpoint_count=20,
        )
    )
    assert decision.status == RecoveryStatus.FAIL
    assert "ZERO_EXIT_ALL_RECOVERY_JOBS" in decision.unresolved_protocol_requirements


def test_missing_preregistered_sleep_inhibitor_fails_complete_segment() -> None:
    decision = evaluate_recovery_receipt(_receipt(sleep_inhibitor_used=False))
    assert decision.status == RecoveryStatus.FAIL
    assert "SLEEP_INHIBITOR" in decision.unresolved_protocol_requirements


def test_missing_retained_output_coverage_fails_complete_segment() -> None:
    decision = evaluate_recovery_receipt(_receipt(retained_output_count=27))
    assert decision.status == RecoveryStatus.FAIL
    assert "RETAINED_OUTPUT_COVERAGE" in decision.unresolved_protocol_requirements


def test_recovery_never_upgrades_scientific_convergence() -> None:
    decision = evaluate_recovery_receipt(_receipt())
    assert decision.scientific_convergence == "NOT_ADJUDICATED"
    assert "CONVERGENCE_REMAINS_SEPARATE" in decision.rationale_codes
