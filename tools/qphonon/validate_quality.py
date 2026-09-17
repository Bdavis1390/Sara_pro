#!/usr/bin/env python3
"""Validate the WS-QPHONON V0.2 quality/reliability profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA = "WS-QPHONON-QUALITY-V0.2"
REQUIRED_CONTROLS = {
    "IMMUTABLE_PRE_RUN_MANIFEST",
    "CONFIG_PARAMETER_ACCEPTANCE_DIGEST_BINDING",
    "EXPLICIT_EXPERIMENT_LIFECYCLE_STATE_MACHINE",
    "NO_SKIPPING_PRIME_OR_HUMAN_APPROVAL",
    "TERMINAL_COMPLETED_OR_ABORTED_OUTCOMES",
    "DETERMINISTIC_CANONICAL_SERIALIZATION",
    "VERSIONED_BACKWARD_COMPATIBLE_EVIDENCE_SCHEMAS",
    "NO_SYNTHESIS_OF_MISSING_DECISION_PARAMETERS",
    "FAIL_SAFE_DRIFT_TO_CHARACTERIZE",
    "REGRESSION_AND_ADVERSARIAL_CI",
}


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != EXPECTED_SCHEMA:
        errors.append(f"schema must equal {EXPECTED_SCHEMA}")
    if data.get("claim_boundary") != "TEN_DIMENSION_QUALITY_PROFILE_NOT_A_DEMONSTRATED_10X_PHYSICAL_PERFORMANCE_GAIN":
        errors.append("quality claim boundary must prohibit an unmeasured 10x physical-performance claim")

    controls = data.get("required_controls")
    if not isinstance(controls, list):
        errors.append("required_controls must be an array")
    else:
        present = set(controls)
        missing = REQUIRED_CONTROLS - present
        if missing:
            errors.append(f"missing quality controls: {sorted(missing)}")
        if len(present) < 10:
            errors.append("quality profile must retain at least ten independent controls")

    if data.get("minimum_control_count") != 10:
        errors.append("minimum_control_count must remain 10")
    if data.get("manifest_schema") != "WS-QPHONON-EXPERIMENT-MANIFEST-V0.2":
        errors.append("manifest schema reference is invalid")

    terminal = data.get("terminal_states")
    if not isinstance(terminal, list) or set(terminal) != {"COMPLETED", "ABORTED"}:
        errors.append("terminal states must be exactly COMPLETED and ABORTED")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        default="config/ws_qphonon_quality_v0_2.json",
    )
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: unable to load quality profile: {exc}")
        return 1
    errors = validate(data) if isinstance(data, dict) else ["top-level value must be an object"]
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("WS-QPHONON quality profile V0.2: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
