from __future__ import annotations

import copy
import hashlib
import json

import pytest

from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.restriction_observability import (
    RestrictionObservabilityError,
    project_restriction_audit_record,
    restriction_observability,
)
from worldshepherd_sara.restriction_provenance import (
    RESTRICTION_AUTHORITY,
    RESTRICTION_EVENT,
    RESTRICTION_SCHEMA,
    RESTRICTION_SCHEMA_V1,
    RESTRICTION_SCHEMA_V2,
    RestrictionProvenanceError,
    capture_restriction,
    queue_restriction_event,
)


KEY = b"worldshepherd-g4-authority-test-key-32-bytes-minimum"
KEY_ID = "ws-restriction-key-epoch-2026-09"
APPROVED_SUMMARY = "Output was restricted; only bounded provenance is retained."


def evidence():
    return capture_restriction(
        fingerprint_key=KEY,
        fingerprint_key_id=KEY_ID,
        action="BLOCK",
        reason_code="POLICY.AUTHORITY_TEST",
        source_system="CHAT_ASSISTANT",
        processor="POLICY_GATE",
        process_version="v2",
        policy_ref="CONTENT_POLICY",
        correlation_id="authority-001",
        raw_input="authority test input must not persist",
        raw_generated="authority test generated must not persist",
        safe_summary=APPROVED_SUMMARY,
        metadata={
            "stage": "post_generation_policy_check",
            "claims_state": "IMPLEMENTED_IN_SOFTWARE",
            "attempt": 1,
        },
        occurred_at="2026-09-17T21:45:00+00:00",
    )


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


def legacy_v2_payload() -> dict:
    payload = evidence().semantic_document()
    payload["schema"] = RESTRICTION_SCHEMA_V2
    payload.pop("fingerprint_key_id")
    payload["restriction_id"] = canonical_id(payload)
    return payload


def legacy_v1_payload() -> dict:
    payload = legacy_v2_payload()
    payload["schema"] = RESTRICTION_SCHEMA_V1
    payload.pop("authority")
    payload["restriction_id"] = canonical_id(payload)
    return payload


def audit_record(*, actor=RESTRICTION_AUTHORITY, payload=None):
    item = evidence()
    value = copy.deepcopy(item.semantic_document() if payload is None else payload)
    value["_outbox_event_id"] = f"SARA-EVENT-RESTRICTION-{value['restriction_id']}"
    value["_delivery_semantics"] = "AT_LEAST_ONCE"
    return AuditRecord(
        timestamp="2026-09-17T21:45:01+00:00",
        event=RESTRICTION_EVENT,
        actor=actor,
        payload=value,
    ).model_dump(mode="json")


def test_new_restrictions_preserve_prime_authority_binding_in_v3_identity():
    item = evidence()
    document = item.semantic_document()

    assert document["schema"] == RESTRICTION_SCHEMA
    assert RESTRICTION_SCHEMA.endswith("V3")
    assert document["fingerprint_key_id"] == KEY_ID
    assert item.authority == RESTRICTION_AUTHORITY
    assert document["authority"] == RESTRICTION_AUTHORITY
    assert item.restriction_id == canonical_id(document)
    assert item.outbox_event_id == f"SARA-EVENT-RESTRICTION-{item.restriction_id}"


def test_unsigned_queue_is_disabled_and_actor_is_not_caller_overridable():
    item = evidence()

    with pytest.raises(RestrictionProvenanceError, match="unsigned restriction queueing"):
        queue_restriction_event({}, item)

    with pytest.raises(TypeError):
        queue_restriction_event({}, item, actor="UNTRUSTED_ACTOR")  # type: ignore[call-arg]


def test_v2_projection_requires_governed_outer_actor_and_payload_authority():
    payload = legacy_v2_payload()
    projected = project_restriction_audit_record(audit_record(payload=payload))
    assert projected["authority"] == RESTRICTION_AUTHORITY
    assert projected["authority_bound_in_payload"] is True
    assert projected["provenance_schema"] == RESTRICTION_SCHEMA_V2
    assert projected["fingerprint_key_epoch_bound_in_payload"] is False
    assert projected["fingerprint_key_id"] is None

    with pytest.raises(RestrictionObservabilityError, match="audit actor"):
        project_restriction_audit_record(audit_record(actor="UNTRUSTED_ACTOR"))

    missing = legacy_v2_payload()
    missing.pop("authority")
    with pytest.raises(RestrictionObservabilityError, match="payload authority"):
        project_restriction_audit_record(audit_record(payload=missing))

    wrong = legacy_v2_payload()
    wrong["authority"] = "UNTRUSTED_ACTOR"
    with pytest.raises(RestrictionObservabilityError, match="payload authority"):
        project_restriction_audit_record(audit_record(payload=wrong))


def test_v2_semantic_tampering_is_detected_by_recomputed_identity():
    tampered = evidence().semantic_document()
    tampered["reason_code"] = "POLICY.TAMPERED"

    with pytest.raises(RestrictionObservabilityError, match="semantic evidence identity"):
        project_restriction_audit_record(audit_record(payload=tampered))


def test_v2_authority_tampering_marks_observability_unhealthy():
    report = restriction_observability(
        [audit_record(actor="UNTRUSTED_ACTOR")],
        recent_limit=1,
    )

    assert report["ok"] is False
    assert report["restriction_events_seen"] == 1
    assert report["valid_restriction_events"] == 0
    assert report["malformed_restriction_events"] == 1
    assert report["recent"] == []


def test_v1_legacy_record_requires_prime_actor_but_not_payload_authority():
    payload = legacy_v1_payload()
    projected = project_restriction_audit_record(audit_record(payload=payload))

    assert projected["provenance_schema"] == RESTRICTION_SCHEMA_V1
    assert projected["authority"] == RESTRICTION_AUTHORITY
    assert projected["authority_bound_in_payload"] is False
    assert payload["restriction_id"] == canonical_id(payload)

    with pytest.raises(RestrictionObservabilityError, match="audit actor"):
        project_restriction_audit_record(
            audit_record(actor="UNTRUSTED_ACTOR", payload=payload)
        )


def test_v2_cannot_be_downgraded_to_v1_by_stripping_authority():
    downgraded = legacy_v2_payload()
    original_v2_id = downgraded["restriction_id"]
    downgraded["schema"] = RESTRICTION_SCHEMA_V1
    downgraded.pop("authority")
    assert downgraded["restriction_id"] == original_v2_id

    with pytest.raises(RestrictionObservabilityError, match="semantic evidence identity"):
        project_restriction_audit_record(audit_record(payload=downgraded))


def test_v1_cannot_smuggle_v2_authority_field():
    payload = legacy_v1_payload()
    payload["authority"] = RESTRICTION_AUTHORITY

    with pytest.raises(RestrictionObservabilityError, match="unknown fields"):
        project_restriction_audit_record(audit_record(payload=payload))
