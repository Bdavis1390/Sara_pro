from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

QUALIFICATION_ID = "WS-LAB-INTEROP-01"
QUALIFICATION_VERSION = "G3-R0"
CAPABILITY_STATUS = "PRE_PHYSICAL_HIL_READINESS"


@dataclass(frozen=True)
class HardwareChannelSpec:
    channel_id: str
    device_id: str
    interface: str
    direction: str
    quantity: str
    unit: str
    min_value: float
    max_value: float
    safe_value: float
    calibration_id: str
    calibration_valid: bool
    clock_source: str


@dataclass(frozen=True)
class UncertaintyBudget:
    instrument_accuracy: float
    repeatability: float
    quantization: float
    timing_equivalent: float

    @property
    def rss(self) -> float:
        return (
            self.instrument_accuracy ** 2
            + self.repeatability ** 2
            + self.quantization ** 2
            + self.timing_equivalent ** 2
        ) ** 0.5


@dataclass(frozen=True)
class SafetyEnvelope:
    command_min: float
    command_max: float
    hard_abort_low: float
    hard_abort_high: float
    requires_estop: bool = True


DEFAULT_CHANNELS = (
    HardwareChannelSpec(
        channel_id="AO-HEATER-01",
        device_id="heater-01",
        interface="HIL-analog-out",
        direction="output",
        quantity="temperature_setpoint",
        unit="degC",
        min_value=20.0,
        max_value=45.0,
        safe_value=20.0,
        calibration_id="CAL-AO-001",
        calibration_valid=True,
        clock_source="monotonic-test-clock",
    ),
    HardwareChannelSpec(
        channel_id="AI-TEMP-02",
        device_id="sensor-02",
        interface="HIL-analog-in",
        direction="input",
        quantity="temperature",
        unit="degC",
        min_value=0.0,
        max_value=80.0,
        safe_value=20.0,
        calibration_id="CAL-AI-002",
        calibration_valid=True,
        clock_source="monotonic-test-clock",
    ),
)

DEFAULT_ENVELOPE = SafetyEnvelope(
    command_min=20.0,
    command_max=45.0,
    hard_abort_low=5.0,
    hard_abort_high=60.0,
)

DEFAULT_UNCERTAINTY = UncertaintyBudget(
    instrument_accuracy=0.20,
    repeatability=0.10,
    quantization=0.05,
    timing_equivalent=0.05,
)


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def bench_manifest(
    *,
    channels: tuple[HardwareChannelSpec, ...] = DEFAULT_CHANNELS,
    envelope: SafetyEnvelope = DEFAULT_ENVELOPE,
    uncertainty: UncertaintyBudget = DEFAULT_UNCERTAINTY,
) -> dict[str, Any]:
    manifest = {
        "qualification_id": QUALIFICATION_ID,
        "qualification_version": QUALIFICATION_VERSION,
        "capability_status": CAPABILITY_STATUS,
        "channels": [asdict(c) for c in channels],
        "safety_envelope": asdict(envelope),
        "uncertainty_budget": {
            **asdict(uncertainty),
            "rss": uncertainty.rss,
        },
        "required_controls": {
            "human_estop": True,
            "fail_safe_default": True,
            "raw_measurement_retention": True,
            "normalized_measurement_retention": True,
            "calibration_traceability": True,
            "clock_source_recorded": True,
            "configuration_digest_required": True,
            "evidence_digest_required": True,
        },
        "claims": {
            "physical_device_validation": False,
            "hil_validation_completed": False,
            "opc_ua_lads_conformance": False,
            "sila2_conformance": False,
            "production_security": False,
            "external_validation": False,
        },
    }
    manifest["configuration_digest"] = _digest(manifest)
    return manifest


def validate_command(
    value: float,
    *,
    envelope: SafetyEnvelope = DEFAULT_ENVELOPE,
    estop_engaged: bool = False,
) -> dict[str, Any]:
    if estop_engaged:
        return {"decision": "DENY", "reason": "estop_engaged", "safe_value": envelope.command_min}
    if value < envelope.command_min or value > envelope.command_max:
        return {"decision": "DENY", "reason": "outside_command_envelope", "safe_value": envelope.command_min}
    return {"decision": "ALLOW", "reason": "within_envelope", "safe_value": envelope.command_min}


def assess_measurement(
    raw_value: float,
    *,
    normalized_value: float,
    channel: HardwareChannelSpec = DEFAULT_CHANNELS[1],
    envelope: SafetyEnvelope = DEFAULT_ENVELOPE,
    uncertainty: UncertaintyBudget = DEFAULT_UNCERTAINTY,
) -> dict[str, Any]:
    calibration_ok = channel.calibration_valid
    agreement_error = abs(raw_value - normalized_value)
    normalization_ok = agreement_error <= max(uncertainty.rss, 1e-12)
    hard_abort = raw_value < envelope.hard_abort_low or raw_value > envelope.hard_abort_high
    return {
        "raw_value": raw_value,
        "normalized_value": normalized_value,
        "unit": channel.unit,
        "calibration_id": channel.calibration_id,
        "calibration_ok": calibration_ok,
        "uncertainty_rss": uncertainty.rss,
        "normalization_error": agreement_error,
        "normalization_ok": normalization_ok,
        "hard_abort": hard_abort,
        "clock_source": channel.clock_source,
    }


def inject_readiness_fault(name: str) -> dict[str, Any]:
    manifest = bench_manifest()

    if name == "expired_calibration":
        manifest["channels"][1]["calibration_valid"] = False
        disposition = "BLOCK_PHYSICAL_RUN"
    elif name == "missing_estop":
        manifest["required_controls"]["human_estop"] = False
        disposition = "BLOCK_PHYSICAL_RUN"
    elif name == "missing_clock":
        manifest["channels"][1]["clock_source"] = ""
        disposition = "BLOCK_PHYSICAL_RUN"
    elif name == "missing_raw_retention":
        manifest["required_controls"]["raw_measurement_retention"] = False
        disposition = "BLOCK_PHYSICAL_RUN"
    elif name == "unsafe_default":
        manifest["channels"][0]["safe_value"] = 100.0
        disposition = "BLOCK_PHYSICAL_RUN"
    else:
        raise ValueError(f"unknown readiness fault: {name}")

    manifest["fault"] = name
    manifest["disposition"] = disposition
    manifest["evidence_digest"] = _digest(manifest)
    return manifest


def evaluate_g3_readiness() -> dict[str, Any]:
    manifest = bench_manifest()
    channels = manifest["channels"]
    controls = manifest["required_controls"]

    two_distinct_devices = len({c["device_id"] for c in channels}) >= 2
    calibrated = all(c["calibration_valid"] for c in channels)
    clocks = all(bool(c["clock_source"]) for c in channels)
    safe_defaults = all(c["min_value"] <= c["safe_value"] <= c["max_value"] for c in channels)
    controls_ok = all(controls.values())
    uncertainty_ok = manifest["uncertainty_budget"]["rss"] > 0.0

    fault_names = (
        "expired_calibration",
        "missing_estop",
        "missing_clock",
        "missing_raw_retention",
        "unsafe_default",
    )
    fail_closed = all(inject_readiness_fault(name)["disposition"] == "BLOCK_PHYSICAL_RUN" for name in fault_names)

    checks = {
        "two_distinct_devices": two_distinct_devices,
        "calibration_traceability": calibrated,
        "clock_traceability": clocks,
        "safe_defaults": safe_defaults,
        "required_controls": controls_ok,
        "uncertainty_budget": uncertainty_ok,
        "readiness_faults_fail_closed": fail_closed,
    }
    ready = all(checks.values())
    return {
        "qualification_id": QUALIFICATION_ID,
        "qualification_version": QUALIFICATION_VERSION,
        "capability_status": CAPABILITY_STATUS,
        "checks": checks,
        "readiness_gate": "G3_READY_FOR_PHYSICAL_BENCH" if ready else "G3_NOT_READY",
        "physical_validation_performed": False,
        "manifest": manifest,
    }
