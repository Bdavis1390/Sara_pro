from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

EVIDENCE_CLASSES = {
    "MEASURED",
    "CALCULATED",
    "LITERATURE",
    "SIMULATED",
    "HYPOTHESIS",
    "NULL_CONTROL",
    "ARTIFACT",
}

RESULT_CLASSES = {"WS-R0", "WS-R1", "WS-R2", "WS-R3", "WS-R4"}
REVIEW_STATES = {"DRAFT", "OPERATOR_REVIEWED", "CRE1AWS_REVIEWED", "FROZEN"}
GLOB_OPERATORS = {"PA", "PB", "PC"}

CLAIM_CLASSES = {
    "OBSERVATION",
    "DERIVED_RESULT",
    "MODEL_PREDICTION",
    "LITERATURE_ASSERTION",
    "ENGINEERING_CONCLUSION",
    "HYPOTHESIS",
    "ANOMALOUS_RESIDUAL",
}

CONFIDENCE_STATES = {
    "UNASSESSED",
    "HYPOTHESIS_ONLY",
    "PRELIMINARY",
    "SUPPORTED_WITHIN_DOMAIN",
    "CONTRADICTED",
    "INDEPENDENTLY_REPRODUCED",
}


class EvidenceValidationError(ValueError):
    """Raised when a Worldshepherd evidence record violates the v0.1 contract."""


def _require_object(payload: Any, name: str) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise EvidenceValidationError(f"{name} must be a JSON object")
    return payload


def _require_keys(payload: Dict[str, Any], keys: Iterable[str], name: str) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise EvidenceValidationError(f"{name} missing required fields: {', '.join(missing)}")


def _require_nonempty_string(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceValidationError(f"{field} must be a non-empty string")


def _require_enum(value: Any, allowed: set[str], field: str) -> None:
    if value not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise EvidenceValidationError(f"{field} must be one of: {allowed_text}")


def _require_string_list(value: Any, field: str, *, allow_empty: bool = True) -> List[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise EvidenceValidationError(f"{field} must be a list of non-empty strings")
    if not allow_empty and not value:
        raise EvidenceValidationError(f"{field} must not be empty")
    if len(value) != len(set(value)):
        raise EvidenceValidationError(f"{field} must not contain duplicates")
    return value


def _validate_timestamp(value: Any, field: str) -> None:
    _require_nonempty_string(value, field)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise EvidenceValidationError(f"{field} must be ISO-8601 date-time") from exc


def _validate_evidence_classes(value: Any, field: str = "evidence_class") -> None:
    values = _require_string_list(value, field, allow_empty=False)
    unknown = sorted(set(values) - EVIDENCE_CLASSES)
    if unknown:
        raise EvidenceValidationError(f"{field} contains unsupported values: {', '.join(unknown)}")


def validate_experiment_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = _require_object(payload, "experiment record")
    _require_keys(
        payload,
        (
            "experiment_id",
            "campaign_id",
            "test_article_id",
            "timestamp_utc",
            "evidence_class",
            "hardware",
            "software",
            "calibration_ids",
            "sensor_manifest",
            "environment",
            "raw_data",
            "uncertainty",
            "hypotheses",
            "result_class",
            "review_state",
        ),
        "experiment record",
    )

    for field in ("experiment_id", "campaign_id", "test_article_id"):
        _require_nonempty_string(payload[field], field)

    _validate_timestamp(payload["timestamp_utc"], "timestamp_utc")
    _validate_evidence_classes(payload["evidence_class"])

    hardware = _require_object(payload["hardware"], "hardware")
    _require_keys(hardware, ("geometry_digest", "configuration_digest"), "hardware")
    _require_nonempty_string(hardware["geometry_digest"], "hardware.geometry_digest")
    _require_nonempty_string(hardware["configuration_digest"], "hardware.configuration_digest")
    if "material_batch_ids" in hardware:
        _require_string_list(hardware["material_batch_ids"], "hardware.material_batch_ids")

    software = _require_object(payload["software"], "software")
    _require_keys(software, ("sara_version", "commit"), "software")
    _require_nonempty_string(software["sara_version"], "software.sara_version")
    _require_nonempty_string(software["commit"], "software.commit")

    _require_string_list(payload["calibration_ids"], "calibration_ids")

    sensors = payload["sensor_manifest"]
    if not isinstance(sensors, list):
        raise EvidenceValidationError("sensor_manifest must be a list")
    sensor_ids: list[str] = []
    for index, sensor in enumerate(sensors):
        sensor = _require_object(sensor, f"sensor_manifest[{index}]")
        _require_keys(
            sensor,
            ("sensor_id", "quantity", "units", "sample_rate_hz", "calibration_id"),
            f"sensor_manifest[{index}]",
        )
        for field in ("sensor_id", "quantity", "units", "calibration_id"):
            _require_nonempty_string(sensor[field], f"sensor_manifest[{index}].{field}")
        if not isinstance(sensor["sample_rate_hz"], (int, float)) or sensor["sample_rate_hz"] <= 0:
            raise EvidenceValidationError(
                f"sensor_manifest[{index}].sample_rate_hz must be > 0"
            )
        sensor_ids.append(sensor["sensor_id"])
    if len(sensor_ids) != len(set(sensor_ids)):
        raise EvidenceValidationError("sensor_manifest sensor_id values must be unique")

    _require_object(payload["environment"], "environment")

    raw_data = _require_object(payload["raw_data"], "raw_data")
    _require_keys(raw_data, ("location", "digest"), "raw_data")
    _require_nonempty_string(raw_data["location"], "raw_data.location")
    _require_nonempty_string(raw_data["digest"], "raw_data.digest")

    uncertainty = _require_object(payload["uncertainty"], "uncertainty")
    _require_keys(uncertainty, ("model_id", "expanded_uncertainty"), "uncertainty")
    _require_nonempty_string(uncertainty["model_id"], "uncertainty.model_id")
    if (
        not isinstance(uncertainty["expanded_uncertainty"], (int, float))
        or uncertainty["expanded_uncertainty"] < 0
    ):
        raise EvidenceValidationError(
            "uncertainty.expanded_uncertainty must be a non-negative number"
        )

    hypotheses = _require_object(payload["hypotheses"], "hypotheses")
    _require_keys(hypotheses, ("H0", "H1"), "hypotheses")
    _require_nonempty_string(hypotheses["H0"], "hypotheses.H0")
    _require_nonempty_string(hypotheses["H1"], "hypotheses.H1")

    _require_enum(payload["result_class"], RESULT_CLASSES, "result_class")
    _require_enum(payload["review_state"], REVIEW_STATES, "review_state")

    glob = payload.get("glob")
    if glob is not None:
        glob = _require_object(glob, "glob")
        for field in ("seed", "operator", "orbit_state", "test_order"):
            if field not in glob:
                raise EvidenceValidationError(f"glob missing required field: {field}")
        _require_nonempty_string(glob["seed"], "glob.seed")
        _require_enum(glob["operator"], GLOB_OPERATORS, "glob.operator")
        _require_nonempty_string(glob["orbit_state"], "glob.orbit_state")
        if not isinstance(glob["test_order"], int) or glob["test_order"] < 0:
            raise EvidenceValidationError("glob.test_order must be a non-negative integer")

    return payload


def validate_claim_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = _require_object(payload, "claim record")
    _require_keys(
        payload,
        (
            "claim_id",
            "statement",
            "claim_class",
            "evidence_classes",
            "supporting_record_ids",
            "contradicting_record_ids",
            "validity_domain",
            "confidence_status",
            "review_state",
        ),
        "claim record",
    )

    _require_nonempty_string(payload["claim_id"], "claim_id")
    _require_nonempty_string(payload["statement"], "statement")
    _require_enum(payload["claim_class"], CLAIM_CLASSES, "claim_class")
    _validate_evidence_classes(payload["evidence_classes"], "evidence_classes")
    _require_string_list(payload["supporting_record_ids"], "supporting_record_ids")
    _require_string_list(payload["contradicting_record_ids"], "contradicting_record_ids")
    _require_object(payload["validity_domain"], "validity_domain")
    _require_enum(payload["confidence_status"], CONFIDENCE_STATES, "confidence_status")
    _require_enum(payload["review_state"], REVIEW_STATES, "review_state")

    replication_ids = payload.get("replication_ids", [])
    _require_string_list(replication_ids, "replication_ids")

    if (
        payload["claim_class"] == "ANOMALOUS_RESIDUAL"
        and payload["confidence_status"] == "INDEPENDENTLY_REPRODUCED"
        and not replication_ids
    ):
        raise EvidenceValidationError(
            "ANOMALOUS_RESIDUAL marked INDEPENDENTLY_REPRODUCED requires replication_ids"
        )

    return payload


def validate_record(kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if kind == "experiment":
        return validate_experiment_record(payload)
    if kind == "claim":
        return validate_claim_record(payload)
    raise EvidenceValidationError("kind must be 'experiment' or 'claim'")


def _main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: python -m worldshepherd_sara.evidence_contract <experiment|claim> <record.json>")
        return 2

    kind, path_text = argv[1], argv[2]
    path = Path(path_text)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_record(kind, payload)
    except (OSError, json.JSONDecodeError, EvidenceValidationError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1

    print(f"VALID {kind}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
