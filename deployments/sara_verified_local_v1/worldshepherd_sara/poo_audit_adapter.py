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
        "TRANSFER_READINESS",
        "RECOVERY_READINESS",
        "LINEAGE_INTEGRITY",
    }
)
_VALID_LINEAGE_CONFLICT_TYPES = frozenset({"NONE", "FORK", "CYCLE", "STRUCTURAL", "MULTIPLE"})
_FORBIDDEN_TRUE_FIELDS = (
    "ownership_changed",
    "transfer_executed",
    "live_value_authorized",
    "legal_title_established",
    "legal_title_transferred",
    "control_rotated",
    "conflict_winner_selected",
    "lineage_auto_resolved",
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
        "transfer_ready",
        "recovery_ready",
        "lineage_checked",
        "lineage_valid",
        "fork_detected",
        "cycle_detected",
        "active_tip_digest",
        "lineage_issue_count",
        "lineage_conflict_type",
        "human_approval_required",
        "ownership_changed",
        "transfer_executed",
        "live_value_authorized",
        "legal_title_established",
        "legal_title_transferred",
        "control_rotated",
        "conflict_winner_selected",
        "lineage_auto_resolved",
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


def _validate_checked_lineage(
    projection: dict[str, Any],
    *,
    active_tip: str | None,
    issue_count: int,
    conflict_type: str,
) -> None:
    if projection["lineage_valid"]:
        if projection["fork_detected"] or projection["cycle_detected"]:
            raise PoOAuditAdapterError("valid lineage cannot report fork/cycle conflict")
        if active_tip is None:
            raise PoOAuditAdapterError("valid lineage requires one active_tip_digest")
        if issue_count != 0 or conflict_type != "NONE":
            raise PoOAuditAdapterError("valid lineage requires zero issues and conflict type NONE")
    else:
        if active_tip is not None:
            raise PoOAuditAdapterError("invalid lineage cannot expose an active technical tip")
        if issue_count < 1:
            raise PoOAuditAdapterError("invalid lineage requires at least one issue")
        if conflict_type == "NONE":
            raise PoOAuditAdapterError("invalid lineage requires a conflict type")
        if projection["fork_detected"] and conflict_type not in {"FORK", "MULTIPLE"}:
            raise PoOAuditAdapterError("fork_detected conflicts with lineage_conflict_type")
        if projection["cycle_detected"] and conflict_type not in {"CYCLE", "MULTIPLE"}:
            raise PoOAuditAdapterError("cycle_detected conflicts with lineage_conflict_type")


def _validate_lineage_semantics(projection: dict[str, Any], operation: str) -> None:
    for field in ("lineage_checked", "lineage_valid", "fork_detected", "cycle_detected"):
        if not isinstance(projection.get(field), bool):
            raise PoOAuditAdapterError(f"{field} must be boolean")

    issue_count = projection.get("lineage_issue_count")
    if not isinstance(issue_count, int) or isinstance(issue_count, bool) or issue_count < 0:
        raise PoOAuditAdapterError("lineage_issue_count must be a non-negative integer")

    conflict_type = projection.get("lineage_conflict_type")
    if conflict_type not in _VALID_LINEAGE_CONFLICT_TYPES:
        raise PoOAuditAdapterError("unsupported lineage_conflict_type")

    active_tip = projection.get("active_tip_digest")
    if active_tip is not None and (not isinstance(active_tip, str) or not active_tip):
        raise PoOAuditAdapterError("active_tip_digest must be null or a non-empty string")

    if operation == "OWNERSHIP_ATTESTATION":
        if projection["lineage_checked"]:
            raise PoOAuditAdapterError("ownership attestation cannot assert lineage_checked")
        if any((projection["lineage_valid"], projection["fork_detected"], projection["cycle_detected"])):
            raise PoOAuditAdapterError("ownership attestation must not carry lineage decision state")
        if active_tip is not None or issue_count != 0 or conflict_type != "NONE":
            raise PoOAuditAdapterError("ownership attestation lineage detail must be empty")
        return

    if projection["lineage_checked"] is not True:
        raise PoOAuditAdapterError(f"{operation} requires lineage_checked=true")

    _validate_checked_lineage(
        projection,
        active_tip=active_tip,
        issue_count=issue_count,
        conflict_type=str(conflict_type),
    )

    if operation == "LINEAGE_INTEGRITY":
        if projection.get("previous_poo_digest") is not None:
            raise PoOAuditAdapterError("LINEAGE_INTEGRITY previous_poo_digest must be null")
        if any(
            (
                projection["technical_attestation_ready"],
                projection["transfer_ready"],
                projection["recovery_ready"],
            )
        ):
            raise PoOAuditAdapterError("lineage operation cannot grant ownership/transfer/recovery readiness")
        return

    previous = projection.get("previous_poo_digest")
    if not isinstance(previous, str) or not previous:
        raise PoOAuditAdapterError(f"{operation} requires previous_poo_digest")

    if operation == "TRANSFER_READINESS":
        if projection["transfer_ready"] and not projection["lineage_valid"]:
            raise PoOAuditAdapterError("transfer_ready requires a valid lineage")
        if projection["transfer_ready"] and previous != active_tip:
            raise PoOAuditAdapterError("transfer_ready requires previous_poo_digest to equal active_tip_digest")
    elif operation == "RECOVERY_READINESS":
        if projection["recovery_ready"] and not projection["lineage_valid"]:
            raise PoOAuditAdapterError("recovery_ready requires a valid lineage")
        if projection["recovery_ready"] and previous != active_tip:
            raise PoOAuditAdapterError("recovery_ready requires previous_poo_digest to equal active_tip_digest")


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

    for field in ("technical_attestation_ready", "transfer_ready", "recovery_ready"):
        if not isinstance(projection.get(field), bool):
            raise PoOAuditAdapterError(f"{field} must be boolean")

    if operation != "OWNERSHIP_ATTESTATION" and projection["technical_attestation_ready"]:
        raise PoOAuditAdapterError("technical_attestation_ready mismatches operation")
    if operation != "TRANSFER_READINESS" and projection["transfer_ready"]:
        raise PoOAuditAdapterError("transfer_ready mismatches operation")
    if operation != "RECOVERY_READINESS" and projection["recovery_ready"]:
        raise PoOAuditAdapterError("recovery_ready mismatches operation")

    _validate_lineage_semantics(projection, str(operation))

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
        "transfer_ready": record["transfer_ready"],
        "recovery_ready": record["recovery_ready"],
        "lineage_checked": record["lineage_checked"],
        "lineage_valid": record["lineage_valid"],
        "fork_detected": record["fork_detected"],
        "cycle_detected": record["cycle_detected"],
        "active_tip_digest": record["active_tip_digest"],
        "lineage_issue_count": record["lineage_issue_count"],
        "lineage_conflict_type": record["lineage_conflict_type"],
        "human_approval_required": True,
        "ownership_changed": False,
        "transfer_executed": False,
        "live_value_authorized": False,
        "legal_title_established": False,
        "legal_title_transferred": False,
        "control_rotated": False,
        "conflict_winner_selected": False,
        "lineage_auto_resolved": False,
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
