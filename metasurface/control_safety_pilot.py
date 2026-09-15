#!/usr/bin/env python3
"""Deterministic safety-envelope pilot for the adaptive metasurface contract.

This exercises command validation, saturation/rejection, thermal interlock and
configuration/sensor provenance. It does NOT simulate or validate RF field
performance, stealth, cloaking, materials, propulsion, or physical hardware.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "metasurface/adaptive_control_contract.v1.json"


class Reject(ValueError):
    pass


def load_contract() -> dict[str, Any]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def valid_timestamp(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except Exception:
        return False


def valid_digest(value: str) -> bool:
    if len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def validate_command(command: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    coupling = float(command["K_ij"])
    cc = contract["coupling_contract"]
    if not cc["K_ij_min"] <= coupling <= cc["K_ij_max"]:
        raise Reject("K_ij outside frozen signed-control range")
    if not valid_timestamp(str(command.get("sensor_timestamp_utc", ""))):
        raise Reject("missing or invalid offset-aware sensor timestamp")
    if not valid_digest(str(command.get("configuration_digest", ""))):
        raise Reject("missing or invalid configuration digest")

    temperature = float(command["temperature_k"])
    thermal_limit = float(command["temperature_limit_k"])
    if not (math.isfinite(temperature) and math.isfinite(thermal_limit) and thermal_limit > 0):
        raise Reject("invalid thermal state/limit")
    if temperature > thermal_limit:
        raise Reject("thermal interlock")

    fields = {
        "delta_phase_rad": float(command["delta_phase_rad"]),
        "delta_amplitude_fraction": float(command["delta_amplitude_fraction"]),
        "delta_permittivity_relative": float(command["delta_permittivity_relative"]),
        "delta_conductivity_s_per_m": float(command["delta_conductivity_s_per_m"]),
    }
    if not all(math.isfinite(v) for v in fields.values()):
        raise Reject("non-finite actuator request")

    b = contract["control_action"]["hard_bounds"]
    limits = {
        "delta_phase_rad": float(b["abs_delta_phase_rad_max"]),
        "delta_amplitude_fraction": float(b["abs_delta_amplitude_fraction_max"]),
        "delta_permittivity_relative": float(b["abs_delta_permittivity_relative_max"]),
        "delta_conductivity_s_per_m": float(b["abs_delta_conductivity_s_per_m_max"]),
    }
    for key, value in fields.items():
        if abs(value) > limits[key]:
            raise Reject(f"{key} outside frozen actuator envelope")

    if command.get("mode_indexing_claim") not in (None, "MATHEMATICAL_DECOMPOSITION_ONLY"):
        raise Reject("prime/composite indexing may not be promoted to a physical quantum claim")

    return {
        "decision": "AUTHORIZE_BOUNDED_COMMAND",
        "K_ij": coupling,
        "coupling_objective": "PHASE_ALIGNMENT" if coupling > 0 else "ANTI_PHASE" if coupling < 0 else "NEUTRAL",
        "command": fields,
        "configuration_digest": command["configuration_digest"],
        "sensor_timestamp_utc": command["sensor_timestamp_utc"],
        "evidence_effect": "INTERNAL_CONTROL_LOGIC_ONLY",
    }


def base_command() -> dict[str, Any]:
    return {
        "K_ij": 0.5,
        "sensor_timestamp_utc": "2026-09-04T19:00:00Z",
        "configuration_digest": hashlib.sha256(b"WS-META-CONTROL-BASE").hexdigest(),
        "temperature_k": 300.0,
        "temperature_limit_k": 350.0,
        "delta_phase_rad": 0.25,
        "delta_amplitude_fraction": 0.1,
        "delta_permittivity_relative": 0.2,
        "delta_conductivity_s_per_m": 100.0,
        "mode_indexing_claim": "MATHEMATICAL_DECOMPOSITION_ONLY",
    }


def run_pilot() -> dict[str, Any]:
    contract = load_contract()
    cases: list[tuple[str, dict[str, Any], bool]] = []

    def add(name: str, updates: dict[str, Any], should_accept: bool):
        c = base_command(); c.update(updates); cases.append((name, c, should_accept))

    add("valid_positive_coupling", {"K_ij": 0.75}, True)
    add("valid_negative_coupling", {"K_ij": -0.75}, True)
    add("valid_neutral_coupling", {"K_ij": 0.0}, True)
    add("reject_coupling_high", {"K_ij": 1.000001}, False)
    add("reject_coupling_low", {"K_ij": -1.000001}, False)
    add("reject_missing_timestamp", {"sensor_timestamp_utc": ""}, False)
    add("reject_naive_timestamp", {"sensor_timestamp_utc": "2026-09-04T19:00:00"}, False)
    add("reject_bad_digest", {"configuration_digest": "abc"}, False)
    add("reject_phase_over_limit", {"delta_phase_rad": math.pi + 1e-6}, False)
    add("reject_amplitude_over_limit", {"delta_amplitude_fraction": 1.000001}, False)
    add("reject_permittivity_over_limit", {"delta_permittivity_relative": 20.000001}, False)
    add("reject_conductivity_over_limit", {"delta_conductivity_s_per_m": 10000000.000001}, False)
    add("reject_thermal_interlock", {"temperature_k": 351.0, "temperature_limit_k": 350.0}, False)
    add("reject_nonfinite", {"delta_amplitude_fraction": float("nan")}, False)
    add("reject_quantum_promotion", {"mode_indexing_claim": "PHYSICAL_QUANTUM_NUMBER"}, False)

    outcomes = []
    exact = 0
    for name, command, should_accept in cases:
        try:
            result = validate_command(command, contract)
            accepted = True
            reason = result["decision"]
        except (Reject, KeyError, TypeError, ValueError) as exc:
            accepted = False
            reason = str(exc)
        match = accepted == should_accept
        exact += int(match)
        outcomes.append({"case": name, "expected_accept": should_accept, "accepted": accepted, "exact": match, "reason": reason})

    report = {
        "schema": "WS-ADAPTIVE-METASURFACE-CONTROL-SAFETY-PILOT-V1",
        "case_count": len(cases),
        "exact_count": exact,
        "all_exact": exact == len(cases),
        "cases": outcomes,
        "evidence_class": "INTERNAL_CONTROL_LOGIC_ONLY",
        "physical_validation_performed": False,
        "contact_authority_created": False,
    }
    if not report["all_exact"]:
        raise AssertionError(json.dumps(report, indent=2))
    return report


def main() -> None:
    report = run_pilot()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
