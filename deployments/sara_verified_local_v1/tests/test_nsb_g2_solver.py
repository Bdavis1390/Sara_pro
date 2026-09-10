from __future__ import annotations

import pytest

from worldshepherd_sara.nsb_g2_solver import (
    NSBG2Report,
    integrate_taylor_green,
    run_nsb_g2_benchmark,
    verify_nsb_g2_report,
)
from worldshepherd_sara.qualification import CapabilityStatus


def test_g2_executes_actual_time_integration_and_passes_reference_gate():
    report = run_nsb_g2_benchmark()
    assert report.actual_pde_time_integration_performed is True
    assert report.convergence.acceptance_pass is True
    assert report.capability_status == CapabilityStatus.SIMULATED_ONLY


def test_spatial_convergence_is_second_order_with_independent_refinement():
    report = run_nsb_g2_benchmark()
    assert report.convergence.spatial_grid_sizes == (12, 24, 48)
    assert report.convergence.spatial_errors[0] > report.convergence.spatial_errors[1]
    assert report.convergence.spatial_errors[1] > report.convergence.spatial_errors[2]
    assert min(report.convergence.spatial_orders) > 1.9


def test_temporal_convergence_is_second_order_from_solution_differences():
    report = run_nsb_g2_benchmark()
    assert report.convergence.temporal_dts == pytest.approx((0.04, 0.02, 0.01))
    assert report.convergence.temporal_pair_differences[0] > report.convergence.temporal_pair_differences[1]
    assert report.convergence.temporal_order > 1.9


def test_incompressibility_and_dissipative_diagnostics_pass():
    report = run_nsb_g2_benchmark()
    assert max(case.divergence_rms for case in report.cases) < 1e-12
    assert all(case.dissipative_energy_monotonic for case in report.cases)
    assert all(case.dissipative_enstrophy_monotonic for case in report.cases)
    assert max(case.kinetic_energy_relative_error for case in report.cases) < 0.01
    assert max(case.enstrophy_relative_error for case in report.cases) < 0.01


def test_report_is_deterministic_hash_bound_and_tamper_detectable():
    first = run_nsb_g2_benchmark()
    second = run_nsb_g2_benchmark()
    assert first == second
    assert first.report_digest is not None
    assert first.report_digest.startswith("sha256:")
    assert verify_nsb_g2_report(first) is True

    tampered = first.model_copy(update={"benchmark_version": "0.7-tampered"})
    assert verify_nsb_g2_report(tampered) is False


def test_claims_model_fails_closed_against_singularity_or_physical_promotion():
    report = run_nsb_g2_benchmark()
    payload = report.model_dump(mode="json")
    payload["navier_stokes_singularity_reproduced"] = True
    with pytest.raises(ValueError):
        NSBG2Report.model_validate(payload)

    payload = report.model_dump(mode="json")
    payload["laboratory_validation_performed"] = True
    with pytest.raises(ValueError):
        NSBG2Report.model_validate(payload)

    payload = report.model_dump(mode="json")
    payload["capability_status"] = CapabilityStatus.PROVEN_INTERNALLY.value
    with pytest.raises(ValueError):
        NSBG2Report.model_validate(payload)


def test_integrator_rejects_unstable_or_invalid_inputs():
    with pytest.raises(ValueError):
        integrate_taylor_green(grid_size=6, viscosity=0.05, dt=0.01, final_time=0.1)
    with pytest.raises(ValueError):
        integrate_taylor_green(grid_size=16, viscosity=0.0, dt=0.01, final_time=0.1)
    with pytest.raises(ValueError):
        integrate_taylor_green(grid_size=48, viscosity=0.05, dt=1.0, final_time=1.0)


def test_refinement_contracts_fail_closed():
    with pytest.raises(ValueError):
        run_nsb_g2_benchmark(spatial_grids=(12, 20, 40))
    with pytest.raises(ValueError):
        run_nsb_g2_benchmark(temporal_dts=(0.04, 0.03, 0.01))
