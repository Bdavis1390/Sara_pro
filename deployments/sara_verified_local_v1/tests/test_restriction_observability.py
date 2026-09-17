from __future__ import annotations

import pytest

from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.restriction_observability import (
    MAX_RESTRICTION_AUDIT_WINDOW,
    RestrictionObservabilityError,
    project_restriction_audit_record,
    restriction_observability,
)
from worldshepherd_sara.restriction_provenance import (
    RESTRICTION_AUTHORITY,
    RESTRICTION_EVENT,
    RESTRICTION_SCHEMA,
    capture_restriction,
)


KEY = b"worldshepherd-observability-test-key-32-bytes-minimum"
KEY_ID = "ws-restriction-key-epoch-2026-09"
OCCURRED_AT = "2026-09-17T20:14:00+00:00"
APPROVED_SUMMARY = "Output was restricted; only bounded provenance is retained."


def valid_restriction_record() -> dict:
    evidence = capture_restriction(
        fingerprint_key=KEY,
        fingerprint_key_id=KEY_ID,
        action="BLOCK",
        reason_code="POLICY.TEST_BLOCK",
        source_system="CHAT_ASSISTANT",
        processor="POLICY_GATE",
        process_version="v1",
        policy_ref="TEST_POLICY",
        correlation_id="obs-001",
        raw_input="raw test input not persisted",
        raw_generated="raw test generated not persisted",
        safe_output="safe test output not persisted",
        safe_summary=APPROVED_SUMMARY,
        metadata={
            "stage": "post_generation_policy_check",
            "claims_state": "IMPLEMENTED_IN_SOFTWARE",
            "attempt": 1,
        },
        occurred_at=OCCURRED_AT,
    )
    payload = evidence.semantic_document()
    payload["_outbox_event_id"] = evidence.outbox_event_id
    payload["_delivery_semantics"] = "AT_LEAST_ONCE"
    return AuditRecord(
        timestamp="2026-09-17T20:14:01+00:00",
        event=RESTRICTION_EVENT,
        actor=RESTRICTION_AUTHORITY,
        payload=payload,
    ).model_dump(mode="json")


def test_unknown_restriction_payload_field_fails_closed():
    record = valid_restriction_record()
    record["payload"]["raw_content"] = "unexpected field must invalidate record"

    with pytest.raises(RestrictionObservabilityError, match="unknown fields"):
        project_restriction_audit_record(record)

    report = restriction_observability([record], recent_limit=1)
    assert report["ok"] is False
    assert report["restriction_events_seen"] == 1
    assert report["valid_restriction_events"] == 0
    assert report["malformed_restriction_events"] == 1
    assert report["recent"] == []


def test_helper_rejects_audit_window_over_bound():
    records = [{"event": "unrelated"}] * (MAX_RESTRICTION_AUDIT_WINDOW + 1)

    with pytest.raises(RestrictionObservabilityError, match="audit window"):
        restriction_observability(records, recent_limit=1)


def test_strict_projection_never_returns_summary_metadata_or_unknown_fields():
    record = valid_restriction_record()

    projected = project_restriction_audit_record(record)

    assert projected["provenance_schema"] == RESTRICTION_SCHEMA
    assert projected["authority"] == RESTRICTION_AUTHORITY
    assert projected["authority_bound_in_payload"] is True
    assert projected["fingerprint_key_id"] == KEY_ID
    assert projected["fingerprint_key_epoch_bound_in_payload"] is True
    assert "safe_summary" not in projected
    assert "metadata" not in projected
    assert set(projected) == {
        "provenance_schema",
        "restriction_id",
        "event_id",
        "authority",
        "authority_bound_in_payload",
        "restriction_schema",
        "signature_verified",
        "signing_key_id",
        "signing_key_fingerprint_sha256",
        "fingerprint_key_id",
        "fingerprint_key_epoch_bound_in_payload",
        "audit_timestamp",
        "occurred_at",
        "action",
        "reason_code",
        "source_system",
        "processor",
        "process_version",
        "policy_ref",
        "correlation_id",
        "parent_event_id",
        "input_fingerprint",
        "generated_fingerprint",
        "safe_output_fingerprint",
        "raw_content_persisted",
    }
