from worldshepherd_sara.quantum_glob_mapping import evaluate_glob_mapping
from worldshepherd_sara.quantum_glob_orbit import OPERATORS, apply_operator, build_operator_mapping, exact_orbit, operator_order


def test_established_operator_orders_and_exact_orbits():
    assert operator_order(OPERATORS["PA"]) == 4
    assert operator_order(OPERATORS["PB"]) == 4
    assert operator_order(OPERATORS["PC"]) == 2
    assert exact_orbit("12345", OPERATORS["PA"])[1] == "31542"
    assert exact_orbit("12345", OPERATORS["PB"])[1] == "13524"
    assert exact_orbit("12345", OPERATORS["PC"])[1] == "14523"


def test_zero_padding_is_not_silent():
    try:
        apply_operator("9069", OPERATORS["PA"])
    except ValueError as exc:
        assert "exactly five symbols" in str(exc)
    else:
        raise AssertionError("4-symbol seed must not be silently padded")


def test_mapping_is_real_computational_object_but_qpu_is_not_justified():
    mapping = build_operator_mapping("PA")
    decision = evaluate_glob_mapping(mapping)
    assert decision.mapping_structurally_valid is True
    assert decision.qpu_execution_justified is False
    assert decision.admissible_for_quantum_experiment is False
    assert any("classical baseline dominates" in reason for reason in decision.reasons)
    assert any("resource estimate" in reason for reason in decision.reasons)
