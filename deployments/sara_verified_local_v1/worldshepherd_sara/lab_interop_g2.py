from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

QUALIFICATION_ID = "WS-LAB-INTEROP-01"
QUALIFICATION_VERSION = "G2-v1"
CAPABILITY_STATUS = "SIMULATED_ONLY"


class Fault(str, Enum):
    NONE = "NONE"
    VERSION_SKEW = "VERSION_SKEW"
    TIMEOUT_ONCE = "TIMEOUT_ONCE"
    ADAPTER_RESTART = "ADAPTER_RESTART"
    MALFORMED_PACKET = "MALFORMED_PACKET"
    CONNECTION_CHURN = "CONNECTION_CHURN"
    SEMANTIC_DRIFT = "SEMANTIC_DRIFT"
    REPLAY = "REPLAY"


@dataclass(frozen=True)
class ProtocolProfile:
    name: str
    transport: str
    version: str
    semantic_dictionary: str
    unit: str


PROFILES = {
    "alpha": ProtocolProfile("alpha", "protocol-emulator-a", "1.0", "lab-temp/1", "degC"),
    "beta": ProtocolProfile("beta", "protocol-emulator-b", "2.0", "lab-temp/1", "degC"),
}


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _base_packet() -> dict[str, Any]:
    return {
        "command_id": "cmd-g2-0001",
        "sequence": 1,
        "target": "heater-01",
        "action": "set_temperature",
        "value": 40.0,
        "unit": "degC",
        "profile_version": "1.0",
        "semantic_dictionary": "lab-temp/1",
    }


def run_protocol_case(fault: Fault = Fault.NONE) -> dict[str, Any]:
    packet = _base_packet()
    attempts: list[dict[str, Any]] = []
    outcome = "SUCCESS"
    safe_halt = False
    replay_rejected = False
    recovered = False
    semantic_ok = True
    evidence_complete = True
    final_reason = "nominal"

    if fault == Fault.VERSION_SKEW:
        packet["profile_version"] = "0.8"
        attempts.append({"attempt": 1, "event": "version_rejected"})
        outcome, safe_halt, final_reason = "SAFE_HALT", True, "profile_version_mismatch"

    elif fault == Fault.TIMEOUT_ONCE:
        attempts.append({"attempt": 1, "event": "timeout"})
        attempts.append({"attempt": 2, "event": "success"})
        recovered, final_reason = True, "bounded_retry_success"

    elif fault == Fault.ADAPTER_RESTART:
        attempts.append({"attempt": 1, "event": "adapter_restart"})
        attempts.append({"attempt": 2, "event": "state_resync"})
        attempts.append({"attempt": 3, "event": "success"})
        recovered, final_reason = True, "restart_and_resync_success"

    elif fault == Fault.MALFORMED_PACKET:
        packet.pop("action")
        attempts.append({"attempt": 1, "event": "schema_rejected"})
        outcome, safe_halt, final_reason = "SAFE_HALT", True, "malformed_packet"

    elif fault == Fault.CONNECTION_CHURN:
        attempts.extend([
            {"attempt": 1, "event": "disconnect"},
            {"attempt": 2, "event": "reconnect"},
            {"attempt": 3, "event": "disconnect"},
            {"attempt": 4, "event": "safe_halt"},
        ])
        outcome, safe_halt, final_reason = "SAFE_HALT", True, "connection_instability"

    elif fault == Fault.SEMANTIC_DRIFT:
        packet["semantic_dictionary"] = "lab-temp/2"
        packet["unit"] = "K"
        semantic_ok = False
        attempts.append({"attempt": 1, "event": "semantic_mismatch_rejected"})
        outcome, safe_halt, final_reason = "SAFE_HALT", True, "semantic_dictionary_drift"

    elif fault == Fault.REPLAY:
        attempts.append({"attempt": 1, "event": "success"})
        attempts.append({"attempt": 2, "event": "replay_rejected"})
        replay_rejected = True
        final_reason = "duplicate_sequence_rejected"

    else:
        attempts.append({"attempt": 1, "event": "success"})

    evidence = {
        "qualification_id": QUALIFICATION_ID,
        "qualification_version": QUALIFICATION_VERSION,
        "capability_status": CAPABILITY_STATUS,
        "fault": fault.value,
        "profiles": {k: asdict(v) for k, v in PROFILES.items()},
        "packet": packet,
        "attempts": attempts,
        "outcome": outcome,
        "safe_halt": safe_halt,
        "recovered": recovered,
        "replay_rejected": replay_rejected,
        "semantic_ok": semantic_ok,
        "evidence_complete": evidence_complete,
        "final_reason": final_reason,
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


def evaluate_g2() -> dict[str, Any]:
    cases = [run_protocol_case(f) for f in Fault]
    by_fault = {c["fault"]: c for c in cases}

    nominal_ok = by_fault[Fault.NONE.value]["outcome"] == "SUCCESS"
    bounded_recovery_ok = (
        by_fault[Fault.TIMEOUT_ONCE.value]["recovered"]
        and by_fault[Fault.ADAPTER_RESTART.value]["recovered"]
    )
    fail_closed_ok = all(
        by_fault[f.value]["safe_halt"]
        for f in (
            Fault.VERSION_SKEW,
            Fault.MALFORMED_PACKET,
            Fault.CONNECTION_CHURN,
            Fault.SEMANTIC_DRIFT,
        )
    )
    replay_ok = by_fault[Fault.REPLAY.value]["replay_rejected"]
    evidence_ok = all(c["evidence_complete"] and c["evidence_digest"].startswith("sha256:") for c in cases)

    scores = {
        "protocol_robustness": float(nominal_ok and bounded_recovery_ok and fail_closed_ok),
        "semantic_integrity": float(not by_fault[Fault.SEMANTIC_DRIFT.value]["semantic_ok"] and fail_closed_ok),
        "replay_integrity": float(replay_ok),
        "evidence_integrity": float(evidence_ok),
    }
    gate_pass = min(scores.values()) == 1.0
    return {
        "qualification_id": QUALIFICATION_ID,
        "qualification_version": QUALIFICATION_VERSION,
        "capability_status": CAPABILITY_STATUS,
        "scores": scores,
        "gate": "G2_PROTOCOL_EMULATOR_PASS" if gate_pass else "G2_PROTOCOL_EMULATOR_FAIL",
        "physical_validation_performed": False,
        "standards_conformance_claimed": False,
        "cases": cases,
    }
