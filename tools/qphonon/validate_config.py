#!/usr/bin/env python3
"""Validate the WS-QPHONON L2 architecture configuration.

This validator intentionally checks governance and claims boundaries in addition to
basic structure. It does not validate quantum-physics performance or promote any
physical capability.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA = "WS-QPHONON-L2-V0.1"
EXPECTED_LEVEL = "L2_ARCHITECTURE"
EXPECTED_STATUS = "ARCHITECTURE_INTEGRATED_PHYSICAL_CAPABILITY_NOT_CLAIMED"
REQUIRED_GOVERNANCE_ROLES = {
    "sara_role",
    "prime_role",
    "echo_role",
    "overwatch_role",
    "pre_role",
    "doctrine",
}
REQUIRED_ECHO_FIELDS = {
    "raw_data_hash",
    "model_version",
    "prior",
    "posterior",
    "experiment_proposed",
    "expected_information_gain",
    "prime_decision",
    "control_waveform_or_parameters",
    "environmental_state",
    "measurement_result",
    "model_discrepancy",
    "claims_state",
}
REQUIRED_L3_GATES = {
    "real_external_quantum_hardware_used",
    "worldshepherd_control_or_governance_layer_used_in_experiment",
    "reproducible_result_observed",
    "holdout_prediction_passed",
    "uncertainty_bounds_reported",
    "full_echo_provenance_recorded",
    "independent_human_or_partner_can_reproduce_result",
}


def _require_mapping(value: Any, name: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{name} must be an object")
        return {}
    return value


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if data.get("schema") != EXPECTED_SCHEMA:
        errors.append(f"schema must equal {EXPECTED_SCHEMA}")
    if data.get("integration_level") != EXPECTED_LEVEL:
        errors.append(f"integration_level must equal {EXPECTED_LEVEL}")
    if data.get("status") != EXPECTED_STATUS:
        errors.append(f"status must equal {EXPECTED_STATUS}")

    boundary = data.get("claims_boundary")
    if not isinstance(boundary, str) or "No Worldshepherd quantum-hardware" not in boundary:
        errors.append("claims_boundary must explicitly deny a current Worldshepherd quantum-hardware claim")

    physical = _require_mapping(data.get("physical_baseline"), "physical_baseline", errors)
    if physical.get("worldshepherd_owned_quantum_hardware") is not False:
        errors.append("physical_baseline.worldshepherd_owned_quantum_hardware must be false at L2")
    if physical.get("evidence_state") != "EXTERNAL_LITERATURE_AND_EXTERNAL_HARDWARE_ONLY":
        errors.append("physical_baseline.evidence_state must remain external-only at L2")

    governance = _require_mapping(data.get("governance"), "governance", errors)
    missing_roles = REQUIRED_GOVERNANCE_ROLES - governance.keys()
    if missing_roles:
        errors.append(f"governance missing roles: {sorted(missing_roles)}")

    params = _require_mapping(data.get("parameter_registry"), "parameter_registry", errors)
    temperature = _require_mapping(params.get("device_temperature_k"), "parameter_registry.device_temperature_k", errors)
    preferred = temperature.get("preferred_max")
    hard_max = temperature.get("hard_screen_max")
    uncertainty = temperature.get("authorization_uncertainty_k_max")
    if not isinstance(preferred, (int, float)) or preferred > 0.100:
        errors.append("preferred device temperature must be <= 0.100 K")
    if not isinstance(hard_max, (int, float)) or hard_max > 0.125:
        errors.append("hard-screen device temperature must be <= 0.125 K")
    if not isinstance(uncertainty, (int, float)) or uncertainty > 0.005:
        errors.append("authorization temperature uncertainty must be <= 0.005 K")

    gamma = _require_mapping(params.get("gamma_eff_hz"), "parameter_registry.gamma_eff_hz", errors)
    if gamma.get("must_not_be_silently_equated_to_kappa_m") is not True:
        errors.append("gamma_eff_hz must remain distinct from intrinsic kappa_m")

    prime = _require_mapping(data.get("prime_authorization"), "prime_authorization", errors)
    violation_probability = prime.get("posterior_violation_probability_max")
    if not isinstance(violation_probability, (int, float)) or not 0 < violation_probability <= 0.01:
        errors.append("posterior_violation_probability_max must be in (0, 0.01]")

    coherent = _require_mapping(
        prime.get("coherent_transfer_attempt_requires"),
        "prime_authorization.coherent_transfer_attempt_requires",
        errors,
    )
    if not isinstance(coherent.get("cooperativity_ct2_min"), (int, float)) or coherent.get("cooperativity_ct2_min", 0) < 1.0:
        errors.append("coherent transfer must require C_T2 >= 1")
    if coherent.get("parameter_confidence_gates_pass") is not True:
        errors.append("coherent transfer must require parameter-confidence gates")
    if coherent.get("model_holdout_validation_pass") is not True:
        errors.append("coherent transfer must require holdout validation")

    bayes = _require_mapping(data.get("bayesian_identification"), "bayesian_identification", errors)
    if bayes.get("transfer_trace_alone_is_sufficient") is not False:
        errors.append("transfer trace alone must remain insufficient for parameter identification")
    if bayes.get("model_discrepancy_is_first_class_state") is not True:
        errors.append("model discrepancy must be a first-class state")

    echo_fields = data.get("echo_record_required_fields")
    if not isinstance(echo_fields, list):
        errors.append("echo_record_required_fields must be an array")
    else:
        missing_echo = REQUIRED_ECHO_FIELDS - set(echo_fields)
        if missing_echo:
            errors.append(f"ECHO record missing required fields: {sorted(missing_echo)}")

    overwatch = _require_mapping(data.get("overwatch"), "overwatch", errors)
    if overwatch.get("fallback_mode") != "CHARACTERIZE":
        errors.append("OVERWATCH fallback mode must be CHARACTERIZE")
    if overwatch.get("no_blind_compensation") is not True:
        errors.append("OVERWATCH must prohibit blind compensation")

    promotions = _require_mapping(data.get("promotion_gates"), "promotion_gates", errors)
    l3 = promotions.get("L3_CAPABILITY_INTEGRATION")
    if not isinstance(l3, list):
        errors.append("L3_CAPABILITY_INTEGRATION must be an array")
    else:
        missing_l3 = REQUIRED_L3_GATES - set(l3)
        if missing_l3:
            errors.append(f"L3 gate missing requirements: {sorted(missing_l3)}")

    return errors


def validate_file(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"unable to load config: {exc}"]
    if not isinstance(data, dict):
        return ["top-level JSON value must be an object"]
    return validate(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        default="config/ws_qphonon_l2_v0_1.json",
        help="path to WS-QPHONON JSON config",
    )
    args = parser.parse_args()

    errors = validate_file(Path(args.path))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("WS-QPHONON L2 config: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
