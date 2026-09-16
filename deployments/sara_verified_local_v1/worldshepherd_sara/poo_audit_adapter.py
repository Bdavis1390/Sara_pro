from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any

from .event_outbox import queue_events_outbox_patch


POO_AUDIT_SCHEMA = "WS-POO-GOVERNANCE-DECISION-V2"
POO_EVENT_SCHEMA = "WS-POO-SARA-AUDIT-EVENT-V2"
AUDIT_INSTANCE_PREFIX = "POO-AUDIT-"
_AUDIT_INSTANCE_PATTERN = re.compile(r"^POO-AUDIT-[0-9a-f]{32}$")
_VALID_OPERATIONS = frozenset(
    {
        "OWNERSHIP_ATTESTATION",
        "COC_ATTESTATION",
        "TRANSFER_READINESS",
        "RECOVERY_READINESS",
        "TECHNICAL_STATE_TRANSITION",
        "REGISTRY_HEALTH",
    }
)
_OPERATION_READINESS_FIELD = {
    "OWNERSHIP_ATTESTATION": "technical_attestation_ready",
    "COC_ATTESTATION": "coc_valid",
    "TRANSFER_READINESS": "transfer_ready",
    "RECOVERY_READINESS": "recovery_ready",
    "TECHNICAL_STATE_TRANSITION": "state_transition_ready",
    "REGISTRY_HEALTH": "registry_consistent",
}
_READINESS_FIELDS = tuple(_OPERATION_READINESS_FIELD.values())
_FORBIDDEN_TRUE_FIELDS = (
    "ownership_changed",
    "transfer_executed",
    "live_value_authorized",
    "legal_title_established",
    "legal_title_transferred",
    "control_rotated",
)
_STAGE_FIELDS = (
    ("ECHO", "echo_state", "poo_echo_state"),
    ("PRIME", "prime_state", "poo_prime_state"),
    ("SARA", "sara_state", "poo_sara_state"),
    ("OVERWATCH", "overwatch_state", "poo_overwatch_state"),
)
_REQUIRED_FIELDS = frozenset(
    {
        "schema",
        "operation",
        "asset_id",
        "source_digest",
        "source_status",
        "previous_poo_digest",
        "echo_state",
        "prime_state",
        "sara_state",
        "overwatch_state",
        "technical_attestation_ready",
        "coc_valid",
        "transfer_ready",
        "recovery_ready",
        "state_transition_ready",
        "registry_consistent",
        "human_approval_required",
        "ownership_changed",
        "transfer_executed",
        "live_value_authorized",
        "legal_title_established",
        "legal_title_transferred",
        "control_rotated",
        "claim_boundary",
    }
)


class PoOAuditAdapterError(ValueError):
    pass


def new_poo_audit_instance_id() -> str:
    return AUDIT_INSTANCE_PREFIX + uuid.uuid4().hex


def validate_poo_audit_instance_id(value: str) -> str:
    if not isinstance(value, str) or not _AUDIT_INSTANCE_PATTERN.fullmatch(value):
        raise PoOAuditAdapterError(
            "audit_instance_id must be a server-format PoO audit instance ID"
        )
    return value


def _validated_projection(projection: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(projection, dict):
        raise PoOAuditAdapterError("PoO audit projection must be a JSON object")
    missing = sorted(_REQUIRED_FIELDS.difference(projection))
    if missing:
        raise PoOAuditAdapterError(
            "PoO audit projection is missing required fields: " + ", ".join(missing)
        )
    if projection.get("schema") != POO_AUDIT_SCHEMA:
        raise PoOAuditAdapterError("unsupported PoO audit projection schema")

    operation = projection.get("operation")
    if operation not in _VALID_OPERATIONS:
        raise PoOAuditAdapterError("unsupported PoO operation")

    for field in ("asset_id", "source_digest", "source_status", "claim_boundary"):
        value = projection.get(field)
        if not isinstance(value, str) or not value:
            raise PoOAuditAdapterError(f"{field} must be a non-empty string")

    previous = projection.get("previous_poo_digest")
    if previous is not None and (not isinstance(previous, str) or not previous):
        raise PoOAuditAdapterError(
            "previous_poo_digest must be null or a non-empty string"
        )

    if projection.get("human_approval_required") is not True:
        raise PoOAuditAdapterError("PoO decisions must preserve the human approval gate")

    for field in _FORBIDDEN_TRUE_FIELDS:
        if projection.get(field) is not False:
            raise PoOAuditAdapterError(f"{field} must remain false at the SARA audit boundary")

    for field in _READINESS_FIELDS:
        if not isinstance(projection.get(field), bool):
            raise PoOAuditAdapterError(f"{field} must be boolean")

    allowed_true_field = _OPERATION_READINESS_FIELD[operation]
    for field in _READINESS_FIELDS:
        if field != allowed_true_field and projection[field]:
            raise PoOAuditAdapterError(f"{field} mismatches operation")

    for _stage, state_field, _event_name in _STAGE_FIELDS:
        state = projection.get(state_field)
        if not isinstance(state, str) or not state:
            raise PoOAuditAdapterError(f"{state_field} must be a non-empty string")

    return dict(projection)


def poo_decision_digest(projection: dict[str, Any]) -> str:
    record = _validated_projection(projection)
    canonical = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def poo_outbox_events(
    projection: dict[str, Any],
    *,
    actor: str,
    audit_instance_id: str | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(actor, str) or not actor:
        raise PoOAuditAdapterError("actor must be a non-empty string")
    record = _validated_projection(projection)
    instance_id = validate_poo_audit_instance_id(
        audit_instance_id or new_poo_audit_instance_id()
    )
    decision_digest = poo_decision_digest(record)

    common = {
        "schema": POO_EVENT_SCHEMA,
        "source_schema": record["schema"],
        "decision_digest": decision_digest,
        "audit_instance_id": instance_id,
        "operation": record["operation"],
        "asset_id": record["asset_id"],
        "source_digest": record["source_digest"],
        "source_status": record["source_status"],
        "previous_poo_digest": record["previous_poo_digest"],
        "technical_attestation_ready": record["technical_attestation_ready"],
        "coc_valid": record["coc_valid"],
        "transfer_ready": record["transfer_ready"],
        "recovery_ready": record["recovery_ready"],
        "state_transition_ready": record["state_transition_ready"],
        "registry_consistent": record["registry_consistent"],
        "human_approval_required": True,
        "ownership_changed": False,
        "transfer_executed": False,
        "live_value_authorized": False,
        "legal_title_established": False,
        "legal_title_transferred": False,
        "control_rotated": False,
        "claim_boundary": record["claim_boundary"],
    }

    events: list[dict[str, Any]] = []
    for stage, state_field, event_name in _STAGE_FIELDS:
        payload = dict(common)
        payload.update({"stage": stage, "state": record[state_field]})
        events.append({"event": event_name, "actor": actor, "payload": payload})
    return events


def queue_poo_projection_patch(
    registry: dict[str, Any],
    projection: dict[str, Any],
    *,
    actor: str,
    audit_instance_id: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    events = poo_outbox_events(
        projection,
        actor=actor,
        audit_instance_id=audit_instance_id,
    )
    return queue_events_outbox_patch(registry, events)
