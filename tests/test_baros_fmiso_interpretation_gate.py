"""Synthetic FMISO interpretation metadata gates: no patient images or true readers."""

from dataclasses import replace
from hashlib import sha256

import pytest

from baros.closed_loop import AdaptationThresholds, BiologicalState
from baros.fmiso_interpretation_gate import (
    DeclaredFMISOObservation,
    DeclaredReader,
    assess_declared_fmiso_pair,
    mock_fmiso_research_handoff,
)
from baros.research_objective_intent import ResearchPriorityPolicy


def digest(value):
    return sha256(value.encode()).hexdigest()


def reader(which, vote="positive", trained=True):
    return DeclaredReader(
        reader_token="SYN-READER-" + which,
        trained_for_locked_protocol=trained,
        interpretation=vote,
    )


def observation(phase, **changes):
    kwargs = {
        "phase_index": phase,
        "study_token": "SYN-MOCK-HNSCC-001",
        "tracer": "18F-FMISO",
        "image_sha256": digest("mock-image-" + str(phase)),
        "acquisition_protocol_sha256": digest("locked-fmiso-acquisition"),
        "quantification_protocol_sha256": digest("locked-fmiso-quantification"),
        "reference_frame_sha256": digest("locked-fmiso-common-frame"),
        "registration_independently_reviewed": True,
        "readers": (reader("A"), reader("B")),
    }
    kwargs.update(changes)
    return DeclaredFMISOObservation(**kwargs)


def state(phase, *, hypoxia=(0.2, 0.3)):
    return BiologicalState(
        phase_index=phase,
        alpha_per_gy=(0.30, 0.31),
        beta_per_gy2=(0.03, 0.03),
        hypoxia_index=hypoxia,
        resistance_index=(0.10, 0.15),
        uncertainty=(0.05, 0.05),
        measurement_quality=0.95,
        geometry_qualified=True,
        model_identifiable=True,
        out_of_distribution=False,
    )


LIMITS = AdaptationThresholds(
    hypoxia_change=0.1,
    resistance_change=0.1,
    uncertainty_change=0.1,
    anatomy_change_mm=3.,
    motion_mm=4.,
    max_uncertainty=0.2,
    min_measurement_quality=0.8,
)


def handoff(prior=None, current=None, **overrides):
    params = dict(
        previous=state(0),
        current=state(1, hypoxia=(0.2, 0.5)),
        previous_fmiso=observation(0),
        current_fmiso=observation(1),
        thresholds=LIMITS,
        policy=ResearchPriorityPolicy(0.5, 0.1),
        region_ids=("SYN-A", "SYN-B"),
    )
    params.update(overrides)
    return mock_fmiso_research_handoff(**params)


def test_consistent_declared_synthetic_evidence_allows_abstract_priority_only():
    result = handoff()
    assert result.assay.eligible
    assert not result.assay.independently_validated
    assert result.assay.blockers == ()
    assert len(result.assay.declared_metadata_sha256) == 64
    assert result.intent.proposal_allowed
    assert result.intent.tps_export_allowed is False
    assert result.intent.dose_or_prescription_defined is False
    assert result.intent.treatment_authority is False
    assert [v.abstract_priority_delta for v in result.intent.region_priorities] == pytest.approx((0., 0.1))


@pytest.mark.parametrize("prior,now,blocker", [
    (observation(0, registration_independently_reviewed=False), observation(1), "previous_registration_not_reviewed"),
    (observation(0), observation(1, registration_independently_reviewed=False), "current_registration_not_reviewed"),
    (observation(0), observation(1, readers=(reader("A", "negative"), reader("B", "positive"))), "current_reader_disagreement"),
    (observation(0, readers=(reader("A", "indeterminate"), reader("B", "positive"))), observation(1), "previous_interpretation_indeterminate"),
    (observation(0), observation(1, readers=(reader("A", trained=False), reader("B"))), "current_reader_training_unconfirmed"),
    (observation(0), observation(1, quantification_protocol_sha256=digest("changed")), "quantification_protocol_sha256_mismatch"),
    (observation(0), observation(1, acquisition_protocol_sha256=digest("changed")), "acquisition_protocol_sha256_mismatch"),
    (observation(0), observation(1, reference_frame_sha256=digest("other")), "reference_frame_sha256_mismatch"),
    (observation(0), observation(1, image_sha256=digest("mock-image-0")), "duplicate_image_digest"),
    (observation(0), observation(1, study_token="SYN-OTHER-STUDY"), "different_research_study"),
])
def test_assay_evidence_gap_blocks_all_mock_reoptimization(prior, now, blocker):
    result = handoff(previous_fmiso=prior, current_fmiso=now)
    assert not result.assay.eligible
    assert blocker in result.assay.blockers
    assert result.intent.decision_action == "HOLD_LAST_VALID"
    assert not result.intent.proposal_allowed
    assert result.intent.region_priorities == ()
    assert not result.intent.tps_export_allowed
    assert not result.intent.treatment_authority


def test_agreed_negative_calls_are_not_invented_as_positive_hypoxia():
    result = handoff(
        previous_fmiso=observation(0, readers=(reader("A", "negative"), reader("B", "negative"))),
        current_fmiso=observation(1, readers=(reader("A", "negative"), reader("B", "negative"))),
    )
    # Consistent metadata is NOT proof that a caller-supplied biological state
    # is scientifically correct; real biological-calibration validation is open.
    assert result.assay.eligible
    assert result.assay.independently_validated is False
    # Reader agreement on an FMISO-negative current scan is a valid negative
    # interpretation, but must not translate a conflicting synthetic
    # quantitative increase into any adaptation proposal or priority.
    assert result.intent.decision_action == "HOLD_LAST_VALID"
    assert not result.intent.proposal_allowed
    assert result.intent.region_priorities == ()
    assert "negative" in result.intent.next_step
    assert not result.intent.tps_export_allowed


def test_prior_negative_to_current_positive_still_allows_synthetic_policy_when_qualified():
    result = handoff(
        previous_fmiso=observation(0, readers=(reader("A", "negative"), reader("B", "negative"))),
        current_fmiso=observation(1),
    )
    assert result.assay.eligible
    assert result.intent.proposal_allowed
    assert not result.intent.treatment_authority


def test_current_negative_with_decreasing_hypoxia_still_cannot_authorize_adaptation():
    result = handoff(
        current=state(1, hypoxia=(0.2, 0.1)),
        current_fmiso=observation(1, readers=(reader("A", "negative"), reader("B", "negative"))),
    )
    assert result.assay.eligible
    assert result.intent.decision_action == "HOLD_LAST_VALID"
    assert not result.intent.proposal_allowed
    assert result.intent.region_priorities == ()


def test_negative_no_change_keeps_no_adaptation():
    result = handoff(
        current=state(1),
        current_fmiso=observation(1, readers=(reader("A", "negative"), reader("B", "negative"))),
    )
    assert result.assay.eligible
    assert result.intent.decision_action == "NO_ADAPTATION"
    assert not result.intent.proposal_allowed


def test_anatomical_trigger_without_biologic_priority_is_not_fmiso_replan():
    from dataclasses import replace
    current = replace(state(1), anatomy_delta_mm=4.0)
    result = handoff(current=current)
    assert result.assay.eligible
    assert result.intent.decision_action == "HOLD_LAST_VALID"
    assert not result.intent.proposal_allowed
    assert result.intent.region_priorities == ()
    assert "no positive" in result.intent.next_step


def test_biologic_decrease_without_positive_priority_does_not_propose():
    result = handoff(current=state(1, hypoxia=(0.2, 0.1)))
    assert result.assay.eligible
    assert result.intent.decision_action == "HOLD_LAST_VALID"
    assert not result.intent.proposal_allowed
    assert result.intent.region_priorities == ()


def test_zero_priority_cap_cannot_create_actionable_research_proposal():
    result = handoff(policy=ResearchPriorityPolicy(0.5, 0.0))
    assert result.assay.eligible
    assert not result.intent.proposal_allowed
    assert result.intent.region_priorities == ()
    assert not result.intent.tps_export_allowed


@pytest.mark.parametrize("wrong", ["18F-FDG", "FDG", "fmiso", "", None])
def test_fmiso_is_not_replaced_by_another_biomarker(wrong):
    with pytest.raises(ValueError, match="tracer"):
        assess_declared_fmiso_pair(observation(0), observation(1, tracer=wrong))


@pytest.mark.parametrize("bad", [
    (reader("A"), reader("A")),
    (reader("A", trained="yes"), reader("B")),
    (reader("A", vote="maybe"), reader("B")),
])
def test_reject_identical_or_ambiguous_reader_declarations(bad):
    with pytest.raises(ValueError):
        assess_declared_fmiso_pair(observation(0), observation(1, readers=bad))


def test_mismatched_phase_or_reused_state_index_never_proposes():
    with pytest.raises(ValueError, match="phases do not match"):
        handoff(current_fmiso=observation(2))
    with pytest.raises(ValueError, match="FMISO phases must advance"):
        assess_declared_fmiso_pair(observation(1), observation(1, image_sha256=digest("another")))


def test_source_changes_change_declared_digest_not_external_authentication():
    a = assess_declared_fmiso_pair(observation(0), observation(1))
    b = assess_declared_fmiso_pair(observation(0), observation(1, image_sha256=digest("new-image")))
    assert a.declared_metadata_sha256 != b.declared_metadata_sha256
    assert not a.independently_validated
    assert a == assess_declared_fmiso_pair(observation(0), observation(1))
