from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from model import FlexRequest
from partner_bundle import (
    MeasurementBoundary,
    PartnerEvidenceContext,
    build_partner_replay_payload,
)
from replay import replay_payload
from trace import TracePoint


SCHEMA_VERSION = "ws-dcar.partner-event/v0.1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized.startswith("replace-with-") or normalized.startswith("replace_with_")


def _require_fields(
    mapping: Mapping[str, Any], fields: tuple[str, ...], object_name: str
) -> None:
    missing = [field for field in fields if field not in mapping]
    if missing:
        raise ValueError(
            f"{object_name} missing required field(s): {', '.join(missing)}"
        )


def _required_str(mapping: Mapping[str, Any], field: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    normalized = value.strip()
    if _is_placeholder(normalized):
        raise ValueError(f"{field} still contains a template placeholder")
    return normalized


def _optional_str(mapping: Mapping[str, Any], field: str) -> str | None:
    value = mapping.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be null or a non-empty string")
    normalized = value.strip()
    if _is_placeholder(normalized):
        raise ValueError(f"{field} still contains a template placeholder")
    return normalized


def _required_bool(mapping: Mapping[str, Any], field: str) -> bool:
    value = mapping.get(field)
    if type(value) is not bool:
        raise ValueError(f"{field} must be an explicit boolean")
    return value


def _required_number(mapping: Mapping[str, Any], field: str) -> float:
    value = mapping.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    return float(value)


def _optional_number(
    mapping: Mapping[str, Any], field: str, default: float = 0.0
) -> float:
    if field not in mapping:
        return default
    return _required_number(mapping, field)


def _nullable_number(mapping: Mapping[str, Any], field: str) -> float | None:
    value = mapping.get(field)
    if value is None:
        return None
    return _required_number(mapping, field)


def _normalize_source_objects(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("source_objects must contain at least one source object")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        obj = _mapping(item, f"source_objects[{index}]")
        _require_fields(
            obj,
            ("object_id", "role", "raw_or_derived", "sha256", "media_type"),
            f"source_objects[{index}]",
        )
        object_id = _required_str(obj, "object_id")
        role = _required_str(obj, "role")
        raw_or_derived = obj.get("raw_or_derived", "raw")
        if raw_or_derived not in {"raw", "derived"}:
            raise ValueError(
                f"source_objects[{index}].raw_or_derived must be 'raw' or 'derived'"
            )
        sha256 = _optional_str(obj, "sha256")
        if sha256 is not None and not _SHA256_RE.fullmatch(sha256):
            raise ValueError(
                f"source_objects[{index}].sha256 must be 64 lowercase hex characters"
            )
        media_type = _optional_str(obj, "media_type")
        normalized.append(
            {
                "object_id": object_id,
                "role": role,
                "raw_or_derived": raw_or_derived,
                "sha256": sha256,
                "media_type": media_type,
            }
        )
    return normalized


def _normalize_points(value: object) -> list[TracePoint]:
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError("points must contain at least two measurements")

    points: list[TracePoint] = []
    for index, item in enumerate(value):
        point = _mapping(item, f"points[{index}]")
        telemetry_fresh = _required_bool(point, "telemetry_fresh")
        meter_provenance_valid = _required_bool(point, "meter_provenance_valid")
        configuration_id = _required_str(point, "configuration_id")
        meter_id = _required_str(point, "meter_id")

        points.append(
            TracePoint(
                timestamp_s=_required_number(point, "timestamp_s"),
                grid_import_mw=_required_number(point, "measured_power_mw"),
                workload_pause_mw=_optional_number(point, "workload_pause_mw"),
                workload_migration_mw=_optional_number(point, "workload_migration_mw"),
                battery_discharge_mw=_optional_number(point, "battery_discharge_mw"),
                onsite_generation_mw=_optional_number(point, "onsite_generation_mw"),
                hvac_reduction_mw=_optional_number(point, "hvac_reduction_mw"),
                telemetry_fresh=telemetry_fresh,
                meter_provenance_valid=meter_provenance_valid,
                configuration_id=configuration_id,
                meter_id=meter_id,
            )
        )
    return points


def build_partner_intake_payload(bundle: dict[str, Any]) -> dict[str, Any]:
    """Translate a partner-facing event bundle into the internal replay contract.

    The external format uses `measured_power_mw` and
    `max_measured_power_mw` so a device/node/cluster measurement is not
    mislabeled as a grid-boundary quantity. The existing internal verifier
    retains its historical field names, while provenance records the mapping
    and the actual measurement boundary.
    """

    if bundle.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must equal {SCHEMA_VERSION!r}")

    request_data = _mapping(bundle.get("request"), "request")
    request = FlexRequest(
        requested_reduction_mw=_required_number(
            request_data, "requested_reduction_mw"
        ),
        response_deadline_s=_required_number(request_data, "response_deadline_s"),
        required_duration_s=_required_number(request_data, "required_duration_s"),
        max_grid_import_mw=_required_number(
            request_data, "max_measured_power_mw"
        ),
    )

    context_data = _mapping(bundle.get("partner_context"), "partner_context")
    _require_fields(
        context_data,
        (
            "source_organization",
            "project_or_dataset_id",
            "measurement_boundary",
            "request_id",
            "authorization_record_id",
            "clock_source",
            "baseline_method",
            "configuration_id",
            "meter_id",
            "authorized",
            "request_provenance_valid",
            "authorization_evidence_valid",
            "clocks_synchronized",
            "baseline_valid",
            "configuration_custody_valid",
            "transformation_history",
            "limitations",
        ),
        "partner_context",
    )
    try:
        boundary = MeasurementBoundary(
            _required_str(context_data, "measurement_boundary")
        )
    except ValueError as exc:
        raise ValueError("measurement_boundary is not a supported boundary") from exc

    transformation_history = context_data.get("transformation_history", [])
    limitations = context_data.get("limitations", [])
    if not isinstance(transformation_history, list) or not all(
        isinstance(item, str) and item.strip() for item in transformation_history
    ):
        raise ValueError("transformation_history must be a list of non-empty strings")
    if not isinstance(limitations, list) or not all(
        isinstance(item, str) and item.strip() for item in limitations
    ):
        raise ValueError("limitations must be a list of non-empty strings")

    context = PartnerEvidenceContext(
        source_organization=_required_str(context_data, "source_organization"),
        project_or_dataset_id=_required_str(
            context_data, "project_or_dataset_id"
        ),
        measurement_boundary=boundary,
        request_id=_optional_str(context_data, "request_id"),
        authorization_record_id=_optional_str(
            context_data, "authorization_record_id"
        ),
        clock_source=_optional_str(context_data, "clock_source"),
        baseline_method=_optional_str(context_data, "baseline_method"),
        configuration_id=_optional_str(context_data, "configuration_id"),
        meter_id=_optional_str(context_data, "meter_id"),
        authorized=_required_bool(context_data, "authorized"),
        request_provenance_valid=_required_bool(
            context_data, "request_provenance_valid"
        ),
        authorization_evidence_valid=_required_bool(
            context_data, "authorization_evidence_valid"
        ),
        clocks_synchronized=_required_bool(context_data, "clocks_synchronized"),
        baseline_valid=_required_bool(context_data, "baseline_valid"),
        configuration_custody_valid=_required_bool(
            context_data, "configuration_custody_valid"
        ),
        transformation_history=tuple(item.strip() for item in transformation_history),
        limitations=tuple(item.strip() for item in limitations),
    )

    points = _normalize_points(bundle.get("points"))
    source_objects = _normalize_source_objects(bundle.get("source_objects"))
    baseline_mw = _required_number(bundle, "baseline_mw")

    custody_data = _mapping(bundle.get("custody"), "custody")
    _require_fields(
        custody_data,
        (
            "event_start_utc",
            "event_end_utc",
            "timezone",
            "baseline_uncertainty_mw",
            "transformation_tool",
            "transformation_tool_version",
            "redaction_statement",
        ),
        "custody",
    )
    partner_custody = {
        "event_start_utc": _optional_str(custody_data, "event_start_utc"),
        "event_end_utc": _optional_str(custody_data, "event_end_utc"),
        "timezone": _optional_str(custody_data, "timezone"),
        "baseline_uncertainty_mw": _nullable_number(
            custody_data, "baseline_uncertainty_mw"
        ),
        "transformation_tool": _optional_str(
            custody_data, "transformation_tool"
        ),
        "transformation_tool_version": _optional_str(
            custody_data, "transformation_tool_version"
        ),
        "redaction_statement": _required_str(
            custody_data, "redaction_statement"
        ),
    }

    payload = build_partner_replay_payload(
        request,
        baseline_mw,
        points,
        context,
        max_gap_s=_optional_number(bundle, "max_gap_s", 300.0),
        energy_mismatch_tolerance_mwh=_optional_number(
            bundle, "energy_mismatch_tolerance_mwh", 0.25
        ),
    )

    provenance = payload.setdefault("provenance", {})
    provenance.update(
        {
            "partner_intake_schema_version": SCHEMA_VERSION,
            "partner_manifest_canonical_sha256": _canonical_sha256(bundle),
            "partner_measurement_field": "measured_power_mw",
            "internal_trace_field": "grid_import_mw",
            "semantic_mapping": (
                "measured_power_mw is interpreted only at the declared "
                "measurement_boundary"
            ),
            "partner_custody": partner_custody,
        }
    )

    partner_supplied = bundle.get("auxiliary_evidence")
    if partner_supplied is not None and not isinstance(partner_supplied, dict):
        raise ValueError("auxiliary_evidence must be an object when supplied")

    payload["auxiliary_evidence"] = {
        "partner_intake": {
            "schema_version": SCHEMA_VERSION,
            "source_objects": source_objects,
        },
        "partner_supplied": partner_supplied,
    }
    return payload


def replay_partner_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    return replay_payload(build_partner_intake_payload(bundle))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay a WS-DCAR partner-origin event bundle"
    )
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    print(json.dumps(replay_partner_bundle(bundle), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
