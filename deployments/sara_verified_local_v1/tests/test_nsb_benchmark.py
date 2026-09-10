from __future__ import annotations

import pytest

from worldshepherd_sara.nsb_benchmark import (
    ControlOutcome,
    NSBBenchmarkReport,
    VerificationEscalation,
    cancellation_condition,
    classify_control_outcome,
    run_nsb_benchmark,
    verification_escalation,
    verify_nsb_benchmark_report,
)
from worldshepherd_sara.qualification import CapabilityStatus


def test_default_benchmark_passes_g0_g1_without_physical_promotion():
    report = run_nsb_benchmark()
    assert report.summary.g0_passed is True
    assert report.summary.g1_passed is True
    assert report.summary.second_order_vorticity_convergence_observed is True
    assert report.summary.second_order_divergence_convergence_observed is True
    assert report.summary.scaling_instrumentation_passed is True
    assert report.capability_status == CapabilityStatus.SIMULATED_ONLY
    assert report.pde_time_integration_performed is False
    assert report.navier_stokes_blowup_reproduced is False
    assert report.mhd_solver_used is False
    assert report.plasma_solver_used is False
    assert report.laboratory_validation_performed is False
    assert report.propulsion_effect_validated is False
    assert report.shielding_effect_validated is False


def test_manufactured_operators_show_second_order_convergence():
    report = run_nsb_benchmark()
    assert all(1.8 <= value <= 2.2 for value in report.summary.vorticity_observed_orders)
    assert all(1.8 <= value <= 2.2 for value in report.summary.divergence_observed_orders)


def test_scaling_instrumentation_recovers_declared_power_laws():
    report = run_nsb_benchmark(h_exponent=0.005)
    scaling = report.scaling
    assert scaling.radial_length_slope == pytest.approx(scaling.target_radial_length_slope, abs=1e-12)
    assert scaling.axial_length_slope == pytest.approx(scaling.target_axial_length_slope, abs=1e-12)
    assert scaling.peak_velocity_slope == pytest.approx(scaling.target_peak_velocity_slope, abs=1e-12)
    assert scaling.core_energy_slope == pytest.approx(scaling.target_core_energy_slope, abs=1e-12)
    assert scaling.angular_reynolds_slope == pytest.approx(scaling.target_angular_reynolds_slope, abs=1e-12)
    assert scaling.max_absolute_slope_error < 1e-12


def test_divergence_free_manufactured_fields_and_nontrivial_diagnostics():
    report = run_nsb_benchmark(resolutions=(8, 16, 32))
    finest = report.diagnostics[-1]
    assert finest.div_u_rms < 1e-12
    assert finest.div_b_rms < 1e-12
    assert finest.vortex_stretching_rms > 0.0
    assert finest.em_vorticity_forcing_rms > 0.0


def test_cancellation_condition_and_escalation_boundaries():
    assert cancellation_condition((1.0, 2.0)) == pytest.approx(1.0)
    high = cancellation_condition((1000.0, -999.0))
    assert high > 1000.0
    assert verification_escalation(9.999) == VerificationEscalation.NORMAL
    assert verification_escalation(10.0) == VerificationEscalation.REFINE_TIMESTEP
    assert verification_escalation(100.0) == VerificationEscalation.REFINE_TIMESTEP_AND_MESH
    assert verification_escalation(1000.0) == VerificationEscalation.REQUIRE_INDEPENDENT_SOLVER


def test_control_outcome_classification_is_fail_closed():
    assert classify_control_outcome(100.0, 90.0) == ControlOutcome.SUPPRESSION
    assert classify_control_outcome(100.0, 103.0) == ControlOutcome.NEUTRAL
    assert classify_control_outcome(100.0, 110.0) == ControlOutcome.AMPLIFICATION
    assert classify_control_outcome(100.0, 100.0, redirected=True) == ControlOutcome.REDIRECTION
    with pytest.raises(ValueError):
        classify_control_outcome(0.0, 0.0)


def test_report_is_deterministic_hash_bound_and_tamper_detectable():
    first = run_nsb_benchmark(resolutions=(8, 12, 16))
    second = run_nsb_benchmark(resolutions=(8, 12, 16))
    assert first == second
    assert first.report_digest is not None
    assert first.report_digest.startswith("sha256:")
    assert verify_nsb_benchmark_report(first) is True

    tampered = first.model_copy(update={"source_claim_status": "SETTLED_THEOREM"})
    assert verify_nsb_benchmark_report(tampered) is False


def test_fail_closed_model_rejects_unsupported_claim_promotion():
    report = run_nsb_benchmark(resolutions=(8, 12, 16))
    payload = report.model_dump(mode="json")
    payload["navier_stokes_blowup_reproduced"] = True
    with pytest.raises(ValueError):
        NSBBenchmarkReport.model_validate(payload)

    payload = report.model_dump(mode="json")
    payload["capability_status"] = CapabilityStatus.PROVEN_INTERNALLY.value
    with pytest.raises(ValueError):
        NSBBenchmarkReport.model_validate(payload)


def test_invalid_inputs_fail_closed():
    with pytest.raises(ValueError):
        run_nsb_benchmark(resolutions=(8, 16))
    with pytest.raises(ValueError):
        run_nsb_benchmark(resolutions=(16, 8, 32))
    with pytest.raises(ValueError):
        run_nsb_benchmark(resolutions=(8, 8, 16))
    with pytest.raises(ValueError):
        run_nsb_benchmark(h_exponent=0.01)
    with pytest.raises(ValueError):
        cancellation_condition(())
    with pytest.raises(ValueError):
        verification_escalation(-1.0)
