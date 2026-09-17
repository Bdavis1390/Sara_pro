from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Any

from .restriction_provenance import (
    RESTRICTION_AUTHORITY,
    RESTRICTION_EVENT,
    RESTRICTION_SCHEMA,
    RESTRICTION_SCHEMA_V1,
)


RESTRICTION_OBSERVABILITY_SCHEMA = "WS-RESTRICTION-OBSERVABILITY-V1"
RESTRICTION_OBSERVABILITY_SCOPE = "BOUNDED_SARA_AUDIT_WINDOW"
MAX_RESTRICTION_AUDIT_WINDOW = 500
MAX_RESTRICTION_RECENT_RESULTS = 100

_RESTRICTION_ID = re.compile(r"^[0-9a-f]{32}$")
_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")
_REASON_CODE = re.compile(r"^[A-Z0-9][A-Z0-9_.:-]{0,95}$")
_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}$")
_ALLOWED_ACTIONS = frozenset({"BLOCK", "REDACT", "TRANSFORM", "ESCALATE"})
_OPTIONAL_COMPONENT_FIELDS = (
    "process_version",
    "policy_ref",
    "correlation_id",
    "parent_event_id",
)
_FINGERPRINT_FIELDS = (
    "input_fingerprint",
    "generated_fingerprint",
    "safe_output_fingerprint",
)
_V1_PAYLOAD_KEYS = frozenset(
    {
        "schema",
        "restriction_id",
        "occurred_at",
        "action",
        "reason_code",
        "source_system",
        "processor",
        *_OPTIONAL_COMPONENT_FIELDS,
        *_FINGERPRINT_FIELDS,
        "safe_summary",
        "metadata",
        "raw_content_persisted",
        "_outbox_event_id",
        "_delivery_semantics",
    }
)
_V2_PAYLOAD_KEYS = _V1_PAYLOAD_KEYS | frozenset({"authority"})


class RestrictionObservabilityError(ValueError):
    pass


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise RestrictionObservabilityError(f"{name} is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RestrictionObservabilityError(f"{name} is invalid") from exc
    if parsed.tzinfo is None:
        raise RestrictionObservabilityError(f"{name} must be timezone-aware")
    return value


def _component(value: Any, name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not _COMPONENT.fullmatch(value):
        raise RestrictionObservabilityError(f"{name} is invalid")
    return value


def _fingerprint(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _FINGERPRINT.fullmatch(value):
        raise RestrictionObservabilityError(f"{name} is invalid")
    return value


def project_restriction_audit_record(record: dict[str, Any]) -> dict[str, Any]:
    """Validate one restriction audit event and return a strict non-content projection."""
    if not isinstance(record, dict) or record.get("event") != RESTRICTION_EVENT:
        raise RestrictionObservabilityError("record is not a restriction event")
    if record.get("actor") != RESTRICTION_AUTHORITY:
        raise RestrictionObservabilityError("restriction audit actor is not the governed authority")

    audit_timestamp = _timestamp(record.get("timestamp"), "audit timestamp")
    payload = record.get("payload")
    if not isinstance(payload, dict):
        raise RestrictionObservabilityError("restriction payload is missing")

    provenance_schema = payload.get("schema")
    if provenance_schema == RESTRICTION_SCHEMA_V1:
        allowed_payload_keys = _V1_PAYLOAD_KEYS
        authority_bound_in_payload = False
    elif provenance_schema == RESTRICTION_SCHEMA:
        allowed_payload_keys = _V2_PAYLOAD_KEYS
        authority_bound_in_payload = True
        if payload.get("authority") != RESTRICTION_AUTHORITY:
            raise RestrictionObservabilityError("restriction payload authority is invalid")
    else:
        raise RestrictionObservabilityError("restriction schema is invalid")

    unknown_keys = sorted(set(payload) - allowed_payload_keys)
    if unknown_keys:
        raise RestrictionObservabilityError("restriction payload contains unknown fields")
    if payload.get("raw_content_persisted") is not False:
        raise RestrictionObservabilityError("raw-content persistence assertion is invalid")

    restriction_id = payload.get("restriction_id")
    if not isinstance(restriction_id, str) or not _RESTRICTION_ID.fullmatch(restriction_id):
        raise RestrictionObservabilityError("restriction_id is invalid")

    event_id = payload.get("_outbox_event_id")
    expected_event_id = f"SARA-EVENT-RESTRICTION-{restriction_id}"
    if event_id != expected_event_id:
        raise RestrictionObservabilityError("restriction outbox event ID is invalid")
    if payload.get("_delivery_semantics") != "AT_LEAST_ONCE":
        raise RestrictionObservabilityError("restriction delivery semantics are invalid")

    action = payload.get("action")
    if action not in _ALLOWED_ACTIONS:
        raise RestrictionObservabilityError("restriction action is invalid")

    reason_code = payload.get("reason_code")
    if not isinstance(reason_code, str) or not _REASON_CODE.fullmatch(reason_code):
        raise RestrictionObservabilityError("restriction reason_code is invalid")

    source_system = _component(payload.get("source_system"), "source_system")
    processor = _component(payload.get("processor"), "processor")
    occurred_at = _timestamp(payload.get("occurred_at"), "occurred_at")

    optional_components = {
        name: _component(payload.get(name), name, optional=True)
        for name in _OPTIONAL_COMPONENT_FIELDS
    }
    fingerprints = {
        name: _fingerprint(payload.get(name), name) for name in _FINGERPRINT_FIELDS
    }

    return {
        "provenance_schema": provenance_schema,
        "restriction_id": restriction_id,
        "event_id": event_id,
        "authority": RESTRICTION_AUTHORITY,
        "authority_bound_in_payload": authority_bound_in_payload,
        "audit_timestamp": audit_timestamp,
        "occurred_at": occurred_at,
        "action": action,
        "reason_code": reason_code,
        "source_system": source_system,
        "processor": processor,
        **optional_components,
        **fingerprints,
        "raw_content_persisted": False,
    }


def restriction_observability(
    audit_records: list[dict[str, Any]],
    *,
    recent_limit: int = 50,
) -> dict[str, Any]:
    """Summarize restriction evidence from one explicitly bounded SARA audit window."""
    if not isinstance(audit_records, list):
        raise RestrictionObservabilityError("audit_records must be a list")
    if len(audit_records) > MAX_RESTRICTION_AUDIT_WINDOW:
        raise RestrictionObservabilityError(
            f"audit window must not exceed {MAX_RESTRICTION_AUDIT_WINDOW} records"
        )
    if not isinstance(recent_limit, int) or not 1 <= recent_limit <= MAX_RESTRICTION_RECENT_RESULTS:
        raise RestrictionObservabilityError(
            f"recent_limit must be 1-{MAX_RESTRICTION_RECENT_RESULTS}"
        )

    projected: list[dict[str, Any]] = []
    malformed = 0
    restriction_seen = 0
    for record in audit_records:
        if not isinstance(record, dict) or record.get("event") != RESTRICTION_EVENT:
            continue
        restriction_seen += 1
        try:
            projected.append(project_restriction_audit_record(record))
        except RestrictionObservabilityError:
            malformed += 1

    by_action = Counter(str(item["action"]) for item in projected)
    by_reason = Counter(str(item["reason_code"]) for item in projected)
    by_source = Counter(str(item["source_system"]) for item in projected)
    by_processor = Counter(str(item["processor"]) for item in projected)

    newest_first = list(reversed(projected[-recent_limit:]))
    last_valid_occurred_at = None if not projected else projected[-1]["occurred_at"]
    return {
        "schema": RESTRICTION_OBSERVABILITY_SCHEMA,
        "scope": RESTRICTION_OBSERVABILITY_SCOPE,
        "ok": malformed == 0,
        "scanned_audit_records": len(audit_records),
        "restriction_events_seen": restriction_seen,
        "valid_restriction_events": len(projected),
        "malformed_restriction_events": malformed,
        "counts": {
            "by_action": dict(sorted(by_action.items())),
            "by_reason_code": dict(sorted(by_reason.items())),
            "by_source_system": dict(sorted(by_source.items())),
            "by_processor": dict(sorted(by_processor.items())),
        },
        "last_valid_occurred_at": last_valid_occurred_at,
        "recent": newest_first,
        "claims_boundary": (
            "Window-scoped observability over persisted SARA restriction events only; "
            "bounded audit retention does not establish global lifetime counts or complete "
            "provider-side restriction history. V1 records rely on the governed outer audit "
            "actor; V2 records additionally bind that authority into the payload identity."
        ),
    }
