import hashlib

import pytest

from worldshepherd_sara.em_convergence import (
    EnergyClosureEvidence,
    ExecutionCompletenessEvidence,
    FrozenConvergenceInput,
    MediumFinePairEvidence,
    ResonanceEvidenceState,
)
from worldshepherd_sara.em_convergence_evidence import (
    CONVERGENCE_EVIDENCE_SCHEMA_VERSION,
    ConvergenceEvidencePackage,
    build_convergence_evidence_package,
)
from worldshepherd_sara.em_maturity_reducer import (
    ReducedEvidenceState,
    reduce_uc06_maturity,
)
from worldshepherd_sara.em_sealed_receipts import (
    SealedEvidenceKind,
    VerifiedConvergenceEvidence,
    verify_sealed_receipt_bytes,
)


def _pairs(
    *,
    complex_delta: float = 0.02,
    resonance_state: ResonanceEvidenceState = ResonanceEvidenceState.EVALUABLE,
    resonance_shift: float | None = 0.0025,
) -> list[MediumFinePairEvidence]:
    if resonance_state != ResonanceEvidenceState.EVALUABLE:
        resonance_shift = None
    return [
        MediumFinePairEvidence(
            state=state,
            polarization=pol,
            angle_deg=angle,
            max_complex_s11_delta=complex_delta,
            resonance_evidence=resonance_state,
            resonance_shift_fraction=resonance_shift,
        )
        for state in ("LOW_C", "HIGH_C", "SAFE_OPEN")
        for pol in ("TE", "TM")
        for angle in (0, 30, 60)
    ]


def _energy(*, error: float = 0.02) -> list[EnergyClosureEvidence]:
    return [
        EnergyClosureEvidence(
            anchor_id=anchor,
            available=True,
            closure_error_fraction=error,
        )
        for anchor in range(1, 55)
    ]


def _input(
    *,
    pairs: list[MediumFinePairEvidence] | None = None,
    energy: list[EnergyClosureEvidence] | None = None,
) -> FrozenConvergenceInput:
    return FrozenConvergenceInput(
        execution=ExecutionCompletenessEvidence(
            completed_anchor_count=54,
            exit_zero_count=54,
            nonzero_exit_count=0,
            parseable_output_count=54,
            retained_output_count=54,
            failures_visible=True,
        ),
        medium_fine_pairs=pairs if pairs is not None else _pairs(),
        energy_closure=energy if energy is not None else _energy(),
    )


def _verified(evidence: FrozenConvergenceInput) -> VerifiedConvergenceEvidence:
    raw_receipt = b"sealed-frozen-convergence-evidence\n"
    digest = hashlib.sha256(raw_receipt).hexdigest()
    source = "/sealed/convergence.json"
    package = build_convergence_evidence_package(
        source_receipt=source,
        source_receipt_sha256=digest,
        parser_id="uc06-d6e-parser",
        parser_version="1.0.0",
        evidence=evidence,
        claims_boundary=["FROZEN_D6E_ONLY", "NO_GATE_CHANGE"],
    )
    receipt = verify_sealed_receipt_bytes(
        evidence_kind=SealedEvidenceKind.FROZEN_CONVERGENCE,
        evidence_contract_version=CONVERGENCE_EVIDENCE_SCHEMA_VERSION,
        source_receipt=source,
        expected_sha256=digest,
        receipt_bytes=raw_receipt,
    )
    return VerifiedConvergenceEvidence(receipt=receipt, package=package)


def test_payload_digest_is_canonical_and_tamper_evident():
    raw_receipt = b"sealed-frozen-convergence-evidence\n"
    digest = hashlib.sha256(raw_receipt).hexdigest()
    evidence = _input()
    package = build_convergence_evidence_package(
        source_receipt="/sealed/convergence.json",
        source_receipt_sha256=digest,
        parser_id="uc06-d6e-parser",
        parser_version="1.0.0",
        evidence=evidence,
        claims_boundary=["FROZEN_D6E_ONLY"],
    )
    assert len(package.evidence_payload_sha256) == 64

    with pytest.raises(ValueError, match="payload SHA mismatch"):
        ConvergenceEvidencePackage(
            source_receipt=package.source_receipt,
            source_receipt_sha256=package.source_receipt_sha256,
            parser_id=package.parser_id,
            parser_version=package.parser_version,
            evidence_payload_sha256="0" * 64,
            evidence=evidence,
            claims_boundary=["FROZEN_D6E_ONLY"],
        )


def test_verified_full_frozen_pass_does_not_authorize_physical_use():
    state = reduce_uc06_maturity(convergence=_verified(_input()))
    assert state.frozen_convergence_overall == ReducedEvidenceState.PASS
    assert state.medium_fine_convergence == ReducedEvidenceState.PASS
    assert state.energy_closure == ReducedEvidenceState.PASS
    assert state.physical_validation == ReducedEvidenceState.NOT_VALIDATED
    assert state.full_campaign == ReducedEvidenceState.NOT_AUTHORIZED
    assert state.hardware_action == ReducedEvidenceState.NOT_AUTHORIZED


def test_boundary_resonance_is_not_evaluable_not_pass():
    state = reduce_uc06_maturity(
        convergence=_verified(
            _input(
                pairs=_pairs(
                    resonance_state=ResonanceEvidenceState.BOUNDARY_MINIMUM,
                )
            )
        )
    )
    assert state.frozen_convergence_overall == ReducedEvidenceState.NOT_EVALUABLE
    assert state.medium_fine_convergence == ReducedEvidenceState.NOT_EVALUABLE
    assert state.energy_closure == ReducedEvidenceState.PASS
    assert "FROZEN_CONVERGENCE_MISSING_OR_BOUNDARY_EVIDENCE" in state.next_required_evidence


def test_complex_s11_failure_remains_visible_separately_from_energy():
    pairs = _pairs()
    pairs[0] = pairs[0].model_copy(update={"max_complex_s11_delta": 0.0200001})
    state = reduce_uc06_maturity(convergence=_verified(_input(pairs=pairs)))
    assert state.frozen_convergence_overall == ReducedEvidenceState.FAIL
    assert state.medium_fine_convergence == ReducedEvidenceState.FAIL
    assert state.energy_closure == ReducedEvidenceState.PASS
    assert "FROZEN_CONVERGENCE_FAILURE_REMEDIATION" in state.next_required_evidence


def test_energy_failure_does_not_get_hidden_by_medium_fine_pass():
    energy = _energy()
    energy[0] = energy[0].model_copy(update={"closure_error_fraction": 0.0200001})
    state = reduce_uc06_maturity(convergence=_verified(_input(energy=energy)))
    assert state.frozen_convergence_overall == ReducedEvidenceState.FAIL
    assert state.medium_fine_convergence == ReducedEvidenceState.PASS
    assert state.energy_closure == ReducedEvidenceState.FAIL
    assert "ENERGY_CLOSURE_FAILURE_REMEDIATION" in state.next_required_evidence
    assert state.hardware_action == ReducedEvidenceState.NOT_AUTHORIZED
