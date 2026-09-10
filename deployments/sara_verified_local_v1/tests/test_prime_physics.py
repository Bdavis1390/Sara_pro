from __future__ import annotations

import math

import pytest

from worldshepherd_sara.prime_physics import (
    PointMass,
    aero_propulsor_trade,
    axisymmetric_cylinder_inertia,
    cg_after_removed_point_masses,
    combine_inertia,
    hadal_effective_displacement_liters,
    hadal_post_ballast_positive_buoyancy_kg,
    hydrostatic_restoring_moment_nm,
    maximum_buoyancy_loss_fraction_before_minimum_margin,
    point_mass_inertia,
    radiator_net_flux_w_m2,
    radiator_rejection_w,
    required_body_utilization,
    rotor_rpm_for_tip_mach,
    unrejected_heat_j,
    vector_magnitude,
)


def _psdm_points() -> list[PointMass]:
    return [
        PointMass(130.0, 0.85, 0.45),
        PointMass(130.0, 0.85, -0.45),
        PointMass(130.0, -0.85, 0.45),
        PointMass(130.0, -0.85, -0.45),
    ]


def test_psdm_v09_loaded_inertia_screen_matches_record():
    central = axisymmetric_cylinder_inertia(
        mass_kg=580.0,
        radius_m=1.05,
        length_m=3.65,
    )
    result = combine_inertia(central, point_mass_inertia(_psdm_points()))
    assert result.ix_kg_m2 == pytest.approx(425.025, abs=0.01)
    assert result.iy_kg_m2 == pytest.approx(1179.483, abs=0.01)
    assert result.iz_kg_m2 == pytest.approx(1284.783, abs=0.01)


def test_psdm_symmetric_pair_removal_preserves_first_order_cg_and_inertia_screen():
    points = _psdm_points()
    removed = [points[0], points[3]]
    cg = cg_after_removed_point_masses(initial_total_mass_kg=1100.0, removed=removed)
    assert cg == pytest.approx((0.0, 0.0, 0.0), abs=1e-12)

    central = axisymmetric_cylinder_inertia(
        mass_kg=580.0,
        radius_m=1.05,
        length_m=3.65,
    )
    remaining = [points[1], points[2]]
    result = combine_inertia(central, point_mass_inertia(remaining))
    assert result.ix_kg_m2 == pytest.approx(372.375, abs=0.01)
    assert result.iy_kg_m2 == pytest.approx(991.633, abs=0.01)
    assert result.iz_kg_m2 == pytest.approx(1044.283, abs=0.01)


def test_psdm_release_mismatch_and_asymmetric_release_cg_screens():
    points = _psdm_points()
    fore_station = cg_after_removed_point_masses(
        initial_total_mass_kg=1100.0,
        removed=[points[0], points[1]],
    )
    lateral_side = cg_after_removed_point_masses(
        initial_total_mass_kg=1100.0,
        removed=[points[0], points[2]],
    )
    one_unit = cg_after_removed_point_masses(
        initial_total_mass_kg=1100.0,
        removed=[points[0]],
    )
    assert vector_magnitude(fore_station) == pytest.approx(0.2631, abs=0.0002)
    assert vector_magnitude(lateral_side) == pytest.approx(0.1393, abs=0.0002)
    assert vector_magnitude(one_unit) == pytest.approx(0.1289, abs=0.0002)


@pytest.mark.parametrize(
    ("effectors", "diameter", "thrust", "power", "mass_each"),
    [
        (4, 1.5958, 446.36, 8.30, 5.75),
        (6, 1.3029, 297.57, 5.5333, 3.8333),
        (8, 1.1284, 223.18, 4.15, 2.875),
        (12, 0.9213, 148.79, 2.7667, 1.9167),
    ],
)
def test_aero_v09_propulsor_trades(effectors, diameter, thrust, power, mass_each):
    result = aero_propulsor_trade(
        gross_mass_kg=182.0,
        total_effective_area_m2=8.0,
        total_design_power_kw=33.2,
        effectors=effectors,
        propulsor_related_mass_kg=23.0,
    )
    assert result.equivalent_diameter_m == pytest.approx(diameter, abs=0.0005)
    assert result.thrust_n_each == pytest.approx(thrust, abs=0.02)
    assert result.design_power_kw_each == pytest.approx(power, abs=0.001)
    assert result.disk_loading_n_m2 == pytest.approx(223.1775, abs=0.001)
    assert result.propulsor_related_mass_kg_each == pytest.approx(mass_each, abs=0.001)


def test_aero_b6_tip_mach_rpm_sensitivity():
    diameter = aero_propulsor_trade(
        gross_mass_kg=182.0,
        total_effective_area_m2=8.0,
        total_design_power_kw=33.2,
        effectors=6,
        propulsor_related_mass_kg=23.0,
    ).equivalent_diameter_m
    assert rotor_rpm_for_tip_mach(diameter_m=diameter, tip_mach=0.55) == pytest.approx(2741, abs=2)
    assert rotor_rpm_for_tip_mach(diameter_m=diameter, tip_mach=0.60) == pytest.approx(2990, abs=2)
    assert rotor_rpm_for_tip_mach(diameter_m=diameter, tip_mach=0.65) == pytest.approx(3239, abs=2)


def test_space_s50_tbi_flux_and_body_utilization_match_v09_screen():
    flux_330 = radiator_net_flux_w_m2(
        temperature_k=330.0, emissivity=0.9, effectiveness=0.7
    )
    flux_350 = radiator_net_flux_w_m2(
        temperature_k=350.0, emissivity=0.9, effectiveness=0.7
    )
    assert flux_330 == pytest.approx(423.6508, abs=0.001)
    assert flux_350 == pytest.approx(536.0737, abs=0.001)

    utilization = required_body_utilization(
        required_rejection_w=700.0,
        temperature_k=330.0,
        deployable_area_m2=1.2,
        body_area_m2=1.2,
        emissivity=0.9,
        effectiveness=0.7,
    )
    assert utilization == pytest.approx(0.37692, abs=0.00001)


def test_space_s50_tbi_rejection_and_two_kw_transient_deficit():
    rejection_330 = radiator_rejection_w(
        temperature_k=330.0,
        deployable_area_m2=1.2,
        body_area_m2=1.2,
        body_utilization=0.60,
        emissivity=0.9,
        effectiveness=0.7,
    )
    rejection_350 = radiator_rejection_w(
        temperature_k=350.0,
        deployable_area_m2=1.2,
        body_area_m2=1.2,
        body_utilization=0.60,
        emissivity=0.9,
        effectiveness=0.7,
    )
    assert rejection_330 == pytest.approx(813.41, abs=0.02)
    assert rejection_350 == pytest.approx(1029.26, abs=0.02)
    assert unrejected_heat_j(
        heat_load_w=2000.0, rejection_w=rejection_330, duration_s=900.0
    ) == pytest.approx(1.06793e6, rel=1e-5)
    assert unrejected_heat_j(
        heat_load_w=2000.0, rejection_w=rejection_350, duration_s=900.0
    ) == pytest.approx(0.873665e6, rel=1e-5)


def test_hadal_v09_displacement_ballast_margin_and_stability_sensitivity():
    displacement_l = hadal_effective_displacement_liters(
        total_mass_kg=242.0,
        apparent_negative_mass_kg=5.0,
        seawater_density_kg_m3=1025.0,
    )
    assert displacement_l == pytest.approx(231.2195, abs=0.001)

    ideal_positive = hadal_post_ballast_positive_buoyancy_kg(
        apparent_negative_mass_kg=5.0,
        released_ballast_kg=15.0,
    )
    assert ideal_positive == pytest.approx(10.0)

    loss_fraction = maximum_buoyancy_loss_fraction_before_minimum_margin(
        buoyancy_equivalent_kg=237.0,
        ideal_positive_buoyancy_kg=10.0,
        minimum_required_positive_buoyancy_kg=5.0,
    )
    assert loss_fraction == pytest.approx(0.021097, abs=0.000001)

    assert hydrostatic_restoring_moment_nm(
        buoyancy_equivalent_kg=237.0,
        cb_cg_separation_m=0.025,
        angle_deg=10.0,
    ) == pytest.approx(10.09, abs=0.02)
    assert hydrostatic_restoring_moment_nm(
        buoyancy_equivalent_kg=237.0,
        cb_cg_separation_m=0.050,
        angle_deg=10.0,
    ) == pytest.approx(20.18, abs=0.03)
    assert hydrostatic_restoring_moment_nm(
        buoyancy_equivalent_kg=237.0,
        cb_cg_separation_m=0.100,
        angle_deg=10.0,
    ) == pytest.approx(40.36, abs=0.05)


def test_invalid_engineering_inputs_fail_closed():
    with pytest.raises(ValueError):
        axisymmetric_cylinder_inertia(mass_kg=0, radius_m=1, length_m=1)
    with pytest.raises(ValueError):
        cg_after_removed_point_masses(
            initial_total_mass_kg=100,
            removed=[PointMass(100, 0, 0)],
        )
    with pytest.raises(ValueError):
        aero_propulsor_trade(
            gross_mass_kg=182,
            total_effective_area_m2=8,
            total_design_power_kw=33.2,
            effectors=0,
            propulsor_related_mass_kg=23,
        )
    with pytest.raises(ValueError):
        radiator_rejection_w(
            temperature_k=330,
            deployable_area_m2=1.2,
            body_area_m2=1.2,
            body_utilization=1.1,
            emissivity=0.9,
            effectiveness=0.7,
        )
    with pytest.raises(ValueError):
        maximum_buoyancy_loss_fraction_before_minimum_margin(
            buoyancy_equivalent_kg=237,
            ideal_positive_buoyancy_kg=4,
            minimum_required_positive_buoyancy_kg=5,
        )
