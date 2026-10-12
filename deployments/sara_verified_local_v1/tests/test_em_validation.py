from worldshepherd_sara.em_intelligence import (
    EMCandidate,
    EMEvidenceClass,
    EMIntent,
    EMOperatingMode,
)
from worldshepherd_sara.em_validation import (
    EMValidationStage,
    assess_candidate_for_palace,
)


def _intent() -> EMIntent:
    return EMIntent(
        intent_id="I-1",
        objective="Explore next-generation TE/TM cell",
        operating_mode=EMOperatingMode.DESIGN_EXPLORATION,
        polarization="BOTH",
    )


def _candidate(**overrides) -> EMCandidate:
    values = {
        "candidate_id": "C-1",
        "source_model": "uc06-latent-surrogate",
        "source_version": "v0.1",
        "evidence_class": EMEvidenceClass.HYPOTHESIS,
        "convergence_status": "PENDING_FULL_WAVE_VALIDATION",
        "model_discrepancy_status": "BOUNDED_FOR_EXPLORATION",
        "evidence_refs": ["github:research/uc06_p1/D4_SUMMARY.md"],
        "hardware_action_authorized": False,
    }
    values.update(overrides)
    return EMCandidate(**values)


def test_candidate_can_enter_palace_validation_without_hardware_authorization():
    result = assess_candidate_for_palace(_intent(), _candidate())

    assert result.stage == EMValidationStage.PALACE_VALIDATION_CANDIDATE
    assert result.may_enter_palace_validation is True
    assert result.hardware_action_authorized is False
    assert "UC06_OVERALL_CONVERGENCE_NOT_ADJUDICATED" in result.advisories
    assert result.candidate_digest.startswith("sha256:")
    assert result.evidence_digest.startswith("sha256:")


def test_candidate_with_hardware_action_flag_is_rejected_at_simulation_stage():
    result = assess_candidate_for_palace(
        _intent(),
        _candidate(hardware_action_authorized=True),
    )

    assert result.stage == EMValidationStage.REJECTED
    assert result.may_enter_palace_validation is False
    assert result.hardware_action_authorized is False
    assert "HARDWARE_ACTION_FLAG_MUST_BE_FALSE_AT_SIMULATION_STAGE" in result.blockers


def test_candidate_without_evidence_refs_is_rejected():
    result = assess_candidate_for_palace(
        _intent(),
        _candidate(evidence_refs=[]),
    )

    assert result.stage == EMValidationStage.REJECTED
    assert "CANDIDATE_EVIDENCE_REFS_REQUIRED" in result.blockers
