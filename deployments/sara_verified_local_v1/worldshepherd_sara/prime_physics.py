from __future__ import annotations

import math
from dataclasses import dataclass


ENGINEERING_SCREEN_CLAIMS_BOUNDARY = (
    "Arithmetic/modeling aid only. Results do not establish physical qualification, "
    "flight performance, launch separation, pressure/depth capability, or thermal-vacuum performance."
)
STEFAN_BOLTZMANN_W_M2_K4 = 5.670374419e-8


@dataclass(frozen=True)
class PointMass:
    mass_kg: float
    x_m: float
    y_m: float
    z_m: float = 0.0


@dataclass(frozen=True)
class InertiaScreen:
    ix_kg_m2: float
    iy_kg_m2: float
    iz_kg_m2: float


@dataclass(frozen=True)
class AeroPropulsorTrade:
    effectors: int
    equivalent_diameter_m: float
    thrust_n_each: float
    design_power_kw_each: float
    disk_loading_n_m2: float
    propulsor_related_mass_kg_each: float


def _positive(value: float, name: str) -> float:
    if value <= 0:
        raise ValueError(f"{name} must be > 0")
    return value


def _fraction(value: float, name: str) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be within [0, 1]")
    return value


def axisymmetric_cylinder_inertia(
    *, mass_kg: float, radius_m: float, length_m: float
) -> InertiaScreen:
    """Approximate a cylinder with its longitudinal axis aligned to +X."""
    _positive(mass_kg, "mass_kg")
    _positive(radius_m, "radius_m")
    _positive(length_m, "length_m")
    ix = 0.5 * mass_kg * radius_m**2
    transverse = (mass_kg / 12.0) * (3.0 * radius_m**2 + length_m**2)
    return InertiaScreen(ix, transverse, transverse)


def point_mass_inertia(points: list[PointMass]) -> InertiaScreen:
    ix = sum(p.mass_kg * (p.y_m**2 + p.z_m**2) for p in points)
    iy = sum(p.mass_kg * (p.x_m**2 + p.z_m**2) for p in points)
    iz = sum(p.mass_kg * (p.x_m**2 + p.y_m**2) for p in points)
    if any(p.mass_kg <= 0 for p in points):
        raise ValueError("point masses must be > 0")
    return InertiaScreen(ix, iy, iz)


def combine_inertia(*screens: InertiaScreen) -> InertiaScreen:
    return InertiaScreen(
        sum(item.ix_kg_m2 for item in screens),
        sum(item.iy_kg_m2 for item in screens),
        sum(item.iz_kg_m2 for item in screens),
    )


def cg_after_removed_point_masses(
    *, initial_total_mass_kg: float, removed: list[PointMass]
) -> tuple[float, float, float]:
    """CG after removals from an initially zero-CG assembly.

    The function intentionally assumes the complete initial assembly has CG=(0,0,0).
    It is a first-order release screen, not a multibody separation simulation.
    """
    _positive(initial_total_mass_kg, "initial_total_mass_kg")
    removed_mass = sum(item.mass_kg for item in removed)
    if any(item.mass_kg <= 0 for item in removed):
        raise ValueError("removed point masses must be > 0")
    remaining_mass = initial_total_mass_kg - removed_mass
    if remaining_mass <= 0:
        raise ValueError("removed mass must be less than initial total mass")
    return (
        -sum(item.mass_kg * item.x_m for item in removed) / remaining_mass,
        -sum(item.mass_kg * item.y_m for item in removed) / remaining_mass,
        -sum(item.mass_kg * item.z_m for item in removed) / remaining_mass,
    )


def vector_magnitude(vector: tuple[float, float, float]) -> float:
    return math.sqrt(sum(component**2 for component in vector))


def aero_propulsor_trade(
    *,
    gross_mass_kg: float,
    total_effective_area_m2: float,
    total_design_power_kw: float,
    effectors: int,
    propulsor_related_mass_kg: float,
    gravity_m_s2: float = 9.81,
) -> AeroPropulsorTrade:
    _positive(gross_mass_kg, "gross_mass_kg")
    _positive(total_effective_area_m2, "total_effective_area_m2")
    _positive(total_design_power_kw, "total_design_power_kw")
    _positive(propulsor_related_mass_kg, "propulsor_related_mass_kg")
    _positive(gravity_m_s2, "gravity_m_s2")
    if effectors <= 0:
        raise ValueError("effectors must be > 0")

    area_each = total_effective_area_m2 / effectors
    diameter = math.sqrt(4.0 * area_each / math.pi)
    total_thrust = gross_mass_kg * gravity_m_s2
    return AeroPropulsorTrade(
        effectors=effectors,
        equivalent_diameter_m=diameter,
        thrust_n_each=total_thrust / effectors,
        design_power_kw_each=total_design_power_kw / effectors,
        disk_loading_n_m2=total_thrust / total_effective_area_m2,
        propulsor_related_mass_kg_each=propulsor_related_mass_kg / effectors,
    )


def rotor_rpm_for_tip_mach(
    *, diameter_m: float, tip_mach: float, speed_of_sound_m_s: float = 340.0
) -> float:
    _positive(diameter_m, "diameter_m")
    _positive(tip_mach, "tip_mach")
    _positive(speed_of_sound_m_s, "speed_of_sound_m_s")
    tip_speed = tip_mach * speed_of_sound_m_s
    return tip_speed * 60.0 / (math.pi * diameter_m)


def radiator_net_flux_w_m2(
    *, temperature_k: float, emissivity: float, effectiveness: float
) -> float:
    _positive(temperature_k, "temperature_k")
    _fraction(emissivity, "emissivity")
    _fraction(effectiveness, "effectiveness")
    return (
        STEFAN_BOLTZMANN_W_M2_K4
        * emissivity
        * temperature_k**4
        * effectiveness
    )


def radiator_rejection_w(
    *,
    temperature_k: float,
    deployable_area_m2: float,
    body_area_m2: float,
    body_utilization: float,
    emissivity: float,
    effectiveness: float,
) -> float:
    if deployable_area_m2 < 0 or body_area_m2 < 0:
        raise ValueError("radiator areas must be >= 0")
    _fraction(body_utilization, "body_utilization")
    effective_area = deployable_area_m2 + body_area_m2 * body_utilization
    return radiator_net_flux_w_m2(
        temperature_k=temperature_k,
        emissivity=emissivity,
        effectiveness=effectiveness,
    ) * effective_area


def required_body_utilization(
    *,
    required_rejection_w: float,
    temperature_k: float,
    deployable_area_m2: float,
    body_area_m2: float,
    emissivity: float,
    effectiveness: float,
) -> float:
    _positive(required_rejection_w, "required_rejection_w")
    if deployable_area_m2 < 0:
        raise ValueError("deployable_area_m2 must be >= 0")
    _positive(body_area_m2, "body_area_m2")
    flux = radiator_net_flux_w_m2(
        temperature_k=temperature_k,
        emissivity=emissivity,
        effectiveness=effectiveness,
    )
    utilization = (required_rejection_w / flux - deployable_area_m2) / body_area_m2
    return utilization


def unrejected_heat_j(
    *, heat_load_w: float, rejection_w: float, duration_s: float
) -> float:
    _positive(heat_load_w, "heat_load_w")
    if rejection_w < 0:
        raise ValueError("rejection_w must be >= 0")
    _positive(duration_s, "duration_s")
    return max(0.0, heat_load_w - rejection_w) * duration_s


def hadal_effective_displacement_liters(
    *,
    total_mass_kg: float,
    apparent_negative_mass_kg: float,
    seawater_density_kg_m3: float,
) -> float:
    _positive(total_mass_kg, "total_mass_kg")
    _positive(seawater_density_kg_m3, "seawater_density_kg_m3")
    if apparent_negative_mass_kg < 0 or apparent_negative_mass_kg >= total_mass_kg:
        raise ValueError("apparent_negative_mass_kg must be within [0, total_mass_kg)")
    buoyancy_equivalent_kg = total_mass_kg - apparent_negative_mass_kg
    return 1000.0 * buoyancy_equivalent_kg / seawater_density_kg_m3


def hadal_post_ballast_positive_buoyancy_kg(
    *, apparent_negative_mass_kg: float, released_ballast_kg: float
) -> float:
    if apparent_negative_mass_kg < 0:
        raise ValueError("apparent_negative_mass_kg must be >= 0")
    _positive(released_ballast_kg, "released_ballast_kg")
    return released_ballast_kg - apparent_negative_mass_kg


def maximum_buoyancy_loss_fraction_before_minimum_margin(
    *,
    buoyancy_equivalent_kg: float,
    ideal_positive_buoyancy_kg: float,
    minimum_required_positive_buoyancy_kg: float,
) -> float:
    _positive(buoyancy_equivalent_kg, "buoyancy_equivalent_kg")
    if minimum_required_positive_buoyancy_kg < 0:
        raise ValueError("minimum_required_positive_buoyancy_kg must be >= 0")
    if ideal_positive_buoyancy_kg < minimum_required_positive_buoyancy_kg:
        raise ValueError("ideal margin must be >= minimum required margin")
    return (
        ideal_positive_buoyancy_kg - minimum_required_positive_buoyancy_kg
    ) / buoyancy_equivalent_kg


def hydrostatic_restoring_moment_nm(
    *,
    buoyancy_equivalent_kg: float,
    cb_cg_separation_m: float,
    angle_deg: float,
    gravity_m_s2: float = 9.81,
) -> float:
    _positive(buoyancy_equivalent_kg, "buoyancy_equivalent_kg")
    _positive(cb_cg_separation_m, "cb_cg_separation_m")
    _positive(gravity_m_s2, "gravity_m_s2")
    if not 0.0 <= angle_deg <= 180.0:
        raise ValueError("angle_deg must be within [0, 180]")
    return (
        buoyancy_equivalent_kg
        * gravity_m_s2
        * cb_cg_separation_m
        * math.sin(math.radians(angle_deg))
    )
