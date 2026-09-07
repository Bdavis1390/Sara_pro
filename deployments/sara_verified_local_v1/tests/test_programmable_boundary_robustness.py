from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldshepherd_sara.programmable_boundary_robustness import (
    ProgrammableBoundaryRobustnessReport,
    RobustnessOutcome,
    run_programmable_boundary_robustness,
    verify_programmable_boundary_robustness_report,
)


def test_robustness_report_is_deterministic_and_hash_bound():
    first = run_programmable_boundary_robustness()
    second = run_programmable_boundary_robustness()
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.report_digest == second.report_digest
    assert first.report_digest and first.report_digest.startswith("sha256:")
    assert verify_programmable_boundary_robustness_report(first)


def test_nominal_sweep_preserves_adverse_cases_and_blocks_promotion():
    report = run_programmable_boundary_robustness()
    summary = report.summary
    assert summary.nominal_case_count == 36
    assert summary.nominal_pass_count < summary.nominal_case_count
    assert summary.nominal_pass_fraction < report.gate.minimum_nominal_pass_fraction
    assert summary.ratio_degenerate_count > 0
    assert summary.ratio_degenerate_fraction > report.gate.maximum_ratio_degenerate_fraction
    assert "NOMINAL_PASS_FRACTION" in summary.failed_gate_conditions
    assert "RATIO_DEGENERATE_FRACTION" in summary.failed_gate_conditions
    assert summary.outcome == RobustnessOutcome.NO_ROBUSTNESS_PROMOTION
    assert any(not case.case_passed for case in report.nominal_cases)
    assert any(case.ratio_degenerate_reference for case in report.nominal_cases)
    assert any("COHERENT_GAIN_THRESHOLD" in case.failure_reasons for case in report.nominal_cases)


def test_nominal_sweep_covers_declared_geometry_envelope():
    report = run_programmable_boundary_robustness()
    assert {case.tile_count for case in report.nominal_cases} == {6, 8, 12}
    assert {case.tile_spacing_wavelengths for case in report.nominal_cases} == {0.25, 0.35, 0.5}
    assert {case.target_angle_degrees for case in report.nominal_cases} == {-30.0, -10.0, 20.0, 40.0}
    assert all(-60.0 <= case.preserve_angle_degrees <= 60.0 for case in report.nominal_cases)


def test_bounded_perturbations_hold_equal_power_without_erasing_failures():
    report = run_programmable_boundary_robustness()
    assert report.summary.perturbation_case_count == 18
    assert all(case.equal_power_after_normalization for case in report.perturbation_cases)
    assert all(abs(case.total_element_power_proxy - 8.0) <= 1e-10 for case in report.perturbation_cases)
    assert report.summary.perturbation_minimum_retention_fraction >= 0.90
    assert "PERTURBATION_RETENTION" not in report.summary.failed_gate_conditions


def test_thermal_severity_degrades_monotonically_in_surrogate():
    report = run_programmable_boundary_robustness()
    assert report.summary.thermal_case_count == 4
    retentions = [case.target_retention_fraction for case in report.thermal_cases]
    assert retentions == sorted(retentions, reverse=True)
    assert report.summary.thermal_retention_monotonic_nonincreasing is True
    assert "THERMAL_MONOTONICITY" not in report.summary.failed_gate_conditions


def test_claims_boundary_remains_simulation_only():
    report = run_programmable_boundary_robustness()
    payload = report.model_dump(mode="json")
    assert payload["capability_status"] == "SIMULATED_ONLY"
    assert payload["laboratory_validation_performed"] is False
    assert payload["full_wave_validation_performed"] is False
    assert payload["measured_material_properties_used"] is False
    assert payload["broadband_validation_performed"] is False
    assert payload["stealth_or_cloaking_validated"] is False
    assert payload["operational_validation_performed"] is False


@pytest.mark.parametrize(
    "field",
    [
        "laboratory_validation_performed",
        "full_wave_validation_performed",
        "measured_material_properties_used",
        "broadband_validation_performed",
        "stealth_or_cloaking_validated",
        "operational_validation_performed",
    ],
)
def test_report_rejects_physical_or_operational_promotion_flags(field):
    report = run_programmable_boundary_robustness()
    payload = report.model_dump(mode="json")
    payload[field] = True
    with pytest.raises(ValidationError):
        ProgrammableBoundaryRobustnessReport.model_validate(payload)


def test_tamper_breaks_digest_verification():
    report = run_programmable_boundary_robustness()
    payload = report.model_dump(mode="json")
    payload["summary"]["nominal_pass_count"] += 1
    tampered = ProgrammableBoundaryRobustnessReport.model_validate(payload)
    assert not verify_programmable_boundary_robustness_report(tampered)
