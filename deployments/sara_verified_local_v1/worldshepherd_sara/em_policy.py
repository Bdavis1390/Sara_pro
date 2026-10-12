"""Fail-closed PRIME policy kernel for future electromagnetic hardware actions.

No current UC06-P1 diagnostic evidence satisfies these gates.  The function exists
so future integrations cannot accidentally treat simulation or CI success as
physical authorization.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .em_intelligence import EMCandidate, EMIntent, EMPolicyDecision


class EMAuthorizationContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1, max_length=128)
    validated_envelope_id: str | None = Field(default=None, max_length=128)
    medium_fine_convergence_passed: bool = False
    energy_closure_passed: bool = False
    physical_validation_complete: bool = False
    repeatability_validated: bool = False
    prime_release_authorized: bool = False
    unresolved_gates: list[str] = Field(default_factory=list, max_length=64)


def evaluate_em_hardware_authorization(
    intent: EMIntent,
    candidate: EMCandidate,
    context: EMAuthorizationContext,
) -> EMPolicyDecision:
    """Evaluate future EM actuation authorization using explicit conjunctive gates."""

    unresolved = list(dict.fromkeys(context.unresolved_gates))
    rationale: list[str] = []

    required = {
        "MEDIUM_FINE_CONVERGENCE": context.medium_fine_convergence_passed,
        "ENERGY_CLOSURE": context.energy_closure_passed,
        "PHYSICAL_VALIDATION": context.physical_validation_complete,
        "REPEATABILITY": context.repeatability_validated,
        "VALIDATED_ENVELOPE": bool(context.validated_envelope_id),
        "PRIME_RELEASE": context.prime_release_authorized,
        "CANDIDATE_ACTION_FLAG": candidate.hardware_action_authorized,
    }

    for gate, passed in required.items():
        if not passed:
            unresolved.append(gate)
            rationale.append(f"DENY_{gate}")

    authorized = not unresolved
    if authorized:
        rationale.append("AUTHORIZED_ALL_EXPLICIT_GATES_SATISFIED")
    else:
        rationale.append("FAIL_CLOSED")

    return EMPolicyDecision(
        decision_id=context.decision_id,
        intent_id=intent.intent_id,
        candidate_id=candidate.candidate_id,
        authorized=authorized,
        validated_envelope_id=context.validated_envelope_id,
        safe_fallback="SAFE_OPEN",
        unresolved_gates=sorted(set(unresolved)),
        rationale_codes=rationale,
    )
