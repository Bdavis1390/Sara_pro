from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldshepherd_sara.em_d5 import (
    D5EvidencePackage,
    D5InteractionEffect,
    D5SparseFrequencySelection,
    D5Status,
    SparseInterrogationReadiness,
    evaluate_sparse_interrogation_readiness,
    pending_d5_status,
)


def _effects() -> list[D5InteractionEffect]:
    names = [
        "STATE",
        "POLARIZATION",
        "ANGLE",
        "STATE_X_POLARIZATION",
        "STATE_X_ANGLE",
        "POLARIZATION_X_ANGLE",
        "STATE_X_POLARIZATION_X_ANGLE",
    ]
    rows: list[D5InteractionEffect] = []
    for pc in (1, 2, 3):
        fractions = [0.10, 0.20, 0.15, 0.10, 0.15, 0.20, 0.10]
        rows.extend(
            D5InteractionEffect(
                principal_component=pc,
                effect=name,
                fraction_of_pc_variance=fraction,
            )
            for name, fraction in zip(names, fractions)
        )
    return rows


def test_d5_status_is_pending_without_result_values() -> None:
    status = pending_d5_status()
    assert status.status == D5Status.PENDING
    assert status.sealed_result_ingested is False
    assert status.result_values_available is False
    assert status.overall_convergence == "NOT_ADJUDICATED"
    assert "NO_D5_RESULT_VALUES_INGESTED" in status.claims_boundary


def test_d5_package_accepts_structurally_closed_diagnostic_bundle() -> None:
    package = D5EvidencePackage(
        source_receipt="local:r2r-b0-d5-example",
        source_receipt_sha256="a" * 64,
        interaction_effects=_effects(),
        sparse_frequency_selections=[
            D5SparseFrequencySelection(
                mode="SPACED_0P10GHZ",
                frequencies_GHz=[9.2, 9.4, 9.6],
                pairwise_distance_correlation=0.9,
                normalized_scaled_stress=0.1,
            )
        ],
        claims_boundary=["DIAGNOSTIC_ONLY"],
    )
    assert package.evidence_integrity_pass is True
    assert package.active_recovery_touched is False
    assert package.scientific_gate_change is False


def test_d5_package_rejects_broken_variance_closure() -> None:
    rows = _effects()
    rows[0] = D5InteractionEffect(
        principal_component=1,
        effect="STATE",
        fraction_of_pc_variance=0.11,
    )
    with pytest.raises(ValidationError):
        D5EvidencePackage(
            source_receipt="local:r2r-b0-d5-example",
            source_receipt_sha256="b" * 64,
            interaction_effects=rows,
            claims_boundary=["DIAGNOSTIC_ONLY"],
        )


def test_spaced_selection_rejects_too_close_frequencies() -> None:
    with pytest.raises(ValidationError):
        D5SparseFrequencySelection(
            mode="SPACED_0P10GHZ",
            frequencies_GHz=[9.2, 9.25],
        )


def test_sparse_interrogation_fails_closed_by_default() -> None:
    decision = evaluate_sparse_interrogation_readiness(SparseInterrogationReadiness())
    assert decision.eligible_for_operational_interrogation is False
    assert decision.hardware_action_authorized is False
    assert "D5_SEALED_EVIDENCE" in decision.unresolved_gates
    assert "FAIL_CLOSED" in decision.rationale_codes


def test_sparse_interrogation_eligibility_still_does_not_authorize_hardware() -> None:
    decision = evaluate_sparse_interrogation_readiness(
        SparseInterrogationReadiness(
            d5_sealed_evidence_ingested=True,
            pairwise_geometry_preserved_on_held_out_data=True,
            task_discriminability_preserved_on_held_out_data=True,
            measurement_repeatability_validated=True,
            hardware_measurement_validated=True,
            medium_fine_convergence_passed=True,
            energy_closure_passed=True,
            prime_review_complete=True,
        )
    )
    assert decision.eligible_for_operational_interrogation is True
    assert decision.hardware_action_authorized is False
    assert decision.unresolved_gates == []
