from __future__ import annotations

import pytest

from worldshepherd_sara.programmable_boundary_benchmark import (
    BoundaryControlMode,
    ProgrammableBoundaryBenchmarkReport,
    run_programmable_boundary_benchmark,
    verify_programmable_boundary_benchmark_report,
)
from worldshepherd_sara.qualification import CapabilityStatus


def _by_id(report):
    return {scenario.scenario_id: scenario for scenario in report.scenarios}


def test_default_benchmark_contains_required_disconfirming_controls():
    report = run_programmable_boundary_benchmark()
    scenarios = _by_id(report)
    assert set(scenarios) == {
        "passive_reference",
        "random_open_loop",
        "coherent_target",
        "null_target",
        "thermal_drift",
    }
    assert scenarios["passive_reference"].mode == BoundaryControlMode.PASSIVE
    assert scenarios["random_open_loop"].mode == BoundaryControlMode.RANDOM_OPEN_LOOP
    assert scenarios["coherent_target"].mode == BoundaryControlMode.COHERENT_TARGET
    assert scenarios["null_target"].mode == BoundaryControlMode.NULL_TARGET
    assert scenarios["thermal_drift"].mode == BoundaryControlMode.THERMAL_DRIFT


def test_nonthermal_design_controls_use_equal_total_power_proxy():
    report = run_programmable_boundary_benchmark()
    scenarios = _by_id(report)
    for scenario_id in (
        "passive_reference",
        "random_open_loop",
        "coherent_target",
        "null_target",
    ):
        assert scenarios[scenario_id].total_element_power_proxy == pytest.approx(
            report.tile_count, abs=1e-10
        )
    assert report.summary.equal_power_design_controls is True


def test_coherent_control_improves_generic_target_over_passive():
    report = run_programmable_boundary_benchmark()
    scenarios = _by_id(report)
    coherent = scenarios["coherent_target"].target_normalized_field
    passive = scenarios["passive_reference"].target_normalized_field
    assert coherent is not None and passive is not None
    assert coherent > 0.99
    assert coherent > passive * 1.5
    assert report.summary.coherent_gain_over_passive > 1.5


def test_random_open_loop_is_not_mistaken_for_target_aware_control():
    report = run_programmable_boundary_benchmark()
    scenarios = _by_id(report)
    random_field = scenarios["random_open_loop"].target_normalized_field
    coherent = scenarios["coherent_target"].target_normalized_field
    assert random_field is not None and coherent is not None
    assert random_field < coherent


def test_constrained_null_suppresses_generic_angle_and_preserves_other_angle():
    report = run_programmable_boundary_benchmark()
    scenario = _by_id(report)["null_target"]
    assert scenario.target_angle_degrees == 0.0
    assert scenario.preserve_angle_degrees == 25.0
    assert scenario.target_normalized_field is not None
    assert scenario.preserve_normalized_field is not None
    assert scenario.target_normalized_field < 1e-8
    assert scenario.preserve_normalized_field > 0.75
    assert report.summary.null_suppression_ratio_vs_passive < 1e-6
    assert report.summary.null_preserve_fraction > 0.75


def test_thermal_drift_degrades_target_and_reduces_power_proxy():
    report = run_programmable_boundary_benchmark()
    scenarios = _by_id(report)
    coherent = scenarios["coherent_target"]
    thermal = scenarios["thermal_drift"]
    assert coherent.target_normalized_field is not None
    assert thermal.target_normalized_field is not None
    assert thermal.target_normalized_field < coherent.target_normalized_field
    assert thermal.total_element_power_proxy < coherent.total_element_power_proxy
    assert report.summary.thermal_target_retention_fraction < 0.98
    assert max(state.normalized_temperature for state in thermal.tile_states) == pytest.approx(1.0)


def test_expected_control_behavior_gate_is_observed_without_physical_promotion():
    report = run_programmable_boundary_benchmark()
    assert report.summary.expected_control_behavior_observed is True
    assert report.capability_status == CapabilityStatus.SIMULATED_ONLY
    assert report.full_wave_solver_used is False
    assert report.mutual_impedance_modeled is False
    assert report.measured_material_properties_used is False
    assert report.laboratory_validation_performed is False
    assert report.stealth_or_cloaking_validated is False
    assert report.broadband_spectrum_validated is False
    assert report.operational_validation_performed is False


def test_report_is_deterministic_hash_bound_and_tamper_detectable():
    first = run_programmable_boundary_benchmark()
    second = run_programmable_boundary_benchmark()
    assert first == second
    assert first.report_digest is not None
    assert first.report_digest.startswith("sha256:")
    assert verify_programmable_boundary_benchmark_report(first) is True

    tampered = first.model_copy(update={"tile_spacing_wavelengths": 0.4})
    assert verify_programmable_boundary_benchmark_report(tampered) is False


def test_fail_closed_model_rejects_physical_claim_promotion():
    report = run_programmable_boundary_benchmark()
    payload = report.model_dump(mode="json")
    payload["laboratory_validation_performed"] = True
    with pytest.raises(ValueError):
        ProgrammableBoundaryBenchmarkReport.model_validate(payload)

    payload = report.model_dump(mode="json")
    payload["stealth_or_cloaking_validated"] = True
    with pytest.raises(ValueError):
        ProgrammableBoundaryBenchmarkReport.model_validate(payload)


def test_invalid_geometry_and_angles_fail_closed():
    with pytest.raises(ValueError):
        run_programmable_boundary_benchmark(tile_count=3)
    with pytest.raises(ValueError):
        run_programmable_boundary_benchmark(tile_spacing_wavelengths=0.75)
    with pytest.raises(ValueError):
        run_programmable_boundary_benchmark(coherent_target_angle_degrees=80.0)
