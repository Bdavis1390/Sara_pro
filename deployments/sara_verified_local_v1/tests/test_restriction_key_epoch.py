from __future__ import annotations

import copy
import hashlib
import json
import re

import pytest

from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.restriction_observability import (
    RestrictionObservabilityError,
    project_restriction_audit_record,
)
from worldshepherd_sara.restriction_provenance import (
    RESTRICTION_AUTHORITY,
    RESTRICTION_EVENT,
    RESTRICTION_SCHEMA,
    RESTRICTION_SCHEMA_V2,
    build_remediation_directive,
    capture_restriction,
)


KEY_A = b"worldshepherd-g5-key-epoch-a-32-bytes-minimum"
KEY_B = b"worldshepherd-g5-key-epoch-b-32-bytes-minimum"
APPROVED_SUMMARY = "Output was restricted; only bounded provenance is retained."
BASELINE_RESIDUAL_RISK_UNITS = 4
MAX_RESIDUAL_RATIO = 0.10


def evidence(key: bytes = KEY_A):
    return capture_restriction(
        fingerprint_key=key,
        action="BLOCK",
        reason_code="POLICY.KEY_EPOCH_TEST",
        source_system="CHAT_ASSISTANT",
        processor="POLICY_GATE",
        process_version="v3",
        policy_ref="CONTENT_POLICY",
        correlation_id="key-epoch-001",
        raw_input="same sensitive input",
        raw_generated="same restricted generated content",
        safe_summary=APPROVED_SUMMARY,
        metadata={
            "stage": "post_generation_policy_check",
            "claims_state": "IMPLEMENTED_IN_SOFTWARE",
            "attempt": 1,
        },
        occurred_at="2026-09-17T23:00:00+00:00",
    )


def audit_record(item) -> dict:
    payload = item.semantic_document()
    payload["_outbox_event_id"] = item.outbox_event_id
    payload["_delivery_semantics"] = "AT_LEAST_ONCE"
    return AuditRecord(
        timestamp="2026-09-17T23:00:01+00:00",
        event=RESTRICTION_EVENT,
        actor=RESTRICTION_AUTHORITY,
        payload=payload,
    ).model_dump(mode="json")


def canonical_id(payload: dict) -> str:
    identity = {
        key: value
        for key, value in payload.items()
        if key not in {"restriction_id", "_outbox_event_id", "_delivery_semantics"}
    }
    encoded = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:32]


def test_v3_binds_opaque_fingerprint_key_epoch_id():
    item = evidence()
    document = item.semantic_document()

    assert RESTRICTION_SCHEMA.endswith("V3")
    assert re.fullmatch(r"[0-9a-f]{32}", item.fingerprint_key_epoch_id)
    assert document["fingerprint_key_epoch_id"] == item.fingerprint_key_epoch_id
    serialized = json.dumps(document, sort_keys=True)
    assert KEY_A.decode("utf-8") not in serialized


def test_same_key_same_epoch_and_rotated_key_changes_epoch():
    first = evidence(KEY_A)
    replay = evidence(KEY_A)
    rotated = evidence(KEY_B)

    assert first.fingerprint_key_epoch_id == replay.fingerprint_key_epoch_id
    assert first.fingerprint_key_epoch_id != rotated.fingerprint_key_epoch_id
    assert first.input_fingerprint == replay.input_fingerprint
    assert first.input_fingerprint != rotated.input_fingerprint


def test_projection_exposes_epoch_identifier_without_secret_material():
    item = evidence()
    projected = project_restriction_audit_record(audit_record(item))

    assert projected["fingerprint_epoch_bound_in_payload"] is True
    assert projected["fingerprint_key_epoch_id"] == item.fingerprint_key_epoch_id
    serialized = json.dumps(projected, sort_keys=True)
    assert KEY_A.decode("utf-8") not in serialized


def test_epoch_tampering_with_stale_semantic_id_is_rejected():
    record = audit_record(evidence())
    tampered = copy.deepcopy(record)
    tampered["payload"]["fingerprint_key_epoch_id"] = "0" * 32

    with pytest.raises(
        RestrictionObservabilityError,
        match="semantic evidence identity",
    ):
        project_restriction_audit_record(tampered)


def test_legacy_v2_remains_readable_but_epoch_is_explicitly_unknown():
    record = audit_record(evidence())
    payload = record["payload"]
    payload["schema"] = RESTRICTION_SCHEMA_V2
    payload.pop("fingerprint_key_epoch_id")
    payload["restriction_id"] = canonical_id(payload)
    payload["_outbox_event_id"] = f"SARA-EVENT-RESTRICTION-{payload['restriction_id']}"

    projected = project_restriction_audit_record(record)

    assert projected["provenance_schema"] == RESTRICTION_SCHEMA_V2
    assert projected["authority_bound_in_payload"] is True
    assert projected["fingerprint_epoch_bound_in_payload"] is False
    assert projected["fingerprint_key_epoch_id"] is None


def test_remediation_binding_carries_key_epoch_context():
    item = evidence()
    directive = build_remediation_directive(
        item,
        action="HUMAN_REVIEW",
        requested_by="SARA",
        rationale_code="VERIFY_BOUNDARY",
    )

    assert (
        directive["content_binding"]["fingerprint_key_epoch_id"]
        == item.fingerprint_key_epoch_id
    )


def test_g5_reduces_declared_key_rotation_ambiguity_by_at_least_ten_x():
    current = evidence(KEY_A)
    rotated = evidence(KEY_B)
    projection = project_restriction_audit_record(audit_record(current))
    remediation = build_remediation_directive(
        current,
        action="HUMAN_REVIEW",
        requested_by="SARA",
    )

    residual = sum(
        int(value)
        for value in (
            not bool(current.fingerprint_key_epoch_id),
            not projection["fingerprint_epoch_bound_in_payload"],
            not bool(remediation["content_binding"]["fingerprint_key_epoch_id"]),
            current.fingerprint_key_epoch_id == rotated.fingerprint_key_epoch_id,
        )
    )

    assert BASELINE_RESIDUAL_RISK_UNITS == 4
    assert residual / BASELINE_RESIDUAL_RISK_UNITS <= MAX_RESIDUAL_RATIO
    assert residual == 0
