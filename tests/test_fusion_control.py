from worldshepherd_sara.fusion_control import (
    ControlProposal,
    DifferentialOpticalEstimator,
    FusionAuditLedger,
    PrimeSafetyGate,
    SafetyEnvelope,
    SensorSample,
    run_simulated_control_cycle,
)


def sample(name: str, value: float, uncertainty: float = 1.0, valid: bool = True):
    return SensorSample(
        timestamp=1000.0,
        shot_id="test-shot",
        diagnostic=name,
        value=value,
        unit="arb",
        uncertainty=uncertainty,
        valid=valid,
        quality="test",
        provenance=f"test:{name}",
    )


def gate(minimum_confidence: float = 0.80):
    return PrimeSafetyGate([
        SafetyEnvelope(
            actuator="virtual_vertical_balance",
            minimum=-1.0,
            maximum=1.0,
            max_abs_slew_per_s=10.0,
            unit="arb",
            minimum_confidence=minimum_confidence,
        )
    ])


def test_simulated_cycle_accepts_bounded_high_confidence_command():
    result = run_simulated_control_cycle(sample("upper", 112.0), sample("lower", 88.0))
    assert result.decision.accepted is True
    assert result.decision.applied_value is not None
    assert result.ledger_ok is True


def test_invalid_sensor_is_rejected_before_control():
    estimator = DifferentialOpticalEstimator()
    try:
        estimator.estimate(sample("upper", 100.0, valid=False), sample("lower", 100.0))
    except ValueError as exc:
        assert "sensor_invalid" in str(exc)
    else:
        raise AssertionError("invalid sensor sample was not rejected")


def test_out_of_bounds_command_is_rejected():
    safety_gate = gate()
    decision = safety_gate.evaluate(ControlProposal(
        timestamp=1000.0,
        shot_id="test-shot",
        actuator="virtual_vertical_balance",
        requested_value=2.0,
        unit="arb",
        model_id="test-model",
        confidence=0.99,
        rationale="test",
    ))
    assert decision.accepted is False
    assert decision.applied_value is None
    assert decision.reason == "requested_value_out_of_bounds"


def test_low_confidence_command_is_rejected():
    safety_gate = gate(minimum_confidence=0.90)
    decision = safety_gate.evaluate(ControlProposal(
        timestamp=1000.0,
        shot_id="test-shot",
        actuator="virtual_vertical_balance",
        requested_value=0.1,
        unit="arb",
        model_id="test-model",
        confidence=0.50,
        rationale="test",
    ))
    assert decision.accepted is False
    assert decision.reason == "proposal_confidence_below_threshold"


def test_unknown_actuator_is_rejected():
    safety_gate = gate()
    decision = safety_gate.evaluate(ControlProposal(
        timestamp=1000.0,
        shot_id="test-shot",
        actuator="real_coil_current",
        requested_value=0.1,
        unit="arb",
        model_id="test-model",
        confidence=0.99,
        rationale="test",
    ))
    assert decision.accepted is False
    assert decision.reason == "actuator_not_allowlisted"


def test_hash_chain_detects_tampering():
    ledger = FusionAuditLedger()
    ledger.append("one", {"value": 1}, timestamp=1.0)
    ledger.append("two", {"value": 2}, timestamp=2.0)
    ok, reason = ledger.verify()
    assert ok is True
    assert reason == "ok"

    ledger._records[0].payload["value"] = 999
    ok, reason = ledger.verify()
    assert ok is False
    assert reason.startswith("record_hash_mismatch")
