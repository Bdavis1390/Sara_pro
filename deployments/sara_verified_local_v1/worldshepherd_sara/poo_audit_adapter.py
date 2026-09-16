from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any

from .event_outbox import queue_events_outbox_patch


POO_AUDIT_SCHEMA = "WS-POO-GOVERNANCE-DECISION-V3"
POO_EVENT_SCHEMA = "WS-POO-SARA-AUDIT-EVENT-V3"
AUDIT_INSTANCE_PREFIX = "POO-AUDIT-"
_AUDIT_INSTANCE_PATTERN = re.compile(r"^POO-AUDIT-[0-9a-f]{32}$")
_VALID_OPERATIONS = frozenset(
    {
        "OWNERSHIP_ATTESTATION",
        "COC_ATTESTATION",
        "TRANSFER_READINESS",
        "RECOVERY_READINESS",
        "TECHNICAL_STATE_TRANSITION",
        "GOVERNED_STATE_TRANSITION",
        "STATE_LINEAGE_INTEGRITY",
        "REGISTRY_HEALTH",
        "REGISTRY_COMMIT_READINESS",
    }
)
_OPERATION_READINESS_FIELD = {
    "OWNERSHIP_ATTESTATION": "technical_attestation_ready",
    "COC_ATTESTATION": "coc_valid",
    "TRANSFER_READINESS": "transfer_ready",
    "RECOVERY_READINESS": "recovery_ready",
    "TECHNICAL_STATE_TRANSITION": "state_transition_ready",
    "GOVERNED_STATE_TRANSITION": "state_transition_ready",
    "STATE_LINEAGE_INTEGRITY": None,
    "REGISTRY_HEALTH": "registry_consistent",
    "REGISTRY_COMMIT_READINESS": "registry_commit_ready",
}
_PRIMARY_READINESS_FIELDS = (
    "technical_attestation_ready",
    "coc_valid",
    "transfer_ready",
    "recovery_ready",
    "state_transition_ready",
    "registry_consistent",
    "registry_commit_ready",
)
_LINEAGE_BOOL_FIELDS = (
    "state_lineage_checked",
    "state_lineage_valid",
    "poo_lineage_valid",
    "coc_lineage_valid",
    "generation_valid",
    "fork_detected",
    "cycle_detected",
)
_FORBIDDEN_TRUE_FIELDS = (
    "ownership_changed",
    "transfer_executed",
    "live_value_authorized",
    "legal_title_established",
    "legal_title_transferred",
    "control_rotated",
    "technical_registry_committed",
    "durable_registry_write_authorized",
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
        "coc_valid",
        "transfer_ready",
        "recovery_ready",
        "state_transition_ready",
        "registry_consistent",
        "state_lineage_checked",
        "state_lineage_valid",
        "poo_lineage_valid",
        "coc_lineage_valid",
        "generation_valid",
        "fork_detected",
        "cycle_detected",
        "active_tip_digest",
        "lineage_issue_count",
        "registry_commit_ready",
        "optimistic_concurrency_checked",
        "optimistic_concurrency_match",
        "expected_registry_digest",
        "current_registry_digest",
        "candidate_registry_digest",
        "candidate_state_digest",
        "human_approval_required",
        "ownership_changed",
        "transfer_executed",
        "live_value_authorized",
        "legal_title_established",
        "legal_title_transferred",
        "control_rotated",
        "technical_registry_committed",
        "durable_registry_write_authorized",
        "conflict_winner_selected",
        "lineage_auto_resolved",
        "claim_boundary",
    }
)
_LINEAGE_OPERATIONS = frozenset(
    {"STATE_LINEAGE_INTEGRITY", "GOVERNED_STATE_TRANSITION", "REGISTRY_COMMIT_READINESS"}
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


def _optional_nonempty_string(projection: dict[str, Any], field: str) -> str | None:
    value = projection.get(field)
    if value is not None and (not isinstance(value, str) or not value):
        raise PoOAuditAdapterError(f"{field} must be null or a non-empty string")
    return value


def _validate_primary_readiness(projection: dict[str, Any], operation: str) -> None:
    for field in _PRIMARY_READINESS_FIELDS:
        if not isinstance(projection.get(field), bool):
            raise PoOAuditAdapterError(f"{field} must be boolean")
    allowed = _OPERATION_READINESS_FIELD[operation]
    for field in _PRIMARY_READINESS_FIELDS:
        if field != allowed and projection[field]:
            raise PoOAuditAdapterError(f"{field} mismatches operation")


def _validate_lineage_semantics(projection: dict[str, Any], operation: str) -> None:
    for field in _LINEAGE_BOOL_FIELDS:
        if not isinstance(projection.get(field), bool):
            raise PoOAuditAdapterError(f"{field} must be boolean")
    issue_count = projection.get("lineage_issue_count")
    if not isinstance(issue_count, int) or isinstance(issue_count, bool) or issue_count < 0:
        raise PoOAuditAdapterError("lineage_issue_count must be a non-negative integer")
    active_tip = _optional_nonempty_string(projection, "active_tip_digest")

    if operation not in _LINEAGE_OPERATIONS:
        if any(projection[field] for field in _LINEAGE_BOOL_FIELDS):
            raise PoOAuditAdapterError("lineage state mismatches operation")
        if active_tip is not None or issue_count != 0:
            raise PoOAuditAdapterError("lineage detail must be empty outside lineage-aware operations")
        return

    if projection["state_lineage_checked"] is not True:
        raise PoOAuditAdapterError(f"{operation} requires state_lineage_checked=true")

    if projection["state_lineage_valid"]:
        if not (
            projection["poo_lineage_valid"]
            and projection["coc_lineage_valid"]
            and projection["generation_valid"]
        ):
            raise PoOAuditAdapterError("valid state lineage requires PoO, COC, and generation validity")
        if projection["fork_detected"] or projection["cycle_detected"]:
            raise PoOAuditAdapterError("valid state lineage cannot report fork/cycle conflict")
        if active_tip is None:
            raise PoOAuditAdapterError("valid state lineage requires active_tip_digest")
        if issue_count != 0:
            raise PoOAuditAdapterError("valid state lineage requires zero lineage issues")
    else:
        if active_tip is not None:
            raise PoOAuditAdapterError("invalid state lineage cannot expose active_tip_digest")
        if issue_count < 1:
            raise PoOAuditAdapterError("invalid state lineage requires at least one lineage issue")

    if operation == "STATE_LINEAGE_INTEGRITY":
        if projection.get("previous_poo_digest") is not None:
            raise PoOAuditAdapterError("STATE_LINEAGE_INTEGRITY previous_poo_digest must be null")
        if any(projection[field] for field in _PRIMARY_READINESS_FIELDS):
            raise PoOAuditAdapterError("state lineage integrity cannot grant operation readiness")
    elif operation == "GOVERNED_STATE_TRANSITION":
        previous = projection.get("previous_poo_digest")
        if not isinstance(previous, str) or not previous:
            raise PoOAuditAdapterError("GOVERNED_STATE_TRANSITION requires previous_poo_digest")
        if projection["state_transition_ready"]:
            if not projection["state_lineage_valid"]:
                raise PoOAuditAdapterError("governed state readiness requires valid state lineage")
            if previous != active_tip:
                raise PoOAuditAdapterError(
                    "governed state readiness requires previous_poo_digest to equal active_tip_digest"
                )
    elif operation == "REGISTRY_COMMIT_READINESS":
        previous = projection.get("previous_poo_digest")
        if not isinstance(previous, str) or not previous:
            raise PoOAuditAdapterError("REGISTRY_COMMIT_READINESS requires previous_poo_digest")
        if projection["registry_commit_ready"]:
            if not projection["state_lineage_valid"]:
                raise PoOAuditAdapterError("registry commit readiness requires valid state lineage")
            if previous != active_tip:
                raise PoOAuditAdapterError(
                    "registry commit readiness requires previous_poo_digest to equal active_tip_digest"
                )


def _validate_concurrency_semantics(projection: dict[str, Any], operation: str) -> None:
    for field in ("optimistic_concurrency_checked", "optimistic_concurrency_match"):
        if not isinstance(projection.get(field), bool):
            raise PoOAuditAdapterError(f"{field} must be boolean")
    expected = _optional_nonempty_string(projection, "expected_registry_digest")
    current = _optional_nonempty_string(projection, "current_registry_digest")
    candidate_registry = _optional_nonempty_string(projection, "candidate_registry_digest")
    candidate_state = _optional_nonempty_string(projection, "candidate_state_digest")

    if operation != "REGISTRY_COMMIT_READINESS":
        if projection["registry_commit_ready"]:
            raise PoOAuditAdapterError("registry_commit_ready mismatches operation")
        if projection["optimistic_concurrency_checked"] or projection["optimistic_concurrency_match"]:
            raise PoOAuditAdapterError("optimistic concurrency state mismatches operation")
        if any(value is not None for value in (expected, current, candidate_registry)):
            raise PoOAuditAdapterError("registry digest detail mismatches operation")
        if operation not in {"TECHNICAL_STATE_TRANSITION", "GOVERNED_STATE_TRANSITION"} and candidate_state is not None:
            raise PoOAuditAdapterError("candidate_state_digest mismatches operation")
        return

    if projection["optimistic_concurrency_checked"] is not True:
        raise PoOAuditAdapterError("REGISTRY_COMMIT_READINESS requires optimistic_concurrency_checked=true")
    if expected is None or current is None:
        raise PoOAuditAdapterError("registry commit readiness requires expected/current registry digests")
    if projection["optimistic_concurrency_match"] != (expected == current):
        raise PoOAuditAdapterError("optimistic_concurrency_match conflicts with registry digests")
    if projection["registry_commit_ready"]:
        if not projection["optimistic_concurrency_match"]:
            raise PoOAuditAdapterError("registry commit readiness requires a matching registry snapshot")
        if candidate_registry is None or candidate_state is None:
            raise PoOAuditAdapterError("ready registry commit requires candidate registry/state digests")


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

    _optional_nonempty_string(projection, "previous_poo_digest")

    if projection.get("human_approval_required") is not True:
        raise PoOAuditAdapterError("PoO decisions must preserve the human approval gate")

    for field in _FORBIDDEN_TRUE_FIELDS:
        if projection.get(field) is not False:
            raise PoOAuditAdapterError(f"{field} must remain false at the SARA audit boundary")

    _validate_primary_readiness(projection, str(operation))
    _validate_lineage_semantics(projection, str(operation))
    _validate_concurrency_semantics(projection, str(operation))

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
        "state_lineage_checked": record["state_lineage_checked"],
        "state_lineage_valid": record["state_lineage_valid"],
        "poo_lineage_valid": record["poo_lineage_valid"],
        "coc_lineage_valid": record["coc_lineage_valid"],
        "generation_valid": record["generation_valid"],
        "fork_detected": record["fork_detected"],
        "cycle_detected": record["cycle_detected"],
        "active_tip_digest": record["active_tip_digest"],
        "lineage_issue_count": record["lineage_issue_count"],
        "registry_commit_ready": record["registry_commit_ready"],
        "optimistic_concurrency_checked": record["optimistic_concurrency_checked"],
        "optimistic_concurrency_match": record["optimistic_concurrency_match"],
        "expected_registry_digest": record["expected_registry_digest"],
        "current_registry_digest": record["current_registry_digest"],
        "candidate_registry_digest": record["candidate_registry_digest"],
        "candidate_state_digest": record["candidate_state_digest"],
        "human_approval_required": True,
        "ownership_changed": False,
        "transfer_executed": False,
        "live_value_authorized": False,
        "legal_title_established": False,
        "legal_title_transferred": False,
        "control_rotated": False,
        "technical_registry_committed": False,
        "durable_registry_write_authorized": False,
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
