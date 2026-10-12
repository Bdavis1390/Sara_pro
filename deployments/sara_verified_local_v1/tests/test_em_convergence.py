from worldshepherd_sara.em_convergence import (
    EnergyClosureEvidence,
    ExecutionCompletenessEvidence,
    FrozenConvergenceInput,
    GateStatus,
    MediumFinePairEvidence,
    ResonanceEvidenceState,
    adjudicate_frozen_convergence,
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


def _energy(*, available: bool = True, error: float | None = 0.02):
    if not available:
        error = None
    return [
        EnergyClosureEvidence(
            anchor_id=anchor,
            available=available,
            closure_error_fraction=error,
        )
        for anchor in range(1, 55)
    ]


def _execution(
    *,
    completed: int = 54,
    zero: int = 54,
    nonzero: int = 0,
    parseable: int = 54,
    retained: int = 54,
    failures_visible: bool = True,
) -> ExecutionCompletenessEvidence:
    return ExecutionCompletenessEvidence(
        completed_anchor_count=completed,
        exit_zero_count=zero,
        nonzero_exit_count=nonzero,
        parseable_output_count=parseable,
        retained_output_count=retained,
        failures_visible=failures_visible,
    )


def _input(**overrides) -> FrozenConvergenceInput:
    data = dict(
        execution=_execution(),
        medium_fine_pairs=_pairs(),
        energy_closure=_energy(),
    )
    data.update(overrides)
    return FrozenConvergenceInput(**data)


def test_exact_frozen_thresholds_are_inclusive_pass() -> None:
    decision = adjudicate_frozen_convergence(_input())
    assert decision.overall == GateStatus.PASS
    assert decision.execution_status == GateStatus.PASS
    assert decision.complex_s11_status == GateStatus.PASS
    assert decision.resonance_status == GateStatus.PASS
    assert decision.energy_closure_status == GateStatus.PASS
    assert decision.frozen_thresholds == {
        "complex_s11_max_delta": 0.02,
        "resonance_shift_fraction": 0.0025,
        "energy_closure_fraction": 0.02,
    }


def test_boundary_resonance_prevents_convergence_closure() -> None:
    decision = adjudicate_frozen_convergence(
        _input(
            medium_fine_pairs=_pairs(
                resonance_state=ResonanceEvidenceState.BOUNDARY_MINIMUM,
            )
        )
    )
    assert decision.resonance_status == GateStatus.NOT_EVALUABLE
    assert decision.overall == GateStatus.NOT_EVALUABLE
    assert len(decision.resonance_not_evaluable) == 18


def test_complex_delta_above_frozen_threshold_fails() -> None:
    pairs = _pairs()
    pairs[0] = pairs[0].model_copy(update={"max_complex_s11_delta": 0.0200001})
    decision = adjudicate_frozen_convergence(_input(medium_fine_pairs=pairs))
    assert decision.complex_s11_status == GateStatus.FAIL
    assert decision.overall == GateStatus.FAIL
    assert len(decision.complex_failures) == 1


def test_energy_above_frozen_threshold_fails() -> None:
    energy = _energy()
    energy[0] = energy[0].model_copy(update={"closure_error_fraction": 0.0200001})
    decision = adjudicate_frozen_convergence(_input(energy_closure=energy))
    assert decision.energy_closure_status == GateStatus.FAIL
    assert decision.overall == GateStatus.FAIL
    assert decision.energy_failures == ["A001"]


def test_unavailable_energy_is_not_evaluable_not_pass() -> None:
    energy = _energy()
    energy[0] = EnergyClosureEvidence(anchor_id=1, available=False)
    decision = adjudicate_frozen_convergence(_input(energy_closure=energy))
    assert decision.energy_closure_status == GateStatus.NOT_EVALUABLE
    assert decision.overall == GateStatus.NOT_EVALUABLE
    assert decision.energy_not_evaluable == ["A001"]


def test_incomplete_execution_is_not_evaluable() -> None:
    decision = adjudicate_frozen_convergence(
        _input(
            execution=_execution(
                completed=53,
                zero=53,
                nonzero=0,
                parseable=53,
                retained=53,
            )
        )
    )
    assert decision.execution_status == GateStatus.NOT_EVALUABLE
    assert decision.overall == GateStatus.NOT_EVALUABLE


def test_completed_nonzero_exit_is_failure() -> None:
    decision = adjudicate_frozen_convergence(
        _input(
            execution=_execution(
                completed=54,
                zero=53,
                nonzero=1,
                parseable=53,
                retained=54,
            )
        )
    )
    assert decision.execution_status == GateStatus.FAIL
    assert decision.overall == GateStatus.FAIL


def test_thresholds_are_frozen_and_no_gate_change_is_allowed() -> None:
    data = _input()
    assert data.scientific_gate_change is False
    decision = adjudicate_frozen_convergence(data)
    assert "FROZEN_D6E_THRESHOLDS_APPLIED" in decision.rationale_codes
    assert "NO_THRESHOLD_RELAXATION" in decision.rationale_codes
