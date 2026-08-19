"""Bounded materials/metrology gate for WS-EM-PROPULSION quantum support.

Quantum computation/sensing may support materials characterization or metrology, but
it cannot by itself establish propulsion-force claims. This module freezes one
measurable support task, calibrated instrumentation, environmental channels and a
minimum null/control matrix while requiring the propulsion claim gate to remain
separate.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re


_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_PLACEHOLDER = ("placeholder", "todo", "tbd", "unknown", "replace-me", "<", ">")


@dataclass(frozen=True)
class NullControlCase:
    control_id: str
    control_class: str
    description: str
    configuration_digest: str
    expected_discrimination: str


@dataclass(frozen=True)
class EMMetrologyTaskRecord:
    project_id: str
    task_id: str
    support_scope: str
    material_or_apparatus_id: str
    target_observable: str
    observable_units: str
    instrument_id: str
    calibration_id: str
    calibration_certificate_digest: str
    apparatus_configuration_digest: str
    test_protocol_digest: str
    environmental_monitor_digest: str
    raw_data_artifact_digest: str
    uncertainty_budget_digest: str
    null_matrix_digest: str
    null_controls: tuple[NullControlCase, ...]
    environmental_channels: tuple[str, ...]
    repeat_target: int
    separate_propulsion_claim_gate: bool
    source_reference: str
    claim_control: str = (
        "Materials/metrology support task only. Acceptance does not establish anomalous thrust, net energy, electrogravitic coupling or propulsion performance. "
        "Any such claim requires a separate controlled force/energy evidence gate."
    )


@dataclass(frozen=True)
class EMMetrologyDecision:
    accepted: bool
    reasons: tuple[str, ...]
    gate_id: str = "WS-EM-PROPULSION-EXT-01"
    precondition_id: str = "WS-EMP-P0-MEASURABLE-SUPPORT-TASK-FROZEN"
    claim_control: str = (
        "Accepted means one bounded materials/metrology task is sufficiently specified for controlled testing. "
        "It cannot be cited as propulsion-force validation."
    )


def artifact_digest(path: str | Path) -> str:
    return "sha256:" + sha256(Path(path).read_bytes()).hexdigest()


def _is_sha(value: str) -> bool:
    return bool(_SHA256.fullmatch(value.strip().lower()))


def _placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or any(token in lowered for token in _PLACEHOLDER)


def validate_em_metrology_task(
    record: EMMetrologyTaskRecord,
    *,
    raw_data_artifact: str | Path | None = None,
) -> EMMetrologyDecision:
    reasons: list[str] = []
    if record.project_id != "WS-EM-PROPULSION":
        reasons.append("project_id must be WS-EM-PROPULSION")
    if not record.separate_propulsion_claim_gate:
        reasons.append("separate propulsion claim gate must remain enabled")
    for field in (
        "task_id", "support_scope", "material_or_apparatus_id", "target_observable", "observable_units",
        "instrument_id", "calibration_id", "source_reference",
    ):
        if _placeholder(str(getattr(record, field))):
            reasons.append(f"{field} must be concrete and non-placeholder")
    for field in (
        "calibration_certificate_digest", "apparatus_configuration_digest", "test_protocol_digest",
        "environmental_monitor_digest", "raw_data_artifact_digest", "uncertainty_budget_digest", "null_matrix_digest",
    ):
        if not _is_sha(str(getattr(record, field))):
            reasons.append(f"{field} must be a sha256 digest")
    if record.repeat_target < 3:
        reasons.append("repeat_target must be at least 3")
    if len(record.environmental_channels) < 2:
        reasons.append("at least two environmental monitoring channels are required")
    if any(_placeholder(channel) for channel in record.environmental_channels):
        reasons.append("environmental channel names must be concrete")

    if len(record.null_controls) < 3:
        reasons.append("null matrix must contain at least three distinct control cases")
    classes = set()
    ids = set()
    for case in record.null_controls:
        if _placeholder(case.control_id) or _placeholder(case.control_class) or _placeholder(case.description) or _placeholder(case.expected_discrimination):
            reasons.append("null-control fields must be concrete and non-placeholder")
        if not _is_sha(case.configuration_digest):
            reasons.append(f"null control {case.control_id} configuration_digest must be sha256")
        classes.add(case.control_class.strip().lower())
        ids.add(case.control_id)
    if len(ids) != len(record.null_controls):
        reasons.append("null control IDs must be unique")
    if len(classes) < 3:
        reasons.append("null matrix must contain at least three distinct control classes")

    if raw_data_artifact is None:
        reasons.append("actual raw metrology artifact is required")
    else:
        path = Path(raw_data_artifact)
        if not path.is_file() or path.stat().st_size == 0:
            reasons.append("raw metrology artifact must exist and be non-empty")
        elif artifact_digest(path).lower() != record.raw_data_artifact_digest.lower():
            reasons.append("raw metrology artifact digest mismatch")

    return EMMetrologyDecision(accepted=not reasons, reasons=tuple(reasons))


def em_metrology_template_as_dict() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "gate_id": "WS-EM-PROPULSION-EXT-01",
        "preconditions": [
            "WS-EMP-P0-MEASURABLE-SUPPORT-TASK-FROZEN",
            "WS-EMP-PROPULSION-CLAIM-GATE-SEPARATE"
        ],
        "record": {
            "project_id": "WS-EM-PROPULSION",
            "task_id": "<replace-me>",
            "support_scope": "<materials or metrology question; not a propulsion conclusion>",
            "material_or_apparatus_id": "<replace-me>",
            "target_observable": "<replace-me>",
            "observable_units": "<replace-me>",
            "instrument_id": "<replace-me>",
            "calibration_id": "<replace-me>",
            "calibration_certificate_digest": "<sha256>",
            "apparatus_configuration_digest": "<sha256>",
            "test_protocol_digest": "<sha256>",
            "environmental_monitor_digest": "<sha256>",
            "raw_data_artifact_digest": "<sha256>",
            "uncertainty_budget_digest": "<sha256>",
            "null_matrix_digest": "<sha256>",
            "null_controls": [
                {"control_class": "power_or_excitation_off", "description": "<define applicability>"},
                {"control_class": "sham_or_dummy_load", "description": "<define applicability>"},
                {"control_class": "orientation_or_coupling_reversal", "description": "<define applicability>"}
            ],
            "environmental_channels": ["<channel-1>", "<channel-2>"],
            "repeat_target": 3,
            "separate_propulsion_claim_gate": True,
            "source_reference": "<replace-me>"
        },
        "claim_control": (
            "Template only. Control classes must be tailored to the actual apparatus and may require additional thermal, vibration, cable-force, magnetic, electrostatic, airflow, acoustic or other controls. "
            "Passing this bounded support gate cannot be cited as proof of propulsion or net energy."
        )
    }
