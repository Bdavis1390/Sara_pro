from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

QUALIFICATION_ID = "WS-LAB-INTEROP-01"
QUALIFICATION_VERSION = "G1-v2"
CAPABILITY_STATUS = "SIMULATED_ONLY"

FAULTS = (
    "F1_VERSION_DRIFT",
    "F2_DROPPED_TELEMETRY",
    "F3_STALE_STATE",
    "F4_MALFORMED_COMMAND",
    "F5_SENSOR_DISAGREEMENT",
    "F6_DEVICE_OFFLINE",
    "F7_UNIT_MISMATCH",
    "F8_TIMESTAMP_REORDER",
    "F9_REPLAY",
    "F10_PARTIAL_EXEC_COMMS_LOSS",
)


@dataclass(frozen=True)
class DeviceProfile:
    device_id: str
    adapter: str
    profile_version: str
    semantic_dictionary: str
    unit: str


PROFILES = {
    "heater": DeviceProfile("heater-01", "adapter-alpha", "1.0", "lab-temp/1", "degC"),
    "sensor": DeviceProfile("sensor-02", "adapter-beta", "2.1", "lab-temp/1", "degC"),
}


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def run_g1_case(fault: str | None = None) -> dict[str, Any]:
    if fault is not None and fault not in FAULTS:
        raise ValueError(f"unknown fault: {fault}")

    command = {
        "actor": "SSPADAWANZZ",
        "role": "admin_operator",
        "target": "heater-01",
        "action": "set_temperature",
        "value": 40.0,
        "unit": "degC",
        "command_id": "cmd-g1-0001",
        "timestamp": 100,
    }
    events: list[dict[str, Any]] = []
    decision, safe_state, reason = "ALLOW", False, "nominal"

    deny_map = {
        "F1_VERSION_DRIFT": "adapter_profile_version_mismatch",
        "F3_STALE_STATE": "stale_pre_state",
        "F4_MALFORMED_COMMAND": "schema_invalid",
        "F6_DEVICE_OFFLINE": "device_unavailable",
        "F7_UNIT_MISMATCH": "semantic_unit_mismatch",
        "F8_TIMESTAMP_REORDER": "event_order_invalid",
        "F9_REPLAY": "duplicate_command_id",
    }
    if fault in deny_map:
        decision, safe_state, reason = "DENY", True, deny_map[fault]
        if fault == "F4_MALFORMED_COMMAND":
            command["value"] = "forty"
        if fault == "F7_UNIT_MISMATCH":
            command["unit"] = "psi"

    events.append({"kind": "authorization", "decision": decision, "reason": reason, "timestamp": 101})

    if decision == "ALLOW":
        events.append({"kind": "command", "target": "heater-01", "timestamp": 102})
        if fault == "F2_DROPPED_TELEMETRY":
            events.extend([
                {"kind": "missing_data", "field": "sensor_result", "timestamp": 103},
                {"kind": "abort", "outcome": "SAFE_HALT", "timestamp": 104},
            ])
            safe_state, reason = True, "telemetry_missing"
        elif fault == "F5_SENSOR_DISAGREEMENT":
            events.extend([
                {"kind": "result", "device": "sensor-02", "value": 32.0, "unit": "degC", "timestamp": 103},
                {"kind": "alarm", "class": "sensor_disagreement", "timestamp": 104},
                {"kind": "abort", "outcome": "SAFE_HALT", "timestamp": 105},
            ])
            safe_state, reason = True, "sensor_disagreement"
        elif fault == "F10_PARTIAL_EXEC_COMMS_LOSS":
            events.extend([
                {"kind": "state", "state": "PARTIAL", "timestamp": 103},
                {"kind": "alarm", "class": "communications_loss", "timestamp": 104},
                {"kind": "abort", "outcome": "SAFE_HALT", "timestamp": 105},
            ])
            safe_state, reason = True, "partial_execution_aborted"
        else:
            events.extend([
                {"kind": "result", "device": "sensor-02", "value": 40.0, "unit": "degC", "timestamp": 103},
                {"kind": "complete", "outcome": "SUCCESS", "timestamp": 104},
            ])

    evidence = {
        "qualification_id": QUALIFICATION_ID,
        "qualification_version": QUALIFICATION_VERSION,
        "capability_status": CAPABILITY_STATUS,
        "fault": fault or "NOMINAL",
        "profiles": {k: asdict(v) for k, v in PROFILES.items()},
        "command": command,
        "events": events,
        "safe_state": safe_state,
        "reason": reason,
        "claims": {
            "physical_device_validation": False,
            "opc_ua_lads_conformance": False,
            "sila2_conformance": False,
            "production_security": False,
            "external_validation": False,
        },
    }
    evidence["configuration_digest"] = _digest(evidence["profiles"])
    evidence["evidence_digest"] = _digest(evidence)
    return evidence


def evaluate_g1() -> dict[str, Any]:
    cases = [run_g1_case(None)] + [run_g1_case(f) for f in FAULTS]
    nominal_ok = cases[0]["events"][-1].get("outcome") == "SUCCESS"
    fault_ok = all(c["safe_state"] for c in cases[1:])
    semantic_ok = all(
        run_g1_case(f)["safe_state"] for f in ("F3_STALE_STATE", "F7_UNIT_MISMATCH", "F8_TIMESTAMP_REORDER")
    )
    evidence_ok = all(c["evidence_digest"].startswith("sha256:") for c in cases)
    scores = {
        "I_C": float(nominal_ok and fault_ok),
        "I_S": float(semantic_ok),
        "I_E": float(evidence_ok),
    }
    return {
        "qualification_id": QUALIFICATION_ID,
        "qualification_version": QUALIFICATION_VERSION,
        "capability_status": CAPABILITY_STATUS,
        "scores": scores,
        "I_overall": min(scores.values()),
        "gate": "G1_SYNTHETIC_PASS" if min(scores.values()) == 1.0 else "G1_SYNTHETIC_FAIL",
        "physical_validation_performed": False,
        "standards_conformance_claimed": False,
        "cases": cases,
    }
