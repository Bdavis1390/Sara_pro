from worldshepherd_sara.quantum_internal_readiness import audit_internal_closure


def test_internally_controllable_quantum_controls_meet_97_target():
    audit = audit_internal_closure(".")
    assert audit["controls_complete"] == audit["controls_total"]
    assert audit["score"] == 100.0
    assert audit["meets_target"] is True
    assert audit["target"] == 97
