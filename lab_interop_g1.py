"""WS-LAB-INTEROP-01 G1 deterministic synthetic interoperability harness.

SIMULATED_ONLY. This module does not implement OPC UA LADS, SiLA 2, or physical-device I/O.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Any

QUALIFICATION_ID = "WS-LAB-INTEROP-01"
QUALIFICATION_VERSION = "G1-v1"
CLAIM_STATE = "SIMULATED_ONLY"


@dataclass(frozen=True)
class Device:
    device_id: str
    adapter: str
    profile_version: str
    semantic_version: str
    unit: str = "degC"


DEVICES = {
    "heater": Device("heater-01", "adapter-alpha", "1.0", "lab-temp/1", "degC"),
    "sensor": Device("sensor-02", "adapter-beta", "2.1", "lab-temp/1", "degC"),
}

FAULTS = (
    "F1_VERSION_DRIFT", "F2_DROPPED_TELEMETRY", "F3_STALE_STATE",
    "F4_MALFORMED_COMMAND", "F5_SENSOR_DISAGREEMENT", "F6_DEVICE_OFFLINE",
    "F7_UNIT_MISMATCH", "F8_TIMESTAMP_REORDER", "F9_REPLAY",
    "F10_PARTIAL_EXEC_COMMS_LOSS",
)


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def run_case(fault: str | None = None) -> dict[str, Any]:
    """Run one deterministic bounded protocol and return reconstruction evidence."""
    if fault is not None and fault not in FAULTS:
        raise ValueError(f"unknown fault: {fault}")

    command = {"actor": "SSPADAWANZZ", "role": "admin_operator",
               "target": "heater", "action": "set_temperature", "value": 40.0, "unit": "degC",
               "command_id": "cmd-0001", "timestamp": 100}
    events: list[dict[str, Any]] = []
    decision = "ALLOW"
    safe_state = False
    reason = "nominal"

    if fault == "F4_MALFORMED_COMMAND":
        command["value"] = "forty"
        decision, safe_state, reason = "DENY", True, "schema_invalid"
    elif fault == "F7_UNIT_MISMATCH":
        command["unit"] = "psi"
        decision, safe_state, reason = "DENY", True, "semantic_unit_mismatch"
    elif fault == "F9_REPLAY":
        decision, safe_state, reason = "DENY", True, "duplicate_command_id"
    elif fault == "F1_VERSION_DRIFT":
        decision, safe_state, reason = "DENY", True, "adapter_profile_version_mismatch"
    elif fault == "F3_STALE_STATE":
        decision, safe_state, reason = "DENY", True, "stale_pre_state"
    elif fault == "F6_DEVICE_OFFLINE":
        decision, safe_state, reason = "DENY", True, "device_unavailable"
    elif fault == "F8_TIMESTAMP_REORDER":
        decision, safe_state, reason = "DENY", True, "event_order_invalid"

    events.append({"kind": "authorization", "decision": decision, "reason": reason,
                   "command_id": command["command_id"], "timestamp": 101})

    if decision == "ALLOW":
        events.append({"kind": "command", "target": DEVICES["heater"].device_id,
                       "normalized": command, "timestamp": 102})
        if fault == "F10_PARTIAL_EXEC_COMMS_LOSS":
            events.append({"kind": "state", "state": "PARTIAL", "timestamp": 103})
            events.append({"kind": "alarm", "class": "communications_loss", "timestamp": 104})
            events.append({"kind": "abort", "outcome": "SAFE_HALT", "timestamp": 105})
            safe_state, reason = True, "partial_execution_aborted"
        elif fault == "F2_DROPPED_TELEMETRY":
            events.append({"kind": "missing_data", "field": "sensor_result", "timestamp": 103})
            events.append({"kind": "abort", "outcome": "SAFE_HALT", "timestamp": 104})
            safe_state, reason = True, "telemetry_missing"
        elif fault == "F5_SENSOR_DISAGREEMENT":
            events.append({"kind": "result", "device": "sensor-02", "value": 32.0, "unit": "degC", "timestamp": 103})
            events.append({"kind": "alarm", "class": "sensor_disagreement", "timestamp": 104})
            events.append({"kind": "abort", "outcome": "SAFE_HALT", "timestamp": 105})
            safe_state, reason = True, "sensor_disagreement"
        else:
            events.append({"kind": "result", "device": "sensor-02", "value": 40.0, "unit": "degC", "timestamp": 103})
            events.append({"kind": "complete", "outcome": "SUCCESS", "timestamp": 104})

    evidence = {
        "qualification_id": QUALIFICATION_ID,
        "qualification_version": QUALIFICATION_VERSION,
        "claim_state": CLAIM_STATE,
        "fault": fault or "NOMINAL",
        "config": {k: asdict(v) for k, v in DEVICES.items()},
        "command": command,
        "events": events,
        "safe_state": safe_state,
        "reason": reason,
        "claims": {
            "physical_device_validation": False,
            "opc_ua_lads_conformance": False,
            "sila2_conformance": False,
            "production_security": False,
        },
    }
    evidence["configuration_digest"] = _digest(evidence["config"])
    evidence["evidence_digest"] = _digest(evidence)
    return evidence


def evaluate() -> dict[str, Any]:
    cases = [run_case(None)] + [run_case(f) for f in FAULTS]
    nominal_ok = cases[0]["events"][-1].get("outcome") == "SUCCESS"
    fault_ok = all(c["safe_state"] for c in cases[1:])
    reconstruction_ok = all(c.get("evidence_digest") and c.get("configuration_digest") and c["events"] for c in cases)
    scores = {
        "I_C": 1.0 if nominal_ok and fault_ok else 0.0,
        "I_S": 1.0 if all(run_case(f)["safe_state"] for f in ("F3_STALE_STATE", "F7_UNIT_MISMATCH", "F8_TIMESTAMP_REORDER")) else 0.0,
        "I_E": 1.0 if reconstruction_ok else 0.0,
    }
    return {
        "qualification_id": QUALIFICATION_ID,
        "qualification_version": QUALIFICATION_VERSION,
        "claim_state": CLAIM_STATE,
        "cases": cases,
        "scores": scores,
        "I_overall": min(scores.values()),
        "gate": "G1_SYNTHETIC_PASS" if min(scores.values()) == 1.0 else "G1_SYNTHETIC_FAIL",
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
