#!/usr/bin/env python3
"""
Worldshepherd synthetic analytical baselines.

These calculations are intentionally low-order, deterministic sanity baselines.
They are not substitutes for full-wave EM, CALPHAD, CFD/FEA, plasma simulation,
hardware-in-the-loop, accredited lab measurement, flight test, clinical
validation, or independent review.

Outputs are labeled SIMULATION ONLY.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

G0 = 9.80665
C0 = 299_792_458.0
QE = 1.602176634e-19
AMU = 1.66053906660e-27


def energy_storage_baseline() -> dict:
    ambient_k = 298.15
    heat_capacity_j_per_k = 5_000.0
    thermal_resistance_k_per_w = 0.08
    internal_heat_w = 900.0
    duration_s = 3600
    dt_s = 1.0

    t_k = ambient_k
    peak_k = t_k
    for _ in range(int(duration_s / dt_s)):
        q_loss_w = (t_k - ambient_k) / thermal_resistance_k_per_w
        t_k += (internal_heat_w - q_loss_w) / heat_capacity_j_per_k * dt_s
        peak_k = max(peak_k, t_k)

    steady_k = ambient_k + internal_heat_w * thermal_resistance_k_per_w
    time_constant_s = heat_capacity_j_per_k * thermal_resistance_k_per_w
    return {
        "workstream": "WS-ENERGY",
        "model": "single-node lumped thermal RC",
        "status": "SIMULATION ONLY",
        "inputs": {
            "ambient_k": ambient_k,
            "heat_capacity_j_per_k": heat_capacity_j_per_k,
            "thermal_resistance_k_per_w": thermal_resistance_k_per_w,
            "internal_heat_w": internal_heat_w,
            "duration_s": duration_s,
            "dt_s": dt_s,
        },
        "results": {
            "peak_temperature_k": round(peak_k, 6),
            "steady_state_temperature_k": round(steady_k, 6),
            "thermal_time_constant_s": round(time_constant_s, 6),
        },
        "acceptance_sanity": {
            "energy_balance_bounded": peak_k <= steady_k + 0.02,
            "temperature_nonnegative": peak_k > 0.0,
        },
        "boundary": "Synthetic thermal-control baseline only; no battery chemistry, pack, HIL, fault-test, safety certification, or hardware performance claim.",
    }


def resonance_baseline() -> dict:
    mass_kg = 12.0
    stiffness_n_per_m = 24_000.0
    damping_n_s_per_m = 180.0

    omega_n = math.sqrt(stiffness_n_per_m / mass_kg)
    f_n_hz = omega_n / (2.0 * math.pi)
    zeta = damping_n_s_per_m / (2.0 * math.sqrt(stiffness_n_per_m * mass_kg))
    q_factor = 1.0 / (2.0 * zeta) if zeta > 0 else math.inf

    return {
        "workstream": "RESONANCE",
        "model": "linear single-degree-of-freedom mass-spring-damper",
        "status": "SIMULATION ONLY",
        "inputs": {
            "mass_kg": mass_kg,
            "stiffness_n_per_m": stiffness_n_per_m,
            "damping_n_s_per_m": damping_n_s_per_m,
        },
        "results": {
            "natural_frequency_hz": round(f_n_hz, 6),
            "damping_ratio": round(zeta, 6),
            "quality_factor": round(q_factor, 6),
        },
        "acceptance_sanity": {
            "stable_linear_damping": zeta > 0.0,
            "underdamped_example": 0.0 < zeta < 1.0,
        },
        "boundary": "Conventional structural-dynamics sanity baseline only; no anomalous, non-Newtonian, antigravity, or reactionless effect is modeled or implied.",
    }


def helios_link_baseline() -> dict:
    wavelength_m = 1.064e-6
    tx_aperture_diameter_m = 0.10
    range_m = 100.0
    receiver_radius_m = 0.05
    transmitted_power_w = 1.0
    receiver_conversion_efficiency = 0.35
    pointing_error_rad = 50e-6

    divergence_rad = 1.22 * wavelength_m / tx_aperture_diameter_m
    spot_radius_m = max(range_m * divergence_rad, 1e-12)
    capture_fraction = 1.0 - math.exp(-2.0 * (receiver_radius_m / spot_radius_m) ** 2)
    capture_fraction = min(max(capture_fraction, 0.0), 1.0)
    pointing_offset_m = range_m * pointing_error_rad
    pointing_loss = math.exp(-2.0 * (pointing_offset_m / spot_radius_m) ** 2)
    pointing_loss = min(max(pointing_loss, 0.0), 1.0)
    received_optical_w = transmitted_power_w * capture_fraction * pointing_loss
    delivered_electric_w = received_optical_w * receiver_conversion_efficiency

    return {
        "workstream": "HELIOS-LINK",
        "model": "diffraction-bounded low-power optical link sanity model",
        "status": "SIMULATION ONLY",
        "inputs": {
            "wavelength_m": wavelength_m,
            "tx_aperture_diameter_m": tx_aperture_diameter_m,
            "range_m": range_m,
            "receiver_radius_m": receiver_radius_m,
            "transmitted_power_w": transmitted_power_w,
            "receiver_conversion_efficiency": receiver_conversion_efficiency,
            "pointing_error_rad": pointing_error_rad,
        },
        "results": {
            "divergence_rad": divergence_rad,
            "spot_radius_m": spot_radius_m,
            "capture_fraction": capture_fraction,
            "pointing_loss": pointing_loss,
            "received_optical_w": received_optical_w,
            "delivered_electric_w": delivered_electric_w,
        },
        "acceptance_sanity": {
            "energy_conservation": 0.0 <= delivered_electric_w <= transmitted_power_w,
            "bounded_capture": 0.0 <= capture_fraction <= 1.0,
            "bounded_pointing_loss": 0.0 <= pointing_loss <= 1.0,
        },
        "boundary": "Low-power synthetic link-budget sanity baseline only; not a power-beaming authorization, range-test result, safety finding, or end-to-end efficiency validation.",
    }


def ion_propulsion_baseline() -> dict:
    ion_mass_amu = 131.293
    ion_mass_kg = ion_mass_amu * AMU
    charge_state = 1.0
    accelerator_voltage_v = 1000.0
    mass_flow_kg_s = 2.0e-6
    beam_efficiency = 0.70

    exhaust_velocity_m_s = math.sqrt(2.0 * charge_state * QE * accelerator_voltage_v / ion_mass_kg)
    thrust_n = mass_flow_kg_s * exhaust_velocity_m_s
    isp_s = exhaust_velocity_m_s / G0
    ideal_jet_power_w = 0.5 * mass_flow_kg_s * exhaust_velocity_m_s**2
    minimum_input_power_w = ideal_jet_power_w / beam_efficiency

    return {
        "workstream": "ION-EP",
        "model": "ideal singly-charged ion electrostatic acceleration budget",
        "status": "SIMULATION ONLY",
        "inputs": {
            "ion_mass_amu": ion_mass_amu,
            "charge_state": charge_state,
            "accelerator_voltage_v": accelerator_voltage_v,
            "mass_flow_kg_s": mass_flow_kg_s,
            "beam_efficiency": beam_efficiency,
        },
        "results": {
            "ideal_exhaust_velocity_m_s": exhaust_velocity_m_s,
            "ideal_thrust_n": thrust_n,
            "ideal_specific_impulse_s": isp_s,
            "ideal_jet_power_w": ideal_jet_power_w,
            "minimum_input_power_w": minimum_input_power_w,
        },
        "acceptance_sanity": {
            "positive_thrust": thrust_n > 0.0,
            "power_bound": minimum_input_power_w >= ideal_jet_power_w,
            "no_reactionless_assumption": mass_flow_kg_s > 0.0,
        },
        "boundary": "Ideal analytical budget only; excludes ionization losses, grids, divergence, neutralization, erosion, plume, charging, thermal rejection, calibrated thrust, endurance, and spacecraft integration.",
    }


def metasurface_sanity_baseline() -> dict:
    frequency_hz = 10.0e9
    wavelength_m = C0 / frequency_hz
    cell_pitch_m = wavelength_m / 8.0
    target_angle_deg = 20.0
    target_angle_rad = math.radians(target_angle_deg)
    k0_rad_per_m = 2.0 * math.pi / wavelength_m
    phase_gradient_rad_per_m = k0_rad_per_m * math.sin(target_angle_rad)
    phase_step_rad = phase_gradient_rad_per_m * cell_pitch_m
    phase_step_deg = math.degrees(phase_step_rad)

    return {
        "workstream": "WS-MS",
        "model": "1-D phase-gradient steering sanity relation",
        "status": "SIMULATION ONLY",
        "inputs": {
            "frequency_hz": frequency_hz,
            "wavelength_m": wavelength_m,
            "cell_pitch_m": cell_pitch_m,
            "target_angle_deg": target_angle_deg,
            "incidence": "normal",
        },
        "results": {
            "free_space_wavenumber_rad_per_m": k0_rad_per_m,
            "required_phase_gradient_rad_per_m": phase_gradient_rad_per_m,
            "phase_step_per_cell_rad": phase_step_rad,
            "phase_step_per_cell_deg": phase_step_deg,
        },
        "acceptance_sanity": {
            "subwavelength_cell": cell_pitch_m < wavelength_m / 2.0,
            "finite_phase_step": math.isfinite(phase_step_rad),
        },
        "boundary": "Pre-full-wave analytical sanity layer only; no efficiency, loss, bandwidth, beam quality, fabrication tolerance, VNA, environmental, or measured RF performance claim.",
    }


BASELINES = {
    "energy": energy_storage_baseline,
    "resonance": resonance_baseline,
    "helios": helios_link_baseline,
    "ion": ion_propulsion_baseline,
    "metasurface": metasurface_sanity_baseline,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="evidence/synthetic-baselines")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "WS-SYNTHETIC-BASELINE-MANIFEST-V1",
        "evidence_class": "SIMULATED ONLY",
        "claims_boundary": "Synthetic analytical baselines never satisfy physical, clinical, flight, RF-measurement, regulatory, certification, or independent-validation gates.",
        "records": [],
    }

    failed = []
    for name, fn in BASELINES.items():
        record = fn()
        path = out_dir / f"{name}.json"
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest["records"].append({"name": name, "path": str(path), "workstream": record["workstream"]})
        for check, passed in record["acceptance_sanity"].items():
            if not passed:
                failed.append(f"{name}:{check}")

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if failed:
        raise SystemExit("failed baseline sanity checks: " + ", ".join(failed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
