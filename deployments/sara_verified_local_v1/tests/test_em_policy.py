from worldshepherd_sara.em_intelligence import (
    EMCandidate,
    EMEvidenceClass,
    EMIntent,
    EMOperatingMode,
)
from worldshepherd_sara.em_policy import (
    EMAuthorizationContext,
    evaluate_em_hardware_authorization,
)


def _intent() -> EMIntent:
    return EMIntent(
        intent_id="INTENT-EM-1",
        objective="test future validated EM actuation",
        operating_mode=EMOperatingMode.SAFE_DEGRADED,
    )


def _candidate(*, action_flag: bool = False) -> EMCandidate:
    return EMCandidate(
        candidate_id="CAND-EM-1",
        source_model="UC06-P1",
        source_version="future-validated",
        evidence_class=EMEvidenceClass.PROVEN_INTERNALLY,
        convergence_status="PASS",
        model_discrepancy_status="CLOSED",
        hardware_action_authorized=action_flag,
    )


def test_current_style_context_fails_closed():
    decision = evaluate_em_hardware_authorization(
        _intent(),
        _candidate(),
        EMAuthorizationContext(decision_id="DEC-1"),
    )
    assert decision.authorized is False
    assert decision.safe_fallback == "SAFE_OPEN"
    assert "MEDIUM_FINE_CONVERGENCE" in decision.unresolved_gates
    assert "PHYSICAL_VALIDATION" in decision.unresolved_gates
    assert "PRIME_RELEASE" in decision.unresolved_gates
    assert "FAIL_CLOSED" in decision.rationale_codes


def test_even_good_simulation_cannot_bypass_physical_validation():
    decision = evaluate_em_hardware_authorization(
        _intent(),
        _candidate(action_flag=True),
        EMAuthorizationContext(
            decision_id="DEC-2",
            validated_envelope_id="ENV-1",
            medium_fine_convergence_passed=True,
            energy_closure_passed=True,
            physical_validation_complete=False,
            repeatability_validated=True,
            prime_release_authorized=True,
        ),
    )
    assert decision.authorized is False
    assert decision.unresolved_gates == ["PHYSICAL_VALIDATION"]


def test_authorization_requires_every_explicit_gate():
    decision = evaluate_em_hardware_authorization(
        _intent(),
        _candidate(action_flag=True),
        EMAuthorizationContext(
            decision_id="DEC-3",
            validated_envelope_id="ENV-VALIDATED-1",
            medium_fine_convergence_passed=True,
            energy_closure_passed=True,
            physical_validation_complete=True,
            repeatability_validated=True,
            prime_release_authorized=True,
        ),
    )
    assert decision.authorized is True
    assert decision.unresolved_gates == []
    assert decision.rationale_codes == ["AUTHORIZED_ALL_EXPLICIT_GATES_SATISFIED"]
