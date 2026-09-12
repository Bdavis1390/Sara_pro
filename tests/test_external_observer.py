import pytest

from worldshepherd_sara.external_observer import ExternalObserverAdapter, ExternalObserverRecord
from worldshepherd_sara.fusion_consensus import StateConsensusGate, StateConsensusPolicy
from worldshepherd_sara.fusion_control import PlasmaStateEstimate


def record(**overrides):
    values = dict(
        timestamp=1.0,
        shot_id="observer-shot",
        vertical_displacement_m=0.011,
        confidence=0.92,
        estimator_id="partner-equilibrium-observer-v1",
        method="external_equilibrium_reconstruction",
        source_diagnostics=("magnetic_flux_loop_set",),
        provenance="partner-record:observer-shot:1.0",
        quality="source-validated",
        validated_by_source=True,
    )
    values.update(overrides)
    return ExternalObserverRecord(**values)


def test_valid_external_record_adapts_to_common_state_contract():
    estimate = ExternalObserverAdapter().adapt(record())
    assert isinstance(estimate, PlasmaStateEstimate)
    assert estimate.estimator_id == "partner-equilibrium-observer-v1"
    assert estimate.vertical_displacement_m == 0.011


def test_unvalidated_external_record_fails_closed():
    with pytest.raises(ValueError, match="external_estimate_not_source_validated"):
        ExternalObserverAdapter().adapt(record(validated_by_source=False))


def test_missing_provenance_fails_closed():
    with pytest.raises(ValueError, match="provenance_missing"):
        ExternalObserverAdapter().adapt(record(provenance=""))


def test_low_confidence_external_record_is_rejected():
    with pytest.raises(ValueError, match="confidence_below_policy"):
        ExternalObserverAdapter(minimum_confidence=0.85).adapt(record(confidence=0.84))


def test_external_observer_can_participate_in_consensus_without_being_implemented_here():
    external = ExternalObserverAdapter().adapt(record())
    local_demo = PlasmaStateEstimate(
        timestamp=1.001,
        shot_id="observer-shot",
        vertical_displacement_m=0.010,
        confidence=0.95,
        estimator_id="optical-demo-estimator",
        source_diagnostics=("upper_demo", "lower_demo"),
    )
    gate = StateConsensusGate(
        StateConsensusPolicy(
            minimum_estimators=2,
            minimum_confidence=0.80,
            maximum_time_skew_s=0.01,
            maximum_abs_disagreement_m=0.005,
        )
    )
    decision = gate.evaluate([local_demo, external])
    assert decision.accepted is True
    assert set(decision.estimator_ids) == {"optical-demo-estimator", "partner-equilibrium-observer-v1"}
