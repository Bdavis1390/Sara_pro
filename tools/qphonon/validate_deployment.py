#!/usr/bin/env python3
"""Validate the WS-QPHONON V0.3 deployment profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != "WS-QPHONON-DEPLOYMENT-V0.3":
        errors.append("deployment schema mismatch")
    if data.get("claims_state") != "DEPLOYMENT_INFRASTRUCTURE_IMPLEMENTED_PHONONIC_LAB_EVIDENCE_NOT_YET_OBTAINED":
        errors.append("deployment claims state must preserve the laboratory-evidence boundary")

    state = data.get("state_store")
    if not isinstance(state, dict):
        errors.append("state_store must be an object")
    else:
        if state.get("backend") != "sqlite":
            errors.append("state store backend must remain sqlite for V0.3")
        if state.get("journal_mode") != "WAL":
            errors.append("SQLite WAL mode is required")
        if state.get("synchronous") != "FULL":
            errors.append("SQLite synchronous=FULL is required")
        if state.get("file_mode") != "0600":
            errors.append("state DB must remain owner-only")
        if state.get("durable_replay_required") is not True:
            errors.append("durable replay protection is required")
        if state.get("monotonic_event_sequence_required") is not True:
            errors.append("monotonic event sequence is required")

    attestation = data.get("approval_attestation")
    if not isinstance(attestation, dict):
        errors.append("approval_attestation must be an object")
    else:
        if attestation.get("mechanism") != "openssh_sshsig":
            errors.append("V0.3 approval verification must use OpenSSH SSHSIG")
        if attestation.get("namespace") != "worldshepherd-qphonon-approval":
            errors.append("approval signature namespace mismatch")
        if attestation.get("approved_signers_file_must_be_read_only") is not True:
            errors.append("approved signers file must be read-only")
        if attestation.get("private_key_must_not_be_present_in_container") is not True:
            errors.append("private approval keys must remain outside the guard")

    physical = data.get("physical_boundary")
    if not isinstance(physical, dict):
        errors.append("physical_boundary must be an object")
    else:
        if physical.get("hardware_actuation_endpoint_present") is not False:
            errors.append("V0.3 guard must not expose a hardware actuation endpoint")
        if physical.get("generic_qpu_evidence_counts_as_phononic_evidence") is not False:
            errors.append("generic QPU evidence must not count as phononic evidence")
        if physical.get("phononic_l3_requires_external_lab_hardware") is not True:
            errors.append("L3 must continue to require external phononic hardware")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="config/ws_qphonon_deployment_v0_3.json")
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: unable to load deployment profile: {exc}")
        return 1
    errors = validate(data) if isinstance(data, dict) else ["top-level value must be an object"]
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("WS-QPHONON deployment profile V0.3: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
