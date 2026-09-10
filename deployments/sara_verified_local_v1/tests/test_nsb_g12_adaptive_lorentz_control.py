import pytest

from worldshepherd_sara.nsb_g12_adaptive_lorentz_control import (
    NSBG12Report,
    integrate_feedback_control,
    run_nsb_g12_benchmark,
    verify_nsb_g12_report,
)


REPORT = run_nsb_g12_benchmark()


def test_g12_default_report_passes_and_verifies():
    assert REPORT.acceptance.acceptance_pass
    assert REPORT.acceptance.baseline_parity_pass
    assert REPORT.acceptance.bounded_command_pass
    assert REPORT.acceptance.target_reduction_pass
    assert REPORT.acceptance.enstrophy_reduction_pass
    assert REPORT.acceptance.wrong_sign_ordering_pass
    assert REPORT.acceptance.geometry_pass
    assert REPORT.acceptance.adaptive_response_pass
    assert verify_nsb_g12_report(REPORT)


def test_g12_controller_reduces_target_and_enstrophy():
    case = REPORT.control_case
    assert case.target_modal_energy_controlled_final < case.target_modal_energy_baseline_final
    assert case.controlled_enstrophy_final < case.baseline_enstrophy_final
    assert case.target_modal_energy_reduction_fraction >= REPORT.acceptance.target_reduction_floor
    assert case.enstrophy_reduction_fraction >= REPORT.acceptance.enstrophy_reduction_floor


def test_g12_wrong_sign_is_worse_than_correct_feedback():
    case = REPORT.control_case
    assert case.target_modal_energy_wrong_sign_final > case.target_modal_energy_controlled_final
    assert case.wrong_sign_vs_controlled_fraction > 0.0


def test_g12_commands_remain_bounded_and_adaptive():
    case = REPORT.control_case
    assert case.max_abs_command <= case.command_limit + REPORT.acceptance.command_bound_tolerance
    assert case.control_effort > 0.0
    assert case.initial_command_rms > 0.0
    assert abs(case.final_command_rms - case.initial_command_rms) > 1e-6


def test_g12_zero_control_matches_g10_plant():
    assert REPORT.control_case.baseline_parity_l2 <= REPORT.acceptance.baseline_parity_limit


def test_g12_integrator_rejects_invalid_gain():
    omega = [[0.0] * 8 for _ in range(8)]
    a = [[0.0] * 8 for _ in range(8)]
    with pytest.raises(ValueError):
        integrate_feedback_control(
            initial_vorticity=omega,
            initial_magnetic_potential=a,
            viscosity=0.01,
            resistivity=0.01,
            dt=0.001,
            final_time=0.01,
            gain=-1.0,
            command_limit=1.0,
        )


def test_g12_digest_detects_tampering():
    tampered = REPORT.model_copy(
        update={
            "control_case": REPORT.control_case.model_copy(
                update={"control_effort": REPORT.control_case.control_effort + 1.0}
            )
        }
    )
    assert not verify_nsb_g12_report(tampered)


def test_g12_fail_closed_physical_actuator_claim():
    payload = REPORT.model_dump(mode="json")
    payload["physical_actuator_mapping_validated"] = True
    with pytest.raises(ValueError):
        NSBG12Report.model_validate(payload)


def test_g12_fail_closed_propulsion_claim():
    payload = REPORT.model_dump(mode="json")
    payload["propulsion_or_shielding_validated"] = True
    with pytest.raises(ValueError):
        NSBG12Report.model_validate(payload)
