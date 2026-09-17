from __future__ import annotations

import json

import pytest

from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.event_outbox import (
    EVENT_OUTBOX_REGISTRY_KEY,
    drain_event_outbox,
)
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.restriction_provenance import (
    RESTRICTION_EVENT,
    RestrictionProvenanceError,
    build_remediation_directive,
    capture_restriction,
    queue_restriction_event,
)
from worldshepherd_sara.storage import DurableStore


KEY = b"worldshepherd-test-restriction-key-32-bytes-minimum"
OCCURRED_AT = "2026-09-17T20:14:00+00:00"


def make_evidence(**overrides):
    values = {
        "fingerprint_key": KEY,
        "action": "REDACT",
        "reason_code": "POLICY.RESTRICTED_OUTPUT",
        "source_system": "CHAT_ASSISTANT",
        "processor": "POLICY_GATE",
        "process_version": "v1",
        "policy_ref": "CONTENT_POLICY",
        "correlation_id": "corr-001",
        "parent_event_id": "SARA-EVENT-parent-001",
        "raw_input": "sensitive input material that must not persist",
        "raw_generated": "restricted candidate output that must not persist",
        "safe_output": "safe replacement",
        "safe_summary": "Output was restricted; only bounded provenance is retained.",
        "metadata": {
            "stage": "post_generation_policy_check",
            "claims_state": "IMPLEMENTED_IN_SOFTWARE",
            "attempt": 1,
        },
        "occurred_at": OCCURRED_AT,
    }
    values.update(overrides)
    return capture_restriction(**values)


def test_raw_restricted_content_never_serializes():
    evidence = make_evidence()

    encoded = evidence.canonical_json()

    assert "sensitive input material" not in encoded
    assert "restricted candidate output" not in encoded
    assert "safe replacement" not in encoded
    assert evidence.semantic_document()["raw_content_persisted"] is False
    assert len(evidence.input_fingerprint or "") == 64
    assert len(evidence.generated_fingerprint or "") == 64
    assert len(evidence.safe_output_fingerprint or "") == 64


def test_fingerprints_are_stable_domain_separated_and_content_bound():
    first = make_evidence()
    replay = make_evidence()
    changed = make_evidence(raw_generated="different restricted candidate")

    assert first.restriction_id == replay.restriction_id
    assert first.generated_fingerprint == replay.generated_fingerprint
    assert first.input_fingerprint != first.generated_fingerprint
    assert changed.generated_fingerprint != first.generated_fingerprint
    assert changed.restriction_id != first.restriction_id


def test_keyed_fingerprints_change_when_deployment_key_changes():
    first = make_evidence()
    second = make_evidence(
        fingerprint_key=b"different-worldshepherd-test-key-32-bytes-minimum"
    )

    assert first.input_fingerprint != second.input_fingerprint
    assert first.generated_fingerprint != second.generated_fingerprint


def test_metadata_rejects_raw_content_and_secret_fields_recursively():
    with pytest.raises(RestrictionProvenanceError, match="forbidden"):
        make_evidence(metadata={"diagnostic": {"raw_content": "do not persist"}})

    with pytest.raises(RestrictionProvenanceError, match="forbidden"):
        make_evidence(metadata={"token": "do not persist"})

    with pytest.raises(RestrictionProvenanceError, match="forbidden"):
        make_evidence(metadata={"diagnostic": ({"prompt": "do not persist"},)})


def test_safe_summary_cannot_equal_restricted_input_or_generated_output():
    raw = "restricted value"
    with pytest.raises(RestrictionProvenanceError, match="safe_summary"):
        make_evidence(raw_generated=raw, safe_summary=raw)

    with pytest.raises(RestrictionProvenanceError, match="safe_summary"):
        make_evidence(raw_input=raw, safe_summary=raw)


def test_queue_restriction_event_uses_normal_sara_outbox_contract():
    evidence = make_evidence()

    patch, event_id = queue_restriction_event({}, evidence)

    assert event_id == evidence.outbox_event_id
    entry = patch[EVENT_OUTBOX_REGISTRY_KEY][event_id]
    assert entry["event"] == RESTRICTION_EVENT
    assert entry["actor"] == "PRIME_SENTINEL"
    assert entry["status"] == "PENDING"
    assert entry["delivery_semantics"] == "AT_LEAST_ONCE"
    assert entry["payload"]["restriction_id"] == evidence.restriction_id
    assert entry["payload"]["raw_content_persisted"] is False
    serialized = json.dumps(entry, sort_keys=True)
    assert "restricted candidate output" not in serialized
    assert "sensitive input material" not in serialized


def test_restriction_survives_sara_to_echo_without_raw_content(tmp_path):
    raw_input = "raw sentinel input must never persist 7c09512f"
    raw_generated = "raw sentinel generated must never persist 4d6e0231"
    safe_output = "safe sentinel output is fingerprinted but not persisted 92ce7c11"
    evidence = make_evidence(
        raw_input=raw_input,
        raw_generated=raw_generated,
        safe_output=safe_output,
    )
    sara = DurableStore(tmp_path / "sara-data")

    def queue_operation(registry):
        patch, stable_id = queue_restriction_event(registry, evidence)
        return patch, stable_id

    stable_id = sara.transact_registry(queue_operation)
    assert stable_id == evidence.outbox_event_id
    assert drain_event_outbox(sara, limit=1) == 1

    records = [
        record
        for record in sara.read_audit(100)
        if record.get("event") == RESTRICTION_EVENT
    ]
    assert len(records) == 1
    serialized_audit = json.dumps(records[0], sort_keys=True)
    for forbidden in (raw_input, raw_generated, safe_output):
        assert forbidden not in serialized_audit

    audit = AuditRecord(**records[0])
    echo = EchoEventStore((tmp_path / "echo-data").resolve())
    first = echo.ingest(audit)
    replay = echo.ingest(audit)
    assert first.outcome == "STORED"
    assert replay.outcome == "DEDUPLICATED"
    assert replay.record.event_id == stable_id
    assert replay.record.delivery_count == 2

    reconciliation = echo.reconcile([audit])
    assert reconciliation["counts"] == {"MATCHED": 1}
    assert reconciliation["entries"] == [
        {"event_id": stable_id, "classification": "MATCHED"}
    ]
    persisted = echo.get(stable_id)
    assert persisted is not None
    assert persisted.payload()["restriction_id"] == evidence.restriction_id
    assert persisted.payload()["raw_content_persisted"] is False
    assert echo.health()["ok"] is True

    database_bytes = echo.db_path.read_bytes()
    for forbidden in (raw_input, raw_generated, safe_output):
        assert forbidden.encode("utf-8") not in database_bytes


def test_allowed_remediation_is_bound_to_restriction_without_raw_content():
    evidence = make_evidence()

    directive = build_remediation_directive(
        evidence,
        action="SAFE_TRANSFORM",
        requested_by="SARA",
        rationale_code="SAFE_REPRESENTATION_ONLY",
    )

    assert directive["restriction_id"] == evidence.restriction_id
    assert directive["restriction_event_id"] == evidence.outbox_event_id
    assert directive["action"] == "SAFE_TRANSFORM"
    assert directive["rationale_code"] == "SAFE_REPRESENTATION_ONLY"
    assert directive["raw_content_included"] is False
    assert directive["content_binding"]["generated_fingerprint"] == evidence.generated_fingerprint


def test_remediation_rationale_is_identifier_only_not_free_text():
    with pytest.raises(RestrictionProvenanceError, match="rationale_code"):
        build_remediation_directive(
            make_evidence(),
            action="HUMAN_REVIEW",
            requested_by="SARA",
            rationale_code="free form text is not allowed here",
        )


def test_raw_replay_and_policy_bypass_remediations_are_rejected():
    evidence = make_evidence()

    for action in ("REPLAY_RAW", "RESTORE_RAW", "BYPASS_POLICY", "DISABLE_FILTER", "FORCE_RELEASE"):
        with pytest.raises(RestrictionProvenanceError, match="must not replay raw content"):
            build_remediation_directive(
                evidence,
                action=action,
                requested_by="SARA",
            )


def test_unknown_remediation_is_rejected_fail_closed():
    with pytest.raises(RestrictionProvenanceError, match="must not replay raw content"):
        build_remediation_directive(
            make_evidence(),
            action="DO_WHATEVER",
            requested_by="SARA",
        )


def test_naive_timestamp_and_invalid_reason_fail_closed():
    with pytest.raises(RestrictionProvenanceError, match="timezone-aware"):
        make_evidence(occurred_at="2026-09-17T20:14:00")

    with pytest.raises(RestrictionProvenanceError, match="reason_code"):
        make_evidence(reason_code="free form explanation")


def test_weak_fingerprint_key_is_rejected_even_without_raw_content():
    with pytest.raises(RestrictionProvenanceError, match="at least 32 bytes"):
        make_evidence(
            fingerprint_key=b"short",
            raw_input=None,
            raw_generated=None,
            safe_output=None,
        )
