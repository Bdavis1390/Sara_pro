from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from partner_bundle import MeasurementBoundary
from partner_intake import SCHEMA_VERSION


@dataclass(frozen=True)
class PreflightReport:
    schema_version: str | None
    replay_ready: bool
    measurement_boundary: str | None
    claim_scope: str | None
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    source_object_count: int
    point_count: int
    source_hashes_declared: int
    bundle_sha256: str


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mapping(value: object) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _placeholder(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    return normalized.startswith("replace-with-") or normalized.startswith(
        "replace_with_"
    )


def _claim_scope(boundary: str | None) -> str | None:
    if boundary is None:
        return None
    if boundary == MeasurementBoundary.GRID_BOUNDARY.value:
        return "grid_boundary"
    if boundary == MeasurementBoundary.FACILITY.value:
        return "facility_only"
    try:
        return f"{MeasurementBoundary(boundary).value}_only"
    except ValueError:
        return None


def preflight_partner_bundle(bundle: dict[str, Any]) -> PreflightReport:
    """Inspect partner evidence without inferring missing facts or issuing a verdict.

    Preflight is deliberately separate from FLEX-001 replay. It reports whether
    the package is structurally ready to enter the normal fail-closed verifier,
    what claim scope the declared measurement boundary permits, and which
    evidence/custody defects should be resolved first.
    """

    blockers: list[str] = []
    warnings: list[str] = []

    schema_version = bundle.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        blockers.append("unsupported_or_missing_schema_version")

    request = _mapping(bundle.get("request"))
    if request is None:
        blockers.append("request_object_missing")
    else:
        for field in (
            "requested_reduction_mw",
            "response_deadline_s",
            "required_duration_s",
            "max_measured_power_mw",
        ):
            value = request.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                blockers.append(f"request_{field}_missing_or_invalid")

    baseline = bundle.get("baseline_mw")
    if isinstance(baseline, bool) or not isinstance(baseline, (int, float)):
        blockers.append("baseline_mw_missing_or_invalid")

    context = _mapping(bundle.get("partner_context"))
    boundary: str | None = None
    if context is None:
        blockers.append("partner_context_missing")
    else:
        for field in ("source_organization", "project_or_dataset_id"):
            value = context.get(field)
            if not isinstance(value, str) or not value.strip() or _placeholder(value):
                blockers.append(f"{field}_missing_or_placeholder")

        boundary_value = context.get("measurement_boundary")
        if isinstance(boundary_value, str):
            try:
                boundary = MeasurementBoundary(boundary_value).value
            except ValueError:
                blockers.append("measurement_boundary_invalid")
        else:
            blockers.append("measurement_boundary_missing")

        required_evidence_strings = (
            "request_id",
            "authorization_record_id",
            "clock_source",
            "baseline_method",
            "configuration_id",
            "meter_id",
        )
        for field in required_evidence_strings:
            if field not in context:
                blockers.append(f"{field}_field_missing")
                continue
            value = context.get(field)
            if value is None:
                warnings.append(f"{field}_not_provided")
            elif (
                not isinstance(value, str)
                or not value.strip()
                or _placeholder(value)
            ):
                blockers.append(f"{field}_invalid_or_placeholder")

        for field in (
            "authorized",
            "request_provenance_valid",
            "authorization_evidence_valid",
            "clocks_synchronized",
            "baseline_valid",
            "configuration_custody_valid",
        ):
            value = context.get(field)
            if type(value) is not bool:
                blockers.append(f"{field}_must_be_explicit_boolean")

        for field, reason in (
            ("request_provenance_valid", "request_provenance_declared_invalid"),
            (
                "authorization_evidence_valid",
                "authorization_evidence_declared_invalid",
            ),
            ("clocks_synchronized", "clock_sync_declared_invalid"),
            ("baseline_valid", "baseline_declared_invalid"),
            (
                "configuration_custody_valid",
                "configuration_custody_declared_invalid",
            ),
        ):
            if context.get(field) is False:
                warnings.append(reason)

        if context.get("authorized") is False:
            warnings.append("action_declared_unauthorized")

    custody = _mapping(bundle.get("custody"))
    if custody is None:
        blockers.append("custody_object_missing")
    else:
        for field in (
            "event_start_utc",
            "event_end_utc",
            "timezone",
            "baseline_uncertainty_mw",
            "transformation_tool",
            "transformation_tool_version",
            "redaction_statement",
        ):
            if field not in custody:
                blockers.append(f"custody_{field}_field_missing")

        for field in (
            "event_start_utc",
            "event_end_utc",
            "timezone",
            "transformation_tool",
            "transformation_tool_version",
        ):
            if field in custody:
                value = custody.get(field)
                if value is None:
                    warnings.append(f"custody_{field}_not_provided")
                elif (
                    not isinstance(value, str)
                    or not value.strip()
                    or _placeholder(value)
                ):
                    blockers.append(f"custody_{field}_invalid_or_placeholder")

        if "baseline_uncertainty_mw" in custody:
            value = custody.get("baseline_uncertainty_mw")
            if value is None:
                warnings.append("custody_baseline_uncertainty_mw_not_provided")
            elif isinstance(value, bool) or not isinstance(value, (int, float)):
                blockers.append("custody_baseline_uncertainty_mw_invalid")

        if "redaction_statement" in custody:
            value = custody.get("redaction_statement")
            if (
                not isinstance(value, str)
                or not value.strip()
                or _placeholder(value)
            ):
                blockers.append(
                    "custody_redaction_statement_invalid_or_placeholder"
                )

    source_objects_raw = bundle.get("source_objects")
    source_objects = source_objects_raw if isinstance(source_objects_raw, list) else []
    if not source_objects:
        blockers.append("source_objects_missing")
    source_hashes_declared = 0
    for index, raw in enumerate(source_objects):
        obj = _mapping(raw)
        if obj is None:
            blockers.append(f"source_object_{index}_invalid")
            continue
        object_id = obj.get("object_id")
        if (
            not isinstance(object_id, str)
            or not object_id.strip()
            or _placeholder(object_id)
        ):
            blockers.append(f"source_object_{index}_identity_missing_or_placeholder")
        sha256 = obj.get("sha256")
        if isinstance(sha256, str) and len(sha256) == 64:
            source_hashes_declared += 1
        elif sha256 is None:
            warnings.append(f"source_object_{index}_sha256_not_declared")
        else:
            blockers.append(f"source_object_{index}_sha256_invalid")

    points_raw = bundle.get("points")
    points = points_raw if isinstance(points_raw, list) else []
    if len(points) < 2:
        blockers.append("insufficient_measurement_points")

    configuration_ids: set[str] = set()
    meter_ids: set[str] = set()
    for index, raw in enumerate(points):
        point = _mapping(raw)
        if point is None:
            blockers.append(f"point_{index}_invalid")
            continue
        for field in ("timestamp_s", "measured_power_mw"):
            value = point.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                blockers.append(f"point_{index}_{field}_missing_or_invalid")
        for field in ("telemetry_fresh", "meter_provenance_valid"):
            value = point.get(field)
            if type(value) is not bool:
                blockers.append(f"point_{index}_{field}_must_be_explicit_boolean")
        if point.get("telemetry_fresh") is False:
            warnings.append(f"point_{index}_telemetry_declared_stale")
        if point.get("meter_provenance_valid") is False:
            warnings.append(f"point_{index}_meter_provenance_declared_invalid")

        configuration_id = point.get("configuration_id")
        if (
            not isinstance(configuration_id, str)
            or not configuration_id.strip()
            or _placeholder(configuration_id)
        ):
            blockers.append(f"point_{index}_configuration_id_missing_or_placeholder")
        else:
            configuration_ids.add(configuration_id)

        meter_id = point.get("meter_id")
        if (
            not isinstance(meter_id, str)
            or not meter_id.strip()
            or _placeholder(meter_id)
        ):
            blockers.append(f"point_{index}_meter_id_missing_or_placeholder")
        else:
            meter_ids.add(meter_id)

    if len(configuration_ids) > 1:
        warnings.append("configuration_drift_present")
    if len(meter_ids) > 1:
        warnings.append("meter_identity_change_present")

    if boundary not in {
        None,
        MeasurementBoundary.GRID_BOUNDARY.value,
    }:
        warnings.append(f"claim_scope_limited_to_{_claim_scope(boundary)}")

    return PreflightReport(
        schema_version=schema_version if isinstance(schema_version, str) else None,
        replay_ready=not blockers,
        measurement_boundary=boundary,
        claim_scope=_claim_scope(boundary),
        blockers=tuple(dict.fromkeys(blockers)),
        warnings=tuple(dict.fromkeys(warnings)),
        source_object_count=len(source_objects),
        point_count=len(points),
        source_hashes_declared=source_hashes_declared,
        bundle_sha256=_canonical_sha256(bundle),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight a WS-DCAR partner-origin event bundle"
    )
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    report = preflight_partner_bundle(bundle)
    print(json.dumps(asdict(report), indent=2, sort_keys=True))
    return 0 if report.replay_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
