from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict

from worldshepherd_sara.evidence_contract import EvidenceValidationError, REVIEW_STATES

CALIBRATION_TYPES = {"PRE", "MID", "POST", "CHECK", "REFERENCE"}
COMBINATION_METHODS = {"RSS_INDEPENDENT", "EXTERNAL_MODEL"}


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceValidationError(f"{field} must be a non-empty string")
    return value


def _number(value: Any, field: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceValidationError(f"{field} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise EvidenceValidationError(f"{field} must be finite")
    if nonnegative and result < 0:
        raise EvidenceValidationError(f"{field} must be non-negative")
    return result


def _timestamp(value: Any, field: str) -> None:
    text = _string(value, field)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise EvidenceValidationError(f"{field} must be ISO-8601 date-time") from exc


def _close(actual: float, expected: float) -> bool:
    scale = max(1.0, abs(actual), abs(expected))
    return abs(actual - expected) <= 1e-9 * scale


def validate_calibration_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise EvidenceValidationError("calibration record must be a JSON object")

    required = {
        "calibration_id",
        "timestamp_utc",
        "instrument_id",
        "quantity",
        "units",
        "calibration_type",
        "method",
        "reference_standard",
        "calibration_points",
        "uncertainty_budget",
        "combination_method",
        "combined_standard_uncertainty",
        "coverage_factor",
        "expanded_uncertainty",
        "environment",
        "raw_data",
        "review_state",
        "validity",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise EvidenceValidationError(
            f"calibration record missing required fields: {', '.join(missing)}"
        )

    for field in ("calibration_id", "instrument_id", "quantity", "units", "method"):
        _string(payload[field], field)
    _timestamp(payload["timestamp_utc"], "timestamp_utc")

    if payload["calibration_type"] not in CALIBRATION_TYPES:
        raise EvidenceValidationError(
            "calibration_type must be one of: " + ", ".join(sorted(CALIBRATION_TYPES))
        )
    if payload["combination_method"] not in COMBINATION_METHODS:
        raise EvidenceValidationError(
            "combination_method must be one of: " + ", ".join(sorted(COMBINATION_METHODS))
        )
    if payload["review_state"] not in REVIEW_STATES:
        raise EvidenceValidationError(
            "review_state must be one of: " + ", ".join(sorted(REVIEW_STATES))
        )

    reference = payload["reference_standard"]
    if not isinstance(reference, dict):
        raise EvidenceValidationError("reference_standard must be a JSON object")
    for field in ("standard_id", "traceability"):
        if field not in reference:
            raise EvidenceValidationError(f"reference_standard missing required field: {field}")
        _string(reference[field], f"reference_standard.{field}")
    if "standard_uncertainty" not in reference:
        raise EvidenceValidationError("reference_standard missing required field: standard_uncertainty")
    _number(
        reference["standard_uncertainty"],
        "reference_standard.standard_uncertainty",
        nonnegative=True,
    )

    points = payload["calibration_points"]
    if not isinstance(points, list) or len(points) < 2:
        raise EvidenceValidationError("calibration_points must contain at least two points")
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise EvidenceValidationError(f"calibration_points[{index}] must be a JSON object")
        for field in ("applied_value", "indicated_value"):
            if field not in point:
                raise EvidenceValidationError(
                    f"calibration_points[{index}] missing required field: {field}"
                )
            _number(point[field], f"calibration_points[{index}].{field}")

    budget = payload["uncertainty_budget"]
    if not isinstance(budget, list) or not budget:
        raise EvidenceValidationError("uncertainty_budget must be a non-empty list")
    component_values: list[float] = []
    names: list[str] = []
    for index, component in enumerate(budget):
        if not isinstance(component, dict):
            raise EvidenceValidationError(f"uncertainty_budget[{index}] must be a JSON object")
        if "name" not in component or "standard_uncertainty" not in component:
            raise EvidenceValidationError(
                f"uncertainty_budget[{index}] requires name and standard_uncertainty"
            )
        names.append(_string(component["name"], f"uncertainty_budget[{index}].name"))
        component_values.append(
            _number(
                component["standard_uncertainty"],
                f"uncertainty_budget[{index}].standard_uncertainty",
                nonnegative=True,
            )
        )
    if len(names) != len(set(names)):
        raise EvidenceValidationError("uncertainty_budget component names must be unique")

    combined = _number(
        payload["combined_standard_uncertainty"],
        "combined_standard_uncertainty",
        nonnegative=True,
    )
    coverage = _number(payload["coverage_factor"], "coverage_factor", nonnegative=True)
    if coverage <= 0:
        raise EvidenceValidationError("coverage_factor must be > 0")
    expanded = _number(
        payload["expanded_uncertainty"], "expanded_uncertainty", nonnegative=True
    )

    if payload["combination_method"] == "RSS_INDEPENDENT":
        expected_combined = math.sqrt(sum(value * value for value in component_values))
        if not _close(combined, expected_combined):
            raise EvidenceValidationError(
                "combined_standard_uncertainty does not match RSS of uncertainty_budget"
            )

    if not _close(expanded, combined * coverage):
        raise EvidenceValidationError(
            "expanded_uncertainty must equal combined_standard_uncertainty * coverage_factor"
        )

    for field in ("environment", "validity"):
        if not isinstance(payload[field], dict):
            raise EvidenceValidationError(f"{field} must be a JSON object")

    raw = payload["raw_data"]
    if not isinstance(raw, dict):
        raise EvidenceValidationError("raw_data must be a JSON object")
    for field in ("location", "digest"):
        if field not in raw:
            raise EvidenceValidationError(f"raw_data missing required field: {field}")
        _string(raw[field], f"raw_data.{field}")

    return payload
