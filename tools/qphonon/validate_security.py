#!/usr/bin/env python3
"""Validate the WS-QPHONON V0.2 security profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA = "WS-QPHONON-SECURITY-V0.2"
REQUIRED_CONTROLS = {
    "STRICT_ECHO_TOP_LEVEL_SCHEMA",
    "SHA256_INTEGRITY_FORMAT",
    "CANONICAL_EVENT_DIGEST",
    "PREVIOUS_EVENT_CHAIN_LINK",
    "EVENT_FRESHNESS_GATE",
    "EVENT_ID_REPLAY_REJECTION",
    "CONFIG_DIGEST_BINDING",
    "FINITE_AND_RANGED_NUMERIC_INPUTS",
    "SEPARATE_HUMAN_EXECUTION_APPROVAL",
    "PINNED_LEAST_PRIVILEGE_CI",
}


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != EXPECTED_SCHEMA:
        errors.append(f"schema must equal {EXPECTED_SCHEMA}")
    if data.get("claim_boundary") != "TEN_CONTROL_HARDENING_PROFILE_NOT_A_DEMONSTRATED_10X_RISK_REDUCTION":
        errors.append("claim boundary must prohibit an unmeasured 10x risk-reduction claim")

    controls = data.get("required_controls")
    if not isinstance(controls, list):
        errors.append("required_controls must be an array")
    else:
        present = set(controls)
        missing = REQUIRED_CONTROLS - present
        if missing:
            errors.append(f"missing hardening controls: {sorted(missing)}")
        if len(present) < 10:
            errors.append("security profile must retain at least ten independent controls")

    freshness = data.get("event_freshness_seconds_max")
    skew = data.get("future_clock_skew_seconds_max")
    lifetime = data.get("approval_lifetime_seconds_max")
    mutation_min = data.get("minimum_adversarial_mutation_cases")
    if not isinstance(freshness, int) or isinstance(freshness, bool) or not 1 <= freshness <= 300:
        errors.append("event freshness window must be an integer in [1, 300]")
    if not isinstance(skew, int) or isinstance(skew, bool) or not 0 <= skew <= 30:
        errors.append("future clock skew must be an integer in [0, 30]")
    if not isinstance(lifetime, int) or isinstance(lifetime, bool) or not 1 <= lifetime <= 900:
        errors.append("approval lifetime must be an integer in [1, 900]")
    if not isinstance(mutation_min, int) or isinstance(mutation_min, bool) or mutation_min < 100:
        errors.append("minimum adversarial mutation cases must remain >= 100")

    execution = data.get("execution_policy")
    if not isinstance(execution, dict):
        errors.append("execution_policy must be an object")
    else:
        if execution.get("prime_pass_disposition") != "READY_FOR_HUMAN_APPROVAL":
            errors.append("PRIME pass may only advance to READY_FOR_HUMAN_APPROVAL")
        if execution.get("approval_attestation_must_be_verified_externally") is not True:
            errors.append("external approval attestation verification must remain required")
        if execution.get("one_time_approval_id_required") is not True:
            errors.append("one-time approval IDs must remain required")
        if execution.get("approval_binds_experiment_digest") is not True:
            errors.append("approval must remain bound to experiment digest")
        if execution.get("approval_binds_config_digest") is not True:
            errors.append("approval must remain bound to config digest")

    supply = data.get("supply_chain")
    if not isinstance(supply, dict):
        errors.append("supply_chain must be an object")
    else:
        if supply.get("github_actions_must_be_commit_pinned") is not True:
            errors.append("GitHub Actions must remain commit-pinned")
        if supply.get("checkout_persist_credentials") is not False:
            errors.append("checkout credentials must not persist")
        if supply.get("workflow_permissions") != "contents_read_only":
            errors.append("QPHONON CI must remain contents-read-only")
        if supply.get("no_secrets_required_by_qphonon_ci") is not True:
            errors.append("QPHONON CI must not require secrets")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        default="config/ws_qphonon_security_v0_2.json",
    )
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: unable to load security profile: {exc}")
        return 1
    errors = validate(data) if isinstance(data, dict) else ["top-level value must be an object"]
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("WS-QPHONON security profile V0.2: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
