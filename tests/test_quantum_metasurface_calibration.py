from pathlib import Path

from worldshepherd_sara.quantum_metasurface_calibration import (
    FullWaveCalibrationRecord,
    FullWaveSolverClass,
    artifact_digest,
    calibration_template_as_dict,
    compare_complex_response,
    validate_full_wave_calibration,
)


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def _record(full_path: Path, reduced_path: Path) -> FullWaveCalibrationRecord:
    metrics = compare_complex_response(
        [0.0, 45.0, 90.0, 135.0],
        [1.0, 44.0, 92.0, 134.0],
        [-3.0, -2.0, -1.0, -2.5],
        [-3.1, -2.1, -0.9, -2.4],
    )
    return FullWaveCalibrationRecord(
        project_id="WS-METASURFACE",
        calibration_id="WS-META-FIXTURE-001",
        solver_class=FullWaveSolverClass.FEM,
        solver_name="fixture Maxwell solver",
        solver_version="1.0",
        geometry_digest=SHA_A,
        mesh_or_discretization_digest=SHA_B,
        material_model_digest=SHA_A,
        boundary_condition_digest=SHA_B,
        excitation_digest=SHA_A,
        frequency_grid_digest=SHA_B,
        tile_state_map_digest=SHA_A,
        full_wave_result_digest=SHA_B,
        reduced_model_digest=SHA_A,
        reduced_result_digest=SHA_B,
        full_wave_artifact_digest=artifact_digest(full_path),
        reduced_artifact_digest=artifact_digest(reduced_path),
        sample_count=int(metrics["sample_count"]),
        phase_rmse_deg=float(metrics["phase_rmse_deg"]),
        magnitude_rmse_db=float(metrics["magnitude_rmse_db"]),
        max_phase_error_deg=float(metrics["max_phase_error_deg"]),
        max_magnitude_error_db=float(metrics["max_magnitude_error_db"]),
        pass_phase_rmse_deg=3.0,
        pass_magnitude_rmse_db=0.25,
        pass_max_phase_error_deg=4.0,
        pass_max_magnitude_error_db=0.3,
        source_reference="synthetic-test-fixture://WS-META-FIXTURE-001",
    )


def test_phase_comparison_wraps_angles_correctly():
    metrics = compare_complex_response(
        [179.0, -179.0, 0.0],
        [-179.0, 179.0, 1.0],
        [0.0, -1.0, -2.0],
        [0.1, -1.1, -2.0],
    )
    assert metrics["sample_count"] == 3
    assert metrics["max_phase_error_deg"] <= 2.0


def test_full_wave_calibration_requires_both_actual_artifacts(tmp_path):
    full = tmp_path / "full.csv"
    reduced = tmp_path / "reduced.csv"
    full.write_text("f,phase,mag\n1,0,-3\n", encoding="utf-8")
    reduced.write_text("f,phase,mag\n1,1,-3.1\n", encoding="utf-8")
    record = _record(full, reduced)

    missing = validate_full_wave_calibration(record)
    assert missing.accepted is False
    assert any("actual full-wave artifact is required" in reason for reason in missing.reasons)
    assert any("actual reduced artifact is required" in reason for reason in missing.reasons)

    accepted = validate_full_wave_calibration(record, full_wave_artifact=full, reduced_artifact=reduced)
    assert accepted.accepted is True
    assert accepted.gate_id == "WS-METASURFACE-EXT-01"


def test_calibration_rejects_threshold_failure(tmp_path):
    full = tmp_path / "full.csv"
    reduced = tmp_path / "reduced.csv"
    full.write_text("full-wave fixture", encoding="utf-8")
    reduced.write_text("reduced fixture", encoding="utf-8")
    record = _record(full, reduced)
    record = FullWaveCalibrationRecord(**{**record.__dict__, "phase_rmse_deg": 9.0})

    decision = validate_full_wave_calibration(record, full_wave_artifact=full, reduced_artifact=reduced)
    assert decision.accepted is False
    assert any("phase RMSE exceeds" in reason for reason in decision.reasons)


def test_calibration_rejects_mismatched_artifact_digest(tmp_path):
    full = tmp_path / "full.csv"
    reduced = tmp_path / "reduced.csv"
    full.write_text("full-wave fixture", encoding="utf-8")
    reduced.write_text("reduced fixture", encoding="utf-8")
    record = _record(full, reduced)
    full.write_text("mutated after freeze", encoding="utf-8")

    decision = validate_full_wave_calibration(record, full_wave_artifact=full, reduced_artifact=reduced)
    assert decision.accepted is False
    assert any("full-wave artifact digest does not match" in reason for reason in decision.reasons)


def test_template_is_explicitly_not_calibration_evidence():
    payload = calibration_template_as_dict()
    assert payload["gate_id"] == "WS-METASURFACE-EXT-01"
    assert payload["record"]["calibration_id"] == "<replace-me>"
    assert "cannot satisfy full-wave calibration" in payload["claim_control"]
