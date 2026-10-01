"""Frozen UC06-P1 convergence adjudication contract.

This evaluator encodes the already preregistered D6-E rules.  It does not create
new scientific thresholds and contains no current recovery/fine-run result values.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


D6E_CONTRACT_ID = "r2q-d6e-20260821T225252Z"
COMPLEX_S11_THRESHOLD = 0.02
RESONANCE_SHIFT_FRACTION_THRESHOLD = 0.0025
ENERGY_CLOSURE_THRESHOLD = 0.02
EXPECTED_ANCHORS = 54
EXPECTED_MEDIUM_FINE_PAIRS = 18


class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class ResonanceEvidenceState(str, Enum):
    EVALUABLE = "EVALUABLE"
    BOUNDARY_MINIMUM = "BOUNDARY_MINIMUM"
    MISSING = "MISSING"


class MediumFinePairEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: Literal["LOW_C", "HIGH_C", "SAFE_OPEN"]
    polarization: Literal["TE", "TM"]
    angle_deg: Literal[0, 30, 60]
    max_complex_s11_delta: float = Field(ge=0.0)
    resonance_evidence: ResonanceEvidenceState
    resonance_shift_fraction: float | None = Field(default=None, ge=0.0)

    @model_validator(mode="after")
    def validate_resonance(self) -> "MediumFinePairEvidence":
        if self.resonance_evidence == ResonanceEvidenceState.EVALUABLE:
            if self.resonance_shift_fraction is None:
                raise ValueError("evaluable resonance requires resonance_shift_fraction")
        elif self.resonance_shift_fraction is not None:
            raise ValueError("non-evaluable resonance must not carry a shift value")
        return self


class EnergyClosureEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anchor_id: int = Field(ge=1, le=54)
    available: bool
    closure_error_fraction: float | None = Field(default=None, ge=0.0)

    @model_validator(mode="after")
    def validate_availability(self) -> "EnergyClosureEvidence":
        if self.available and self.closure_error_fraction is None:
            raise ValueError("available energy evidence requires closure_error_fraction")
        if not self.available and self.closure_error_fraction is not None:
            raise ValueError("unavailable energy evidence must not carry a closure value")
        return self


class ExecutionCompletenessEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_anchor_count: Literal[EXPECTED_ANCHORS] = EXPECTED_ANCHORS
    exit_zero_count: int = Field(ge=0, le=54)
    parseable_output_count: int = Field(ge=0, le=54)
    retained_output_count: int = Field(ge=0, le=54)
    failures_visible: bool
    automatic_retry_count: Literal[0] = 0


class FrozenConvergenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_contract_id: Literal[D6E_CONTRACT_ID] = D6E_CONTRACT_ID
    scientific_gate_change: Literal[False] = False
    execution: ExecutionCompletenessEvidence
    medium_fine_pairs: list[MediumFinePairEvidence] = Field(
        min_length=EXPECTED_MEDIUM_FINE_PAIRS,
        max_length=EXPECTED_MEDIUM_FINE_PAIRS,
    )
    energy_closure: list[EnergyClosureEvidence] = Field(
        min_length=EXPECTED_ANCHORS,
        max_length=EXPECTED_ANCHORS,
    )

    @model_validator(mode="after")
    def validate_design_coverage(self) -> "FrozenConvergenceInput":
        pair_keys = {
            (p.state, p.polarization, p.angle_deg)
            for p in self.medium_fine_pairs
        }
        expected_keys = {
            (state, pol, angle)
            for state in ("LOW_C", "HIGH_C", "SAFE_OPEN")
            for pol in ("TE", "TM")
            for angle in (0, 30, 60)
        }
        if pair_keys != expected_keys:
            raise ValueError("medium_fine_pairs must cover the exact 3x2x3 frozen design")

        anchors = {row.anchor_id for row in self.energy_closure}
        if anchors != set(range(1, 55)):
            raise ValueError("energy_closure must cover anchors A001-A054 exactly once")
        return self


class FrozenConvergenceDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_contract_id: Literal[D6E_CONTRACT_ID] = D6E_CONTRACT_ID
    overall: GateStatus
    execution_status: GateStatus
    complex_s11_status: GateStatus
    resonance_status: GateStatus
    energy_closure_status: GateStatus
    complex_failures: list[str]
    resonance_failures: list[str]
    resonance_not_evaluable: list[str]
    energy_failures: list[str]
    energy_not_evaluable: list[str]
    rationale_codes: list[str]
    frozen_thresholds: dict[str, float]


def _pair_name(p: MediumFinePairEvidence) -> str:
    return f"{p.state}:{p.polarization}:{p.angle_deg}deg"


def adjudicate_frozen_convergence(data: FrozenConvergenceInput) -> FrozenConvergenceDecision:
    """Apply D6-E exactly; missing evidence never becomes an implicit pass."""

    execution_complete = (
        data.execution.exit_zero_count == EXPECTED_ANCHORS
        and data.execution.parseable_output_count == EXPECTED_ANCHORS
        and data.execution.retained_output_count == EXPECTED_ANCHORS
        and data.execution.failures_visible
        and data.execution.automatic_retry_count == 0
    )
    execution_status = GateStatus.PASS if execution_complete else GateStatus.NOT_EVALUABLE

    complex_failures = [
        _pair_name(p)
        for p in data.medium_fine_pairs
        if p.max_complex_s11_delta > COMPLEX_S11_THRESHOLD
    ]
    complex_status = GateStatus.FAIL if complex_failures else GateStatus.PASS

    resonance_failures: list[str] = []
    resonance_not_evaluable: list[str] = []
    for p in data.medium_fine_pairs:
        name = _pair_name(p)
        if p.resonance_evidence != ResonanceEvidenceState.EVALUABLE:
            resonance_not_evaluable.append(name)
        elif p.resonance_shift_fraction is not None and (
            p.resonance_shift_fraction > RESONANCE_SHIFT_FRACTION_THRESHOLD
        ):
            resonance_failures.append(name)

    if resonance_failures:
        resonance_status = GateStatus.FAIL
    elif resonance_not_evaluable:
        resonance_status = GateStatus.NOT_EVALUABLE
    else:
        resonance_status = GateStatus.PASS

    energy_failures = [
        f"A{row.anchor_id:03d}"
        for row in data.energy_closure
        if row.available
        and row.closure_error_fraction is not None
        and row.closure_error_fraction > ENERGY_CLOSURE_THRESHOLD
    ]
    energy_not_evaluable = [
        f"A{row.anchor_id:03d}"
        for row in data.energy_closure
        if not row.available
    ]

    if energy_failures:
        energy_status = GateStatus.FAIL
    elif energy_not_evaluable:
        energy_status = GateStatus.NOT_EVALUABLE
    else:
        energy_status = GateStatus.PASS

    component_statuses = [
        execution_status,
        complex_status,
        resonance_status,
        energy_status,
    ]
    if GateStatus.FAIL in component_statuses:
        overall = GateStatus.FAIL
    elif GateStatus.NOT_EVALUABLE in component_statuses:
        overall = GateStatus.NOT_EVALUABLE
    else:
        overall = GateStatus.PASS

    rationale = [
        "FROZEN_D6E_THRESHOLDS_APPLIED",
        "NO_THRESHOLD_RELAXATION",
        "NO_POST_HOC_RETRY",
    ]
    if overall == GateStatus.NOT_EVALUABLE:
        rationale.append("MISSING_OR_BOUNDARY_EVIDENCE_PREVENTS_CLOSURE")
    if overall == GateStatus.FAIL:
        rationale.append("ONE_OR_MORE_FROZEN_GATES_EXCEEDED")
    if overall == GateStatus.PASS:
        rationale.append("ALL_FROZEN_GATES_SATISFIED_ON_COMPLETE_EVIDENCE")

    return FrozenConvergenceDecision(
        overall=overall,
        execution_status=execution_status,
        complex_s11_status=complex_status,
        resonance_status=resonance_status,
        energy_closure_status=energy_status,
        complex_failures=complex_failures,
        resonance_failures=resonance_failures,
        resonance_not_evaluable=resonance_not_evaluable,
        energy_failures=energy_failures,
        energy_not_evaluable=energy_not_evaluable,
        rationale_codes=rationale,
        frozen_thresholds={
            "complex_s11_max_delta": COMPLEX_S11_THRESHOLD,
            "resonance_shift_fraction": RESONANCE_SHIFT_FRACTION_THRESHOLD,
            "energy_closure_fraction": ENERGY_CLOSURE_THRESHOLD,
        },
    )
