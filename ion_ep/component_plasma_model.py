#!/usr/bin/env python3
"""Bounded 0-D ion-source / extraction-grid model for ION-EP.

This model provides a reproducible component/plasma sanity layer using mass,
charge, extraction-current and energy accounting. It is not a calibrated
thruster prediction and does not model plume, erosion, charging, lifetime,
neutralizer dynamics, detailed ionization kinetics or spacecraft integration.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

EPS0 = 8.8541878128e-12
QE = 1.602176634e-19
AMU = 1.66053906660e-27
G0 = 9.80665


def main() -> int:
    ion_mass_amu = 131.293  # xenon reference ion mass
    ion_mass_kg = ion_mass_amu * AMU
    mass_flow_kg_s = 2.0e-6
    ionization_fraction = 0.70
    beam_transmission = 0.85
    accelerator_voltage_v = 1000.0
    grid_gap_m = 1.0e-3
    extraction_area_m2 = 1.0e-2
    first_ionization_energy_ev = 12.13
    ionization_energy_efficiency = 0.45

    ionized_mass_flow_kg_s = mass_flow_kg_s * ionization_fraction
    extracted_mass_flow_kg_s = ionized_mass_flow_kg_s * beam_transmission
    residual_mass_flow_kg_s = mass_flow_kg_s - extracted_mass_flow_kg_s
    ion_rate_s = ionized_mass_flow_kg_s / ion_mass_kg
    produced_ion_current_a = ion_rate_s * QE
    extracted_ion_current_a = produced_ion_current_a * beam_transmission

    exhaust_velocity_m_s = math.sqrt(2.0 * QE * accelerator_voltage_v / ion_mass_kg)
    ideal_beam_thrust_n = extracted_mass_flow_kg_s * exhaust_velocity_m_s
    ideal_specific_impulse_s = exhaust_velocity_m_s / G0
    ideal_jet_power_w = 0.5 * extracted_mass_flow_kg_s * exhaust_velocity_m_s**2
    electrical_beam_power_w = extracted_ion_current_a * accelerator_voltage_v

    child_langmuir_j_a_m2 = (
        (4.0 / 9.0)
        * EPS0
        * math.sqrt(2.0 * QE / ion_mass_kg)
        * accelerator_voltage_v**1.5
        / grid_gap_m**2
    )
    child_langmuir_current_limit_a = child_langmuir_j_a_m2 * extraction_area_m2
    extraction_loading_fraction = extracted_ion_current_a / child_langmuir_current_limit_a

    minimum_ionization_power_w = (
        ion_rate_s * first_ionization_energy_ev * QE / ionization_energy_efficiency
    )
    accounted_input_power_w = electrical_beam_power_w + minimum_ionization_power_w

    mass_balance_error_kg_s = abs(
        mass_flow_kg_s - (extracted_mass_flow_kg_s + residual_mass_flow_kg_s)
    )
    beam_power_relative_error = abs(electrical_beam_power_w - ideal_jet_power_w) / max(
        electrical_beam_power_w, 1e-12
    )

    checks = {
        "mass_conservation": mass_balance_error_kg_s <= 1e-15,
        "positive_ion_current": extracted_ion_current_a > 0.0,
        "child_langmuir_limit_not_exceeded": extraction_loading_fraction <= 1.0,
        "beam_energy_consistency": beam_power_relative_error <= 1e-12,
        "input_power_exceeds_jet_power": accounted_input_power_w >= ideal_jet_power_w,
        "bounded_ionization_fraction": 0.0 <= ionization_fraction <= 1.0,
        "bounded_beam_transmission": 0.0 <= beam_transmission <= 1.0,
    }

    report = {
        "schema": "WS-ION-EP-0D-COMPONENT-PLASMA-V1",
        "evidence_class": "SIMULATED ONLY",
        "model": "0-D xenon ionization, extraction-grid current and energy-accounting sanity model",
        "inputs": {
            "ion_mass_amu": ion_mass_amu,
            "mass_flow_kg_s": mass_flow_kg_s,
            "ionization_fraction": ionization_fraction,
            "beam_transmission": beam_transmission,
            "accelerator_voltage_v": accelerator_voltage_v,
            "grid_gap_m": grid_gap_m,
            "extraction_area_m2": extraction_area_m2,
            "first_ionization_energy_ev": first_ionization_energy_ev,
            "ionization_energy_efficiency": ionization_energy_efficiency,
        },
        "results": {
            "ionized_mass_flow_kg_s": ionized_mass_flow_kg_s,
            "extracted_mass_flow_kg_s": extracted_mass_flow_kg_s,
            "residual_mass_flow_kg_s": residual_mass_flow_kg_s,
            "produced_ion_current_a": produced_ion_current_a,
            "extracted_ion_current_a": extracted_ion_current_a,
            "child_langmuir_current_limit_a": child_langmuir_current_limit_a,
            "extraction_loading_fraction": extraction_loading_fraction,
            "ideal_exhaust_velocity_m_s": exhaust_velocity_m_s,
            "ideal_beam_thrust_n": ideal_beam_thrust_n,
            "ideal_specific_impulse_s": ideal_specific_impulse_s,
            "ideal_jet_power_w": ideal_jet_power_w,
            "electrical_beam_power_w": electrical_beam_power_w,
            "minimum_ionization_power_w": minimum_ionization_power_w,
            "accounted_input_power_w": accounted_input_power_w,
            "mass_balance_error_kg_s": mass_balance_error_kg_s,
            "beam_power_relative_error": beam_power_relative_error,
        },
        "acceptance_sanity": checks,
        "result": "PASS" if all(checks.values()) else "FAIL",
        "claims_boundary": "Closes only a bounded simulated component/plasma-model gate when retained by CI. It does not establish calibrated thrust, plasma-discharge fidelity, grid erosion, neutralization, endurance, plume/charging behavior, thermal qualification, efficiency validation or spacecraft integration."
    }

    out = Path(__file__).resolve().parent / "evidence"
    out.mkdir(parents=True, exist_ok=True)
    (out / "component-plasma-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
