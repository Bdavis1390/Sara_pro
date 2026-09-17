from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from typing import Any

from .prime_sentinel_authorization import (
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
)
from .restriction_provenance import (
    RESTRICTION_AUTHORITY,
    RESTRICTION_EVENT,
    RESTRICTION_SCHEMA,
    RESTRICTION_SCHEMA_V1,
    RESTRICTION_SCHEMA_V2,
)
from .restriction_signature import (
    RESTRICTION_SIGNATURE_SCHEMA,
    SIGNED_RESTRICTION_SCHEMA,
    verify_restriction_signature_document,
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
_V3_PAYLOAD_KEYS = _V2_PAYLOAD_KEYS | frozenset({"fingerprint_key_id"})
_V4_PAYLOAD_KEYS = frozenset(
    {
        "schema",
        "restriction",
        "prime_signature",
        "raw_content_persisted",
        "_outbox_event_id",
        "_delivery_semantics",
    }
)
_SIGNATURE_KEYS = frozenset(
    {
        "schema",
        "restriction_id",
        "signing_key_id",
        "signing_key_fingerprint_sha256",
        "signature_b64url",
        "signed_message_sha256",
    }
)


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


def _canonical_json(value: dict[str, Any]) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RestrictionObservabilityError(
            "restriction identity document is not canonical bounded JSON"
        ) from exc


def _expected_restriction_id(payload: dict[str, Any], provenance_schema: str) -> str:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise RestrictionObservabilityError("restriction metadata is invalid")

    safe_summary = payload.get("safe_summary")
    if safe_summary is not None and not isinstance(safe_summary, str):
        raise RestrictionObservabilityError("restriction safe_summary is invalid")

    identity_document: dict[str, Any] = {
        "schema": provenance_schema,
        "occurred_at": payload.get("occurred_at"),
        "action": payload.get("action"),
        "reason_code": payload.get("reason_code"),
        "source_system": payload.get("source_system"),
        "processor": payload.get("processor"),
        "process_version": payload.get("process_version"),
        "policy_ref": payload.get("policy_ref"),
        "correlation_id": payload.get("correlation_id"),
        "parent_event_id": payload.get("parent_event_id"),
        "input_fingerprint": payload.get("input_fingerprint"),
        "generated_fingerprint": payload.get("generated_fingerprint"),
        "safe_output_fingerprint": payload.get("safe_output_fingerprint"),
        "safe_summary": safe_summary,
        "metadata": metadata,
        "raw_content_persisted": payload.get("raw_content_persisted"),
    }
    if provenance_schema in {RESTRICTION_SCHEMA_V2, RESTRICTION_SCHEMA}:
        identity_document["authority"] = payload.get("authority")
    if provenance_schema == RESTRICTION_SCHEMA:
        identity_document["fingerprint_key_id"] = payload.get("fingerprint_key_id")

    return hashlib.sha256(
        _canonical_json(identity_document).encode("utf-8")
    ).hexdigest()[:32]


def _project_signed_restriction_audit_record(
    record: dict[str, Any],
    *,
    audit_timestamp: str,
    payload: dict[str, Any],
    verifier: PrimeSentinelVerifier | None,
) -> dict[str, Any]:
    if verifier is None:
        raise RestrictionObservabilityError(
            "signed restriction evidence requires a PRIME signature verifier"
        )
    unknown_top = sorted(set(payload) - _V4_PAYLOAD_KEYS)
    if unknown_top:
        raise RestrictionObservabilityError(
            "signed restriction envelope contains unknown fields"
        )
    if payload.get("raw_content_persisted") is not False:
        raise RestrictionObservabilityError(
            "signed restriction raw-content persistence assertion is invalid"
        )

    event_id = payload.get("_outbox_event_id")
    if not isinstance(event_id, str):
        raise RestrictionObservabilityError("signed restriction event ID is missing")
    if payload.get("_delivery_semantics") != "AT_LEAST_ONCE":
        raise RestrictionObservabilityError(
            "signed restriction delivery semantics are invalid"
        )

    restriction = payload.get("restriction")
    signature = payload.get("prime_signature")
    if not isinstance(restriction, dict):
        raise RestrictionObservabilityError("signed restriction document is missing")
    if not isinstance(signature, dict):
        raise RestrictionObservabilityError("PRIME signature attestation is missing")

    # Reuse the V1-V3 structural and semantic-ID validation path, injecting
    # only the delivery metadata that lives at the V4 envelope level.
    nested_payload = dict(restriction)
    nested_payload["_outbox_event_id"] = event_id
    nested_payload["_delivery_semantics"] = "AT_LEAST_ONCE"
    nested_record = {
        "timestamp": audit_timestamp,
        "event": RESTRICTION_EVENT,
        "actor": RESTRICTION_AUTHORITY,
        "payload": nested_payload,
    }
    projected = project_restriction_audit_record(
        nested_record,
        verifier=verifier,
    )
    if projected["provenance_schema"] != RESTRICTION_SCHEMA:
        raise RestrictionObservabilityError(
            "V4 signed envelopes must wrap the active V3 restriction schema"
        )

    unknown_signature = sorted(set(signature) - _SIGNATURE_KEYS)
    if unknown_signature:
        raise RestrictionObservabilityError(
            "PRIME signature attestation contains unknown fields"
        )
    if signature.get("schema") != RESTRICTION_SIGNATURE_SCHEMA:
        raise RestrictionObservabilityError("PRIME signature schema is invalid")
    if signature.get("restriction_id") != projected["restriction_id"]:
        raise RestrictionObservabilityError(
            "PRIME signature restriction identity mismatch"
        )

    signing_key_id = _component(signature.get("signing_key_id"), "signing_key_id")
    signing_key_fingerprint = _fingerprint(
        signature.get("signing_key_fingerprint_sha256"),
        "signing_key_fingerprint_sha256",
    )
    signed_message_sha256 = _fingerprint(
        signature.get("signed_message_sha256"),
        "signed_message_sha256",
    )
    signature_b64url = signature.get("signature_b64url")
    if not isinstance(signature_b64url, str) or not signature_b64url:
        raise RestrictionObservabilityError("PRIME signature value is invalid")

    try:
        verified = verify_restriction_signature_document(
            restriction,
            signing_key_id=signing_key_id,
            signature_b64url=signature_b64url,
            verifier=verifier,
        )
    except (PrimeSentinelAuthorizationError, ValueError) as exc:
        raise RestrictionObservabilityError(
            "PRIME restriction signature verification failed"
        ) from exc

    if verified.signing_key_fingerprint_sha256 != signing_key_fingerprint:
        raise RestrictionObservabilityError(
            "PRIME signature public-key fingerprint mismatch"
        )
    if verified.signed_message_sha256 != signed_message_sha256:
        raise RestrictionObservabilityError(
            "PRIME signed-message digest mismatch"
        )

    return {
        **projected,
        "provenance_schema": SIGNED_RESTRICTION_SCHEMA,
        "restriction_schema": RESTRICTION_SCHEMA,
        "signature_verified": True,
        "signing_key_id": verified.key_id,
        "signing_key_fingerprint_sha256": verified.signing_key_fingerprint_sha256,
    }


def project_restriction_audit_record(
    record: dict[str, Any],
    *,
    verifier: PrimeSentinelVerifier | None = None,
) -> dict[str, Any]:
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
    if provenance_schema == SIGNED_RESTRICTION_SCHEMA:
        return _project_signed_restriction_audit_record(
            record,
            audit_timestamp=audit_timestamp,
            payload=payload,
            verifier=verifier,
        )
    if provenance_schema == RESTRICTION_SCHEMA_V1:
        allowed_payload_keys = _V1_PAYLOAD_KEYS
        authority_bound_in_payload = False
        fingerprint_key_epoch_bound_in_payload = False
        fingerprint_key_id = None
    elif provenance_schema == RESTRICTION_SCHEMA_V2:
        allowed_payload_keys = _V2_PAYLOAD_KEYS
        authority_bound_in_payload = True
        fingerprint_key_epoch_bound_in_payload = False
        fingerprint_key_id = None
        if payload.get("authority") != RESTRICTION_AUTHORITY:
            raise RestrictionObservabilityError("restriction payload authority is invalid")
    elif provenance_schema == RESTRICTION_SCHEMA:
        allowed_payload_keys = _V3_PAYLOAD_KEYS
        authority_bound_in_payload = True
        fingerprint_key_epoch_bound_in_payload = True
        if payload.get("authority") != RESTRICTION_AUTHORITY:
            raise RestrictionObservabilityError("restriction payload authority is invalid")
        fingerprint_key_id = _component(
            payload.get("fingerprint_key_id"),
            "fingerprint_key_id",
        )
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
    if restriction_id != _expected_restriction_id(payload, provenance_schema):
        raise RestrictionObservabilityError(
            "restriction_id does not match the semantic evidence identity"
        )

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
        "delivery_semantics": "AT_LEAST_ONCE",
        "authority": RESTRICTION_AUTHORITY,
        "authority_bound_in_payload": authority_bound_in_payload,
        "restriction_schema": provenance_schema,
        "signature_verified": False,
        "signing_key_id": None,
        "signing_key_fingerprint_sha256": None,
        "fingerprint_key_id": fingerprint_key_id,
        "fingerprint_key_epoch_bound_in_payload": fingerprint_key_epoch_bound_in_payload,
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


ASSURANCE_DIMENSIONS = (
    "restriction_identity",
    "event_identity",
    "delivery_semantics",
    "authority_identity",
    "authority_binding",
    "fingerprint_key_epoch",
    "signature_verification",
    "signing_key_identity",
    "signing_key_fingerprint",
    "raw_content_persistence",
)


def restriction_assurance_dimensions(projected: dict[str, Any]) -> dict[str, bool]:
    restriction_id = projected.get("restriction_id")
    event_id = projected.get("event_id")
    signing_key_fingerprint = projected.get("signing_key_fingerprint_sha256")
    facts = {
        "restriction_identity": isinstance(restriction_id, str)
        and bool(_RESTRICTION_ID.fullmatch(restriction_id)),
        "event_identity": isinstance(event_id, str)
        and event_id == f"SARA-EVENT-RESTRICTION-{restriction_id}",
        "delivery_semantics": projected.get("delivery_semantics") == "AT_LEAST_ONCE",
        "authority_identity": projected.get("authority") == RESTRICTION_AUTHORITY,
        "authority_binding": projected.get("authority_bound_in_payload") is True,
        "fingerprint_key_epoch": (
            projected.get("fingerprint_key_epoch_bound_in_payload") is True
            and isinstance(projected.get("fingerprint_key_id"), str)
            and bool(projected.get("fingerprint_key_id"))
        ),
        "signature_verification": projected.get("signature_verified") is True,
        "signing_key_identity": isinstance(projected.get("signing_key_id"), str)
        and bool(projected.get("signing_key_id")),
        "signing_key_fingerprint": isinstance(signing_key_fingerprint, str)
        and bool(_FINGERPRINT.fullmatch(signing_key_fingerprint)),
        "raw_content_persistence": projected.get("raw_content_persisted") is False,
    }
    assert tuple(facts) == ASSURANCE_DIMENSIONS
    return facts


def restriction_observability(
    audit_records: list[dict[str, Any]],
    *,
    recent_limit: int = 50,
    verifier: PrimeSentinelVerifier | None = None,
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
            projected.append(project_restriction_audit_record(record, verifier=verifier))
        except RestrictionObservabilityError:
            malformed += 1

    by_action = Counter(str(item["action"]) for item in projected)
    by_reason = Counter(str(item["reason_code"]) for item in projected)
    by_source = Counter(str(item["source_system"]) for item in projected)
    by_processor = Counter(str(item["processor"]) for item in projected)
    by_fingerprint_key_id = Counter(
        str(item["fingerprint_key_id"] or "UNBOUND_LEGACY") for item in projected
    )
    by_signing_key_id = Counter(
        str(item["signing_key_id"] or "UNSIGNED_LEGACY") for item in projected
    )
    assurance_vectors = [restriction_assurance_dimensions(item) for item in projected]
    fully_resolved = sum(
        int(all(vector.values())) for vector in assurance_vectors
    )
    unresolved_dimensions = sum(
        sum(int(not value) for value in vector.values())
        for vector in assurance_vectors
    )

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
            "by_fingerprint_key_id": dict(sorted(by_fingerprint_key_id.items())),
            "by_signing_key_id": dict(sorted(by_signing_key_id.items())),
        },
        "assurance_quality": {
            "required_dimensions_per_record": len(ASSURANCE_DIMENSIONS),
            "fully_resolved_v4_records": fully_resolved,
            "unresolved_dimensions": unresolved_dimensions,
        },
        "last_valid_occurred_at": last_valid_occurred_at,
        "recent": newest_first,
        "claims_boundary": (
            "Window-scoped observability over persisted SARA restriction events only; "
            "bounded audit retention does not establish global lifetime counts or complete "
            "provider-side restriction history. V1 records rely on the governed outer audit "
            "actor; V2 records additionally bind authority into the payload identity; V3 "
            "records also bind the non-secret fingerprint-key epoch identifier; V4 "
            "records additionally require a currently trusted PRIME Ed25519 signature."
        ),
    }
