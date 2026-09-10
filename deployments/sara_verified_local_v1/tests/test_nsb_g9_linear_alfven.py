from __future__ import annotations

import pytest

from worldshepherd_sara.nsb_g9_linear_alfven import (
    NSBG9Report,
    integrate_linear_alfven,
    run_nsb_g9_benchmark,
    verify_nsb_g9_report,
)


@pytest.fixture(scope="module")
def report():
    return run_nsb_g9_benchmark()


def test_default_g9_gate_passes_and_digest_verifies(report):
    assert report.acceptance.acceptance_pass is True
    assert verify_nsb_g9_report(report) is True
    assert report.report_digest is not None
    assert report.report_digest.startswith("sha256:")


def test_spatial_convergence_is_second_order(report):
    assert min(report.acceptance.spatial_orders) >= 1.9
    assert report.spatial_cases[-1].combined_l2_error <= 1e-3


def test_temporal_convergence_is_fourth_order(report):
    assert min(report.acceptance.temporal_orders) >= 3.6
    assert report.temporal_cases[-1].combined_l2_error <= 1e-9


def test_quarter_period_transfers_energy_to_magnetic_component(report):
    transfer = report.transfer_result
    assert transfer.mode_magnetic_reynolds > 1.0
    assert transfer.magnetic_energy_fraction_final >= 0.999
    assert transfer.total_energy_relative_error <= 2e-4
    assert transfer.magnetic_energy_final > transfer.kinetic_energy_final


def test_diffusion_sign_and_zero_coupling_controls(report):
    controls = report.controls
    assert controls.diffusion_only_magnetic_l2 <= 5e-5
    assert controls.diffusion_only_velocity_rms <= 1e-12
    assert controls.alfven_sign_velocity_l2 <= 1e-12
    assert controls.alfven_sign_magnetic_antisymmetry_l2 <= 1e-12
    assert controls.zero_coupling_generated_magnetic_rms <= 1e-12


def test_integrator_rejects_bad_inputs():
    u = [0.0] * 16
    b = [0.0] * 16
    with pytest.raises(ValueError):
        integrate_linear_alfven(
            initial_velocity=u,
            initial_magnetic=b[:-1],
            alfven_speed=1.0,
            viscosity=0.02,
            magnetic_diffusivity=0.02,
            dt=0.01,
            final_time=0.1,
        )
    with pytest.raises(ValueError):
        integrate_linear_alfven(
            initial_velocity=u,
            initial_magnetic=b,
            alfven_speed=1.0,
            viscosity=-0.01,
            magnetic_diffusivity=0.02,
            dt=0.01,
            final_time=0.1,
        )


def test_report_tampering_breaks_digest(report):
    tampered = report.model_copy(update={"benchmark_version": "tampered"})
    assert verify_nsb_g9_report(tampered) is False


def test_claim_promotion_fails_closed(report):
    payload = report.model_dump(mode="json")
    payload["nonlinear_mhd_solver_claimed"] = True
    with pytest.raises(ValueError):
        NSBG9Report.model_validate(payload)

    payload = report.model_dump(mode="json")
    payload["plasma_solved"] = True
    with pytest.raises(ValueError):
        NSBG9Report.model_validate(payload)


def test_non_factor_two_refinement_is_rejected():
    with pytest.raises(ValueError):
        run_nsb_g9_benchmark(spatial_grids=(32, 48, 96))
    with pytest.raises(ValueError):
        run_nsb_g9_benchmark(temporal_dts=(0.016, 0.009, 0.004))


def test_gate_explicitly_remains_linearized(report):
    assert report.linearized_induction_equation_solved is True
    assert report.linearized_lorentz_backreaction_solved is True
    assert report.finite_rm_linear_reference_implemented is True
    assert report.nonlinear_mhd_solver_claimed is False
    assert report.general_2d_or_3d_mhd_claimed is False
    assert report.plasma_solved is False
