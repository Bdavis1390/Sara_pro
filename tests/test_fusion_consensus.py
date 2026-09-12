from worldshepherd_sara.fusion_consensus import StateConsensusGate, StateConsensusPolicy
from worldshepherd_sara.fusion_control import PlasmaStateEstimate


def estimate(estimator_id: str, displacement: float, *, confidence: float = 0.95, timestamp: float = 1.0, shot_id: str = "consensus-shot") -> PlasmaStateEstimate:
    return PlasmaStateEstimate(
        timestamp=timestamp,
        shot_id=shot_id,
        vertical_displacement_m=displacement,
        confidence=confidence,
        estimator_id=estimator_id,
        source_diagnostics=(f"source:{estimator_id}",),
    )


def gate() -> StateConsensusGate:
    return StateConsensusGate(
        StateConsensusPolicy(
            minimum_estimators=2,
            minimum_confidence=0.80,
            maximum_time_skew_s=0.01,
            maximum_abs_disagreement_m=0.005,
        )
    )


def test_distinct_close_estimates_are_accepted():
    result = gate().evaluate([
        estimate("optical-demo", 0.010),
        estimate("independent-observer", 0.012, confidence=0.90, timestamp=1.001),
    ])
    assert result.accepted is True
    assert result.reason == "consensus_accepted"
    assert result.vertical_displacement_m is not None
    assert 0.010 <= result.vertical_displacement_m <= 0.012
    assert result.confidence == 0.90


def test_duplicate_estimator_identity_is_not_treated_as_independent():
    result = gate().evaluate([
        estimate("same-estimator", 0.010),
        estimate("same-estimator", 0.011),
    ])
    assert result.accepted is False
    assert result.reason == "estimators_not_independent_by_identity"


def test_cross_shot_estimates_are_rejected():
    result = gate().evaluate([
        estimate("one", 0.010, shot_id="shot-a"),
        estimate("two", 0.011, shot_id="shot-b"),
    ])
    assert result.accepted is False
    assert result.reason == "shot_id_mismatch"


def test_low_confidence_estimate_blocks_consensus():
    result = gate().evaluate([
        estimate("one", 0.010),
        estimate("two", 0.011, confidence=0.79),
    ])
    assert result.accepted is False
    assert result.reason == "estimator_confidence_below_policy"


def test_excessive_estimator_disagreement_blocks_consensus():
    result = gate().evaluate([
        estimate("one", 0.010),
        estimate("two", 0.020),
    ])
    assert result.accepted is False
    assert result.reason == "estimator_disagreement_exceeded"
    assert result.disagreement_span_m == 0.01


def test_excessive_time_skew_blocks_consensus():
    result = gate().evaluate([
        estimate("one", 0.010, timestamp=1.0),
        estimate("two", 0.011, timestamp=1.02),
    ])
    assert result.accepted is False
    assert result.reason == "estimator_time_skew_exceeded"
