from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from .event_outbox import queue_event_outbox_patch
from .limits import validate_json_resource
from .restriction_context_policy import (
    RestrictionContextPolicyError,
    validate_restriction_context,
)


RESTRICTION_SCHEMA_V1 = "WS-RESTRICTION-PROVENANCE-V1"
RESTRICTION_SCHEMA_V2 = "WS-RESTRICTION-PROVENANCE-V2"
RESTRICTION_SCHEMA = "WS-RESTRICTION-PROVENANCE-V3"
RESTRICTION_AUTHORITY = "PRIME_SENTINEL"
REMEDIATION_SCHEMA = "WS-RESTRICTION-REMEDIATION-V1"
RESTRICTION_EVENT = "content_restriction_recorded"
MIN_FINGERPRINT_KEY_BYTES = 32
FINGERPRINT_KEY_ID_ENV = "RESTRICTION_FINGERPRINT_KEY_ID"
MAX_SAFE_SUMMARY_CHARS = 2048
MAX_REASON_CODE_CHARS = 96
MAX_COMPONENT_CHARS = 128

RestrictionAction = Literal["BLOCK", "REDACT", "TRANSFORM", "ESCALATE"]
RemediationAction = Literal[
    "NO_ACTION",
    "SAFE_TRANSFORM",
    "HUMAN_REVIEW",
    "REDUCE_SCOPE",
]

_ALLOWED_RESTRICTION_ACTIONS = frozenset({"BLOCK", "REDACT", "TRANSFORM", "ESCALATE"})
_ALLOWED_REMEDIATIONS = frozenset(
    {"NO_ACTION", "SAFE_TRANSFORM", "HUMAN_REVIEW", "REDUCE_SCOPE"}
)
_FORBIDDEN_REMEDIATIONS = frozenset(
    {"REPLAY_RAW", "RESTORE_RAW", "BYPASS_POLICY", "DISABLE_FILTER", "FORCE_RELEASE"}
)
_REASON_CODE = re.compile(r"^[A-Z0-9][A-Z0-9_.:-]{0,95}$")
_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}$")
_FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "raw",
        "raw_content",
        "restricted_content",
        "prompt",
        "prompt_text",
        "input_text",
        "generated_text",
        "completion",
        "completion_text",
        "output_text",
        "secret",
        "password",
        "token",
        "api_key",
    }
)


class RestrictionProvenanceError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RestrictionProvenanceError("restriction timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise RestrictionProvenanceError("restriction timestamp must be timezone-aware")


def _bounded_component(name: str, value: str) -> str:
    if not isinstance(value, str) or not _COMPONENT.fullmatch(value):
        raise RestrictionProvenanceError(
            f"{name} must be 1-{MAX_COMPONENT_CHARS} safe identifier characters"
        )
    return value


def _validate_fingerprint_key(key: bytes) -> None:
    if not isinstance(key, bytes) or len(key) < MIN_FINGERPRINT_KEY_BYTES:
        raise RestrictionProvenanceError(
            f"fingerprint key must contain at least {MIN_FINGERPRINT_KEY_BYTES} bytes"
        )


def _fingerprint(key: bytes, label: str, value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RestrictionProvenanceError(f"{label} content must be text when supplied")
    message = b"WS-RESTRICTION\x00" + label.encode("ascii") + b"\x00" + value.encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def fingerprint_key_id_from_environment() -> str:
    """Load the non-secret identifier for the active fingerprint-key epoch."""
    value = os.getenv(FINGERPRINT_KEY_ID_ENV, "")
    return _bounded_component("fingerprint_key_id", value)


def fingerprint_key_from_environment() -> bytes:
    """Load the deployment-only key used for non-reversible content fingerprints.

    The key is intentionally not stored in a restriction event. Deployments should
    provide a high-entropy secret through their normal secret-injection mechanism.
    """
    value = os.getenv("RESTRICTION_FINGERPRINT_KEY", "")
    key = value.encode("utf-8")
    _validate_fingerprint_key(key)
    return key


def _scan_metadata(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in _FORBIDDEN_METADATA_KEYS:
                raise RestrictionProvenanceError(
                    f"metadata key {key!r} is forbidden for restriction evidence"
                )
            _scan_metadata(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            _scan_metadata(child)


def _sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    value = {} if metadata is None else metadata
    if not isinstance(value, dict):
        raise RestrictionProvenanceError("metadata must be a JSON object")
    _scan_metadata(value)
    try:
        validate_json_resource(value)
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RestrictionProvenanceError("metadata is not safe bounded JSON") from exc
    decoded = json.loads(encoded)
    assert isinstance(decoded, dict)
    return decoded


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


@dataclass(frozen=True)
class RestrictionEvidence:
    restriction_id: str
    authority: str
    fingerprint_key_id: str
    occurred_at: str
    action: RestrictionAction
    reason_code: str
    source_system: str
    processor: str
    process_version: str | None
    policy_ref: str | None
    correlation_id: str | None
    parent_event_id: str | None
    input_fingerprint: str | None
    generated_fingerprint: str | None
    safe_output_fingerprint: str | None
    safe_summary: str | None
    metadata: dict[str, Any]

    def semantic_document(self) -> dict[str, Any]:
        return {
            "schema": RESTRICTION_SCHEMA,
            "restriction_id": self.restriction_id,
            "authority": self.authority,
            "fingerprint_key_id": self.fingerprint_key_id,
            "occurred_at": self.occurred_at,
            "action": self.action,
            "reason_code": self.reason_code,
            "source_system": self.source_system,
            "processor": self.processor,
            "process_version": self.process_version,
            "policy_ref": self.policy_ref,
            "correlation_id": self.correlation_id,
            "parent_event_id": self.parent_event_id,
            "input_fingerprint": self.input_fingerprint,
            "generated_fingerprint": self.generated_fingerprint,
            "safe_output_fingerprint": self.safe_output_fingerprint,
            "safe_summary": self.safe_summary,
            "metadata": self.metadata,
            "raw_content_persisted": False,
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.semantic_document())

    @property
    def outbox_event_id(self) -> str:
        return f"SARA-EVENT-RESTRICTION-{self.restriction_id}"


def capture_restriction(
    *,
    fingerprint_key: bytes,
    fingerprint_key_id: str,
    action: RestrictionAction,
    reason_code: str,
    source_system: str,
    processor: str,
    raw_input: str | None = None,
    raw_generated: str | None = None,
    safe_output: str | None = None,
    safe_summary: str | None = None,
    process_version: str | None = None,
    policy_ref: str | None = None,
    correlation_id: str | None = None,
    parent_event_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    occurred_at: str | None = None,
) -> RestrictionEvidence:
    """Convert a restriction into authority-bound non-content provenance.

    Raw text is accepted only long enough to compute domain-separated HMAC-SHA256
    fingerprints. It is never included in the returned object or its JSON form.
    The authority is system-controlled and cannot be supplied by the caller.
    """
    _validate_fingerprint_key(fingerprint_key)
    fingerprint_key_id = _bounded_component("fingerprint_key_id", fingerprint_key_id)
    if action not in _ALLOWED_RESTRICTION_ACTIONS:
        raise RestrictionProvenanceError("unsupported restriction action")
    if not isinstance(reason_code, str) or not _REASON_CODE.fullmatch(reason_code):
        raise RestrictionProvenanceError(
            f"reason_code must be 1-{MAX_REASON_CODE_CHARS} uppercase identifier characters"
        )
    source_system = _bounded_component("source_system", source_system)
    processor = _bounded_component("processor", processor)
    if process_version is not None:
        process_version = _bounded_component("process_version", process_version)
    if policy_ref is not None:
        policy_ref = _bounded_component("policy_ref", policy_ref)
    if correlation_id is not None:
        correlation_id = _bounded_component("correlation_id", correlation_id)
    if parent_event_id is not None:
        parent_event_id = _bounded_component("parent_event_id", parent_event_id)
    if safe_summary is not None:
        if not isinstance(safe_summary, str) or len(safe_summary) > MAX_SAFE_SUMMARY_CHARS:
            raise RestrictionProvenanceError(
                f"safe_summary must be at most {MAX_SAFE_SUMMARY_CHARS} characters"
            )
        if raw_generated is not None and safe_summary == raw_generated:
            raise RestrictionProvenanceError(
                "safe_summary must not be the raw generated restricted content"
            )
        if raw_input is not None and safe_summary == raw_input:
            raise RestrictionProvenanceError(
                "safe_summary must not be the raw restricted input"
            )

    timestamp = occurred_at or _utc_now()
    _validate_timestamp(timestamp)
    safe_metadata = _sanitize_metadata(metadata)
    try:
        safe_metadata, safe_summary = validate_restriction_context(
            source_system=source_system,
            processor=processor,
            metadata=safe_metadata,
            safe_summary=safe_summary,
        )
    except RestrictionContextPolicyError as exc:
        raise RestrictionProvenanceError(str(exc)) from exc

    input_fp = _fingerprint(fingerprint_key, "input", raw_input)
    generated_fp = _fingerprint(fingerprint_key, "generated", raw_generated)
    safe_output_fp = _fingerprint(fingerprint_key, "safe-output", safe_output)

    identity_document = {
        "schema": RESTRICTION_SCHEMA,
        "authority": RESTRICTION_AUTHORITY,
        "fingerprint_key_id": fingerprint_key_id,
        "occurred_at": timestamp,
        "action": action,
        "reason_code": reason_code,
        "source_system": source_system,
        "processor": processor,
        "process_version": process_version,
        "policy_ref": policy_ref,
        "correlation_id": correlation_id,
        "parent_event_id": parent_event_id,
        "input_fingerprint": input_fp,
        "generated_fingerprint": generated_fp,
        "safe_output_fingerprint": safe_output_fp,
        "safe_summary": safe_summary,
        "metadata": safe_metadata,
        "raw_content_persisted": False,
    }
    restriction_id = hashlib.sha256(_canonical_json(identity_document).encode("utf-8")).hexdigest()[:32]

    return RestrictionEvidence(
        restriction_id=restriction_id,
        authority=RESTRICTION_AUTHORITY,
        fingerprint_key_id=fingerprint_key_id,
        occurred_at=timestamp,
        action=action,
        reason_code=reason_code,
        source_system=source_system,
        processor=processor,
        process_version=process_version,
        policy_ref=policy_ref,
        correlation_id=correlation_id,
        parent_event_id=parent_event_id,
        input_fingerprint=input_fp,
        generated_fingerprint=generated_fp,
        safe_output_fingerprint=safe_output_fp,
        safe_summary=safe_summary,
        metadata=safe_metadata,
    )


def queue_restriction_event(
    registry: dict[str, Any],
    evidence: RestrictionEvidence,
) -> tuple[dict[str, Any], str]:
    """Fail closed for unsigned new restriction events.

    G6 requires an externally signed PRIME attestation before a restriction may
    enter the governed SARA -> ECHO outbox. Historical V1-V3 evidence remains
    readable, but this unsigned queue path is intentionally retired.
    """
    del registry, evidence
    raise RestrictionProvenanceError(
        "unsigned restriction queueing is disabled; use queue_signed_restriction_event"
    )


def build_remediation_directive(
    evidence: RestrictionEvidence,
    *,
    action: str,
    requested_by: str,
    rationale_code: str | None = None,
) -> dict[str, Any]:
    """Bind an allowed remediation to a restriction without carrying raw content."""
    normalized = action.strip().upper() if isinstance(action, str) else ""
    if normalized in _FORBIDDEN_REMEDIATIONS or normalized not in _ALLOWED_REMEDIATIONS:
        raise RestrictionProvenanceError(
            "remediation must not replay raw content, bypass policy, or disable filtering"
        )
    requested_by = _bounded_component("requested_by", requested_by)
    if rationale_code is not None:
        rationale_code = _bounded_component("rationale_code", rationale_code)
    directive = {
        "schema": REMEDIATION_SCHEMA,
        "restriction_id": evidence.restriction_id,
        "restriction_event_id": evidence.outbox_event_id,
        "action": normalized,
        "requested_by": requested_by,
        "rationale_code": rationale_code,
        "created_at": _utc_now(),
        "content_binding": {
            "input_fingerprint": evidence.input_fingerprint,
            "generated_fingerprint": evidence.generated_fingerprint,
            "fingerprint_key_id": evidence.fingerprint_key_id,
        },
        "raw_content_included": False,
    }
    validate_json_resource(directive)
    return directive
