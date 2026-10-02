"""Evidence-driven UC06-P1 maturity reduction.

Repository defaults remain conservative. This reducer advances only the evidence
states supported by cryptographically verified typed receipts. It does not persist
state, mutate the read-only service, or authorize scientific/hardware promotion.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .em_convergence import GateStatus, adjudicate_frozen_convergence
from .em_recovery import RecoveryStatus, evaluate_recovery_receipt
from .em_sealed_receipts import (
    VerifiedConvergenceEvidence,
    VerifiedD5Evidence,
    VerifiedRecoveryEvidence,
)


MATURITY_REDUCER_VERSION = "worldshepherd.uc06-p1.maturity-reducer.v0.2"


class ReducedEvidenceState(str, Enum):
    ESTABLISHED_DIAGNOSTIC = "ESTABLISHED_DIAGNOSTIC"
    INGESTED_DIAGNOSTIC = "INGESTED_DIAGNOSTIC"
    PENDING = "PENDING"
    NOT_INGESTED = "NOT_INGESTED"
    INCOMPLETE = "INCOMPLETE"
    EXECUTION_COMPLETE = "EXECUTION_COMPLETE"
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    NOT_ADJUDICATED = "NOT_ADJUDICATED"
    NOT_VALIDATED = "NOT_VALIDATED"
    NOT_AUTHORIZED = "NOT_AUTHORIZED"


class ReducedUC06MaturityState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reducer_version: Literal[MATURITY_REDUCER_VERSION] = MATURITY_REDUCER_VERSION
    evidence_scope: Literal["UC06-P1"] = "UC06-P1"
    d4_capability_attribution: ReducedEvidenceState
    d5_interaction_sparse_analysis: ReducedEvidenceState
    recovery_a027_a054_completion: ReducedEvidenceState
    frozen_convergence_overall: ReducedEvidenceState
    medium_fine_convergence: ReducedEvidenceState
    energy_closure: ReducedEvidenceState
    physical_validation: ReducedEvidenceState
    repeatability_validation: ReducedEvidenceState
    validated_operating_envelope: ReducedEvidenceState
    h2_promotion: ReducedEvidenceState
    full_campaign: ReducedEvidenceState
    hardware_action: ReducedEvidenceState
    software_ci_is_physics_validation: Literal[False] = False
    evidence_driven: Literal[True] = True
    persisted_state_mutation: Literal[False] = False
    next_required_evidence: list[str]
    claims_boundary: list[str]


def _gate_to_state(status: GateStatus) -> ReducedEvidenceState:
    return {
        GateStatus.PASS: ReducedEvidenceState.PASS,
        GateStatus.FAIL: ReducedEvidenceState.FAIL,
        GateStatus.NOT_EVALUABLE: ReducedEvidenceState.NOT_EVALUABLE,
    }[status]


def _combine_pair_gates(a: GateStatus, b: GateStatus) -> ReducedEvidenceState:
    if GateStatus.FAIL in (a, b):
        return ReducedEvidenceState.FAIL
    if GateStatus.NOT_EVALUABLE in (a, b):
        return ReducedEvidenceState.NOT_EVALUABLE
    return ReducedEvidenceState.PASS


def reduce_uc06_maturity(
    *,
    d5: VerifiedD5Evidence | None = None,
    recovery: VerifiedRecoveryEvidence | None = None,
    convergence: VerifiedConvergenceEvidence | None = None,
) -> ReducedUC06MaturityState:
    """Reduce verified evidence into conservative maturity states.

    Every reducible package must already be bound to the bytes of its sealed source
    receipt. The frozen convergence decision is recomputed here from raw typed evidence;
    no caller-supplied PASS/FAIL value is accepted.
    """

    d5_state = (
        ReducedEvidenceState.INGESTED_DIAGNOSTIC
        if d5 is not None
        else ReducedEvidenceState.PENDING
    )

    if recovery is None:
        recovery_state = ReducedEvidenceState.NOT_INGESTED
        recovery_decision = None
    else:
        recovery_decision = evaluate_recovery_receipt(recovery.package)
        recovery_state = {
            RecoveryStatus.INCOMPLETE: ReducedEvidenceState.INCOMPLETE,
            RecoveryStatus.FAIL: ReducedEvidenceState.FAIL,
            RecoveryStatus.EXECUTION_COMPLETE: ReducedEvidenceState.EXECUTION_COMPLETE,
            RecoveryStatus.NOT_INGESTED: ReducedEvidenceState.NOT_INGESTED,
        }[recovery_decision.status]

    if convergence is None:
        convergence_decision = None
        overall_convergence_state = ReducedEvidenceState.NOT_ADJUDICATED
        medium_fine_state = ReducedEvidenceState.NOT_ADJUDICATED
        energy_state = ReducedEvidenceState.PENDING
    else:
        convergence_decision = adjudicate_frozen_convergence(convergence.package.evidence)
        overall_convergence_state = _gate_to_state(convergence_decision.overall)
        medium_fine_state = _combine_pair_gates(
            convergence_decision.complex_s11_status,
            convergence_decision.resonance_status,
        )
        energy_state = _gate_to_state(convergence_decision.energy_closure_status)

    next_required: list[str] = []
    if d5 is None:
        next_required.append("SEALED_D5_RESULT_RECEIPT")
    if recovery_state != ReducedEvidenceState.EXECUTION_COMPLETE:
        next_required.append("SEALED_A027_A054_RECOVERY_COMPLETION_RECEIPT")

    if convergence_decision is None:
        next_required.extend(
            [
                "FROZEN_MEDIUM_FINE_CONVERGENCE_ADJUDICATION",
                "FROZEN_ENERGY_CLOSURE_ADJUDICATION",
            ]
        )
    else:
        if overall_convergence_state == ReducedEvidenceState.FAIL:
            next_required.append("FROZEN_CONVERGENCE_FAILURE_REMEDIATION")
        elif overall_convergence_state == ReducedEvidenceState.NOT_EVALUABLE:
            next_required.append("FROZEN_CONVERGENCE_MISSING_OR_BOUNDARY_EVIDENCE")
        if energy_state == ReducedEvidenceState.FAIL:
            next_required.append("ENERGY_CLOSURE_FAILURE_REMEDIATION")
        elif energy_state == ReducedEvidenceState.NOT_EVALUABLE:
            next_required.append("ENERGY_CLOSURE_MISSING_EVIDENCE")

    next_required.extend(
        [
            "PHYSICAL_VNA_COUPON_VALIDATION",
            "REPEATABILITY_AND_UNCERTAINTY_VALIDATION",
            "VALIDATED_OPERATING_ENVELOPE",
            "EXPLICIT_PRIME_RELEASE_BEFORE_ANY_HARDWARE_ACTION",
        ]
    )

    claims = [
        "D4_IS_DIAGNOSTIC_NOT_PHYSICAL_VALIDATION",
        "VERIFIED_RECEIPT_HASH_REQUIRED_BEFORE_EVIDENCE_REDUCTION",
        "D5_INGESTION_DOES_NOT_CHANGE_SCIENTIFIC_GATES",
        "RECOVERY_EXECUTION_COMPLETE_DOES_NOT_EQUAL_CONVERGENCE",
        "FROZEN_CONVERGENCE_DECISION_RECOMPUTED_NOT_CALLER_SUPPLIED",
        "SOFTWARE_CI_IS_NOT_PHYSICS_VALIDATION",
        "NO_H2_PROMOTION",
        "NO_FULL_CAMPAIGN_AUTHORIZATION",
        "NO_HARDWARE_ACTION",
    ]
    if recovery_decision is not None and recovery_decision.status == RecoveryStatus.FAIL:
        claims.append("RECOVERY_FAILURE_RETAINED_VISIBLE")
    if recovery_decision is not None and recovery_decision.status == RecoveryStatus.INCOMPLETE:
        claims.append("RECOVERY_INCOMPLETE_NOT_MISLABELED_AS_FAILURE")
    if convergence_decision is not None and convergence_decision.overall == GateStatus.FAIL:
        claims.append("FROZEN_CONVERGENCE_FAILURE_RETAINED_VISIBLE")
    if convergence_decision is not None and convergence_decision.overall == GateStatus.NOT_EVALUABLE:
        claims.append("FROZEN_CONVERGENCE_NOT_EVALUABLE_RETAINED_VISIBLE")

    return ReducedUC06MaturityState(
        d4_capability_attribution=ReducedEvidenceState.ESTABLISHED_DIAGNOSTIC,
        d5_interaction_sparse_analysis=d5_state,
        recovery_a027_a054_completion=recovery_state,
        frozen_convergence_overall=overall_convergence_state,
        medium_fine_convergence=medium_fine_state,
        energy_closure=energy_state,
        physical_validation=ReducedEvidenceState.NOT_VALIDATED,
        repeatability_validation=ReducedEvidenceState.NOT_VALIDATED,
        validated_operating_envelope=ReducedEvidenceState.NOT_VALIDATED,
        h2_promotion=ReducedEvidenceState.NOT_AUTHORIZED,
        full_campaign=ReducedEvidenceState.NOT_AUTHORIZED,
        hardware_action=ReducedEvidenceState.NOT_AUTHORIZED,
        next_required_evidence=next_required,
        claims_boundary=claims,
    )
