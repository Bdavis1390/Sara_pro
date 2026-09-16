from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any

from .event_outbox import queue_events_outbox_patch


QCRYPTO_AUDIT_SCHEMA = "WS-QCRYPTO-CONTROL-DECISION-V1"
QCRYPTO_EVENT_SCHEMA = "WS-QCRYPTO-SARA-AUDIT-EVENT-V1"
AUDIT_INSTANCE_PREFIX = "QCRYPTO-AUDIT-"
_AUDIT_INSTANCE_PATTERN = re.compile(r"^QCRYPTO-AUDIT-[0-9a-f]{32}$")
_FORBIDDEN_TRUE_FIELDS = (
    "migration_executed",
    "execution_authority",
    "live_value_authorized",
    "federal_compliance_established",
    "ws_cae_conformance_established",
)
_STAGE_FIELDS = (
    ("ECHO", "echo_state", "qcrypto_echo_state"),
    ("PRIME", "prime_state", "qcrypto_prime_state"),
    ("SARA", "sara_state", "qcrypto_sara_state"),
    ("OVERWATCH", "overwatch_state", "qcrypto_overwatch_state"),
)
_REQUIRED_FIELDS = frozenset(
    {
        "schema",
        "asset_id",
        "echo_state",
        "prime_state",
        "sara_state",
        "overwatch_state",
        "priority",
        "human_approval_required",
        "migration_executed",
        "execution_authority",
        "live_value_authorized",
        "federal_compliance_established",
        "ws_cae_conformance_established",
        "claim_boundary",
    }
)


class QCryptoAuditAdapterError(ValueError):
    pass


def new_qcrypto_audit_instance_id() -> str:
    """Create a server-side identity for one concrete four-event audit submission."""
    return AUDIT_INSTANCE_PREFIX + uuid.uuid4().hex


def validate_qcrypto_audit_instance_id(value: str) -> str:
    if not isinstance(value, str) or not _AUDIT_INSTANCE_PATTERN.fullmatch(value):
        raise QCryptoAuditAdapterError(
            "audit_instance_id must be a server-format QCRYPTO audit instance ID"
        )
    return value


def _validated_projection(projection: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(projection, dict):
        raise QCryptoAuditAdapterError("QCRYPTO audit projection must be a JSON object")
    missing = sorted(_REQUIRED_FIELDS.difference(projection))
    if missing:
        raise QCryptoAuditAdapterError(
            "QCRYPTO audit projection is missing required fields: " + ", ".join(missing)
        )
    if projection.get("schema") != QCRYPTO_AUDIT_SCHEMA:
        raise QCryptoAuditAdapterError("unsupported QCRYPTO audit projection schema")
    if not isinstance(projection.get("asset_id"), str) or not projection["asset_id"]:
        raise QCryptoAuditAdapterError("asset_id must be a non-empty string")
    if projection.get("human_approval_required") is not True:
        raise QCryptoAuditAdapterError("QCRYPTO decisions must preserve the human approval gate")
    for field in _FORBIDDEN_TRUE_FIELDS:
        if projection.get(field) is not False:
            raise QCryptoAuditAdapterError(f"{field} must remain false at the SARA audit boundary")
    for _stage, state_field, _event_name in _STAGE_FIELDS:
        state = projection.get(state_field)
        if not isinstance(state, str) or not state:
            raise QCryptoAuditAdapterError(f"{state_field} must be a non-empty string")
    priority = projection.get("priority")
    if not isinstance(priority, str) or not priority:
        raise QCryptoAuditAdapterError("priority must be a non-empty string")
    claim_boundary = projection.get("claim_boundary")
    if not isinstance(claim_boundary, str) or not claim_boundary:
        raise QCryptoAuditAdapterError("claim_boundary must be a non-empty string")
    correlation_id = projection.get("correlation_id")
    if correlation_id is not None and (
        not isinstance(correlation_id, str) or not correlation_id
    ):
        raise QCryptoAuditAdapterError("correlation_id must be a non-empty string when supplied")
    return dict(projection)


def qcrypto_decision_digest(projection: dict[str, Any]) -> str:
    """Return a deterministic content digest for one validated decision projection.

    The digest describes semantic decision content. It intentionally excludes the
    server-generated audit-instance identity so identical decisions retain the
    same digest while separate submissions remain distinguishable in SARA.
    """
    record = _validated_projection(projection)
    canonical = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def qcrypto_outbox_events(
    projection: dict[str, Any],
    *,
    actor: str,
    audit_instance_id: str | None = None,
) -> list[dict[str, Any]]:
    """Convert one governed decision into one four-event SARA audit instance."""
    if not isinstance(actor, str) or not actor:
        raise QCryptoAuditAdapterError("actor must be a non-empty string")
    record = _validated_projection(projection)
    instance_id = validate_qcrypto_audit_instance_id(
        audit_instance_id or new_qcrypto_audit_instance_id()
    )
    decision_digest = qcrypto_decision_digest(record)
    common = {
        "schema": QCRYPTO_EVENT_SCHEMA,
        "source_schema": record["schema"],
        "decision_digest": decision_digest,
        "audit_instance_id": instance_id,
        "asset_id": record["asset_id"],
        "priority": record["priority"],
        "human_approval_required": True,
        "migration_executed": False,
        "execution_authority": False,
        "live_value_authorized": False,
        "federal_compliance_established": False,
        "ws_cae_conformance_established": False,
        "claim_boundary": record["claim_boundary"],
    }
    if "correlation_id" in record:
        common["correlation_id"] = record["correlation_id"]

    events: list[dict[str, Any]] = []
    for stage, state_field, event_name in _STAGE_FIELDS:
        payload = dict(common)
        payload.update({"stage": stage, "state": record[state_field]})
        events.append({"event": event_name, "actor": actor, "payload": payload})
    return events


def queue_qcrypto_projection_patch(
    registry: dict[str, Any],
    projection: dict[str, Any],
    *,
    actor: str,
    audit_instance_id: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Queue QCRYPTO governance evidence into SARA's native durable outbox."""
    events = qcrypto_outbox_events(
        projection,
        actor=actor,
        audit_instance_id=audit_instance_id,
    )
    return queue_events_outbox_patch(registry, events)
