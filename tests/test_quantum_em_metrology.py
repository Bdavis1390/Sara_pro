from pathlib import Path

from worldshepherd_sara.quantum_em_metrology import (
    EMMetrologyTaskRecord,
    NullControlCase,
    artifact_digest,
    em_metrology_template_as_dict,
    validate_em_metrology_task,
)


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def _record(path: Path) -> EMMetrologyTaskRecord:
    controls = (
        NullControlCase("N1", "power_or_excitation_off", "excitation disabled fixture", SHA_A, "separates active excitation from baseline"),
        NullControlCase("N2", "sham_or_dummy_load", "dummy load fixture", SHA_B, "separates apparatus loading from target interaction"),
        NullControlCase("N3", "orientation_or_coupling_reversal", "reversed coupling fixture", SHA_A, "tests sign/orientation sensitivity"),
    )
    return EMMetrologyTaskRecord(
        project_id="WS-EM-PROPULSION",
        task_id="WS-EMP-MET-FIXTURE-001",
        support_scope="software fixture for bounded materials/metrology task",
        material_or_apparatus_id="fixture-apparatus",
        target_observable="fixture calibrated force-like observable",
        observable_units="fixture-units",
        instrument_id="fixture-instrument",
        calibration_id="fixture-calibration",
        calibration_certificate_digest=SHA_A,
        apparatus_configuration_digest=SHA_B,
        test_protocol_digest=SHA_A,
        environmental_monitor_digest=SHA_B,
        raw_data_artifact_digest=artifact_digest(path),
        uncertainty_budget_digest=SHA_A,
        null_matrix_digest=SHA_B,
        null_controls=controls,
        environmental_channels=("temperature", "magnetic_field"),
        repeat_target=3,
        separate_propulsion_claim_gate=True,
        source_reference="synthetic-test-fixture://WS-EMP-MET-FIXTURE-001",
    )


def test_em_support_gate_requires_actual_raw_artifact_and_null_matrix(tmp_path):
    raw = tmp_path / "metrology.csv"
    raw.write_text("run,value\n1,0\n", encoding="utf-8")
    record = _record(raw)

    blocked = validate_em_metrology_task(record)
    assert blocked.accepted is False
    assert any("actual raw metrology artifact is required" in reason for reason in blocked.reasons)

    accepted = validate_em_metrology_task(record, raw_data_artifact=raw)
    assert accepted.accepted is True
    assert accepted.gate_id == "WS-EM-PROPULSION-EXT-01"


def test_em_support_gate_refuses_collapsing_propulsion_claim_boundary(tmp_path):
    raw = tmp_path / "metrology.csv"
    raw.write_text("fixture", encoding="utf-8")
    record = _record(raw)
    record = EMMetrologyTaskRecord(**{**record.__dict__, "separate_propulsion_claim_gate": False})

    decision = validate_em_metrology_task(record, raw_data_artifact=raw)
    assert decision.accepted is False
    assert any("separate propulsion claim gate" in reason for reason in decision.reasons)


def test_em_support_gate_requires_three_distinct_control_classes(tmp_path):
    raw = tmp_path / "metrology.csv"
    raw.write_text("fixture", encoding="utf-8")
    record = _record(raw)
    duplicate_class = (
        NullControlCase("N1", "sham", "one", SHA_A, "disc one"),
        NullControlCase("N2", "sham", "two", SHA_B, "disc two"),
        NullControlCase("N3", "sham", "three", SHA_A, "disc three"),
    )
    record = EMMetrologyTaskRecord(**{**record.__dict__, "null_controls": duplicate_class})

    decision = validate_em_metrology_task(record, raw_data_artifact=raw)
    assert decision.accepted is False
    assert any("three distinct control classes" in reason for reason in decision.reasons)


def test_template_explicitly_blocks_propulsion_inference():
    payload = em_metrology_template_as_dict()
    assert payload["gate_id"] == "WS-EM-PROPULSION-EXT-01"
    assert payload["record"]["separate_propulsion_claim_gate"] is True
    assert "cannot be cited as proof of propulsion" in payload["claim_control"]
