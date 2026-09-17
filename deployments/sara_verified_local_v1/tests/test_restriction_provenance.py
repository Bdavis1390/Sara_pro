from __future__ import annotations

import base64
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.event_outbox import (
    EVENT_OUTBOX_REGISTRY_KEY,
    drain_event_outbox,
)
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.prime_sentinel_authorization import PrimeSentinelVerifier
from worldshepherd_sara.restriction_observability import (
    RESTRICTION_OBSERVABILITY_SCHEMA,
    restriction_observability,
)
from worldshepherd_sara.restriction_provenance import (
    RESTRICTION_EVENT,
    RESTRICTION_SCHEMA,
    RestrictionProvenanceError,
    build_remediation_directive,
    capture_restriction,
    queue_restriction_event,
)
from worldshepherd_sara.restriction_signature import (
    SIGNED_RESTRICTION_SCHEMA,
    bind_verified_restriction_signature,
    canonical_restriction_signature_message,
    queue_signed_restriction_event,
)
from worldshepherd_sara.storage import DurableStore


KEY = b"worldshepherd-test-restriction-key-32-bytes-minimum"
KEY_ID = "ws-restriction-key-epoch-2026-09"
OCCURRED_AT = "2026-09-17T20:14:00+00:00"
APPROVED_SUMMARY = "Output was restricted; only bounded provenance is retained."
SIGNING_KEY_ID = "PS-RESTRICTION-TEST-K1"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


_SIGNING_PRIVATE = Ed25519PrivateKey.generate()
_SIGNING_VERIFIER = PrimeSentinelVerifier(
    public_keys_b64url={
        SIGNING_KEY_ID: _b64url(_SIGNING_PRIVATE.public_key().public_bytes_raw())
    }
)


def sign_evidence(evidence):
    signature = _b64url(
        _SIGNING_PRIVATE.sign(
            canonical_restriction_signature_message(
                evidence,
                signing_key_id=SIGNING_KEY_ID,
            )
        )
    )
    return bind_verified_restriction_signature(
        evidence,
        signing_key_id=SIGNING_KEY_ID,
        signature_b64url=signature,
        verifier=_SIGNING_VERIFIER,
    )


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def make_evidence(**overrides):
    values = {
        "fingerprint_key": KEY,
        "fingerprint_key_id": KEY_ID,
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
        "safe_summary": APPROVED_SUMMARY,
        "metadata": {
            "stage": "post_generation_policy_check",
            "claims_state": "IMPLEMENTED_IN_SOFTWARE",
            "attempt": 1,
        },
        "occurred_at": OCCURRED_AT,
    }
    values.update(overrides)
    return capture_restriction(**values)


def queue_into_store(store: DurableStore, evidence) -> str:
    signed = sign_evidence(evidence)

    def operation(registry):
        patch, stable_id = queue_signed_restriction_event(registry, signed)
        return patch, stable_id

    stable_id = store.transact_registry(operation)
    assert drain_event_outbox(store, limit=1) == 1
    return stable_id


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


def test_unsigned_queue_fails_closed_and_signed_v4_uses_normal_sara_outbox_contract():
    evidence = make_evidence()

    with pytest.raises(RestrictionProvenanceError, match="unsigned restriction queueing"):
        queue_restriction_event({}, evidence)

    signed = sign_evidence(evidence)
    patch, event_id = queue_signed_restriction_event({}, signed)

    assert event_id == evidence.outbox_event_id
    entry = patch[EVENT_OUTBOX_REGISTRY_KEY][event_id]
    assert entry["event"] == RESTRICTION_EVENT
    assert entry["actor"] == "PRIME_SENTINEL"
    assert entry["status"] == "PENDING"
    assert entry["delivery_semantics"] == "AT_LEAST_ONCE"
    assert entry["payload"]["schema"] == SIGNED_RESTRICTION_SCHEMA
    assert entry["payload"]["restriction"]["restriction_id"] == evidence.restriction_id
    assert entry["payload"]["prime_signature"]["restriction_id"] == evidence.restriction_id
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

    stable_id = queue_into_store(sara, evidence)
    assert stable_id == evidence.outbox_event_id

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
    assert persisted.payload()["schema"] == SIGNED_RESTRICTION_SCHEMA
    assert persisted.payload()["restriction"]["restriction_id"] == evidence.restriction_id
    assert persisted.payload()["restriction"]["raw_content_persisted"] is False
    assert persisted.payload()["raw_content_persisted"] is False
    assert echo.health()["ok"] is True

    database_bytes = echo.db_path.read_bytes()
    for forbidden in (raw_input, raw_generated, safe_output):
        assert forbidden.encode("utf-8") not in database_bytes


def test_observability_strict_projection_omits_summary_and_metadata(tmp_path):
    approved_stage = "connector_policy_check"
    approved_claims_state = "PROVEN_INTERNALLY"
    raw_input = "raw input must remain absent 4b92d3"
    raw_generated = "raw generated must remain absent 04a9ee"
    safe_output = "safe replacement must remain absent 4d2cc8"
    evidence = make_evidence(
        raw_input=raw_input,
        raw_generated=raw_generated,
        safe_output=safe_output,
        safe_summary=APPROVED_SUMMARY,
        metadata={
            "stage": approved_stage,
            "claims_state": approved_claims_state,
            "attempt": 7,
        },
    )
    sara = DurableStore(tmp_path / "sara-observability")
    stable_id = queue_into_store(sara, evidence)

    report = restriction_observability(
        sara.read_audit(100),
        recent_limit=10,
        verifier=_SIGNING_VERIFIER,
    )

    assert report["schema"] == RESTRICTION_OBSERVABILITY_SCHEMA
    assert report["ok"] is True
    assert report["restriction_events_seen"] == 1
    assert report["valid_restriction_events"] == 1
    assert report["malformed_restriction_events"] == 0
    assert report["counts"]["by_action"] == {"REDACT": 1}
    assert report["recent"][0]["event_id"] == stable_id
    serialized = json.dumps(report, sort_keys=True)
    for forbidden in (
        "safe_summary",
        "metadata",
        APPROVED_SUMMARY,
        approved_stage,
        approved_claims_state,
        raw_input,
        raw_generated,
        safe_output,
    ):
        assert forbidden not in serialized


def test_observability_counts_malformed_restriction_records():
    malformed = AuditRecord.create(
        event=RESTRICTION_EVENT,
        actor="PRIME_SENTINEL",
        payload={
            "schema": RESTRICTION_SCHEMA,
            "restriction_id": "0" * 32,
            "raw_content_persisted": True,
        },
    ).model_dump(mode="json")

    report = restriction_observability([malformed], recent_limit=1)

    assert report["ok"] is False
    assert report["restriction_events_seen"] == 1
    assert report["valid_restriction_events"] == 0
    assert report["malformed_restriction_events"] == 1
    assert report["recent"] == []


def test_restriction_observability_api_is_admin_only_and_strict(client, tokens):
    relay_token, admin_token = tokens
    approved_stage = "pre_generation_policy_check"
    approved_claims_state = "SUPPORTED_BY_LITERATURE"
    raw_input = "api raw input sentinel d39a42"
    raw_generated = "api raw generated sentinel 0aaf16"
    safe_output = "api safe output sentinel 620c04"
    evidence = make_evidence(
        raw_input=raw_input,
        raw_generated=raw_generated,
        safe_output=safe_output,
        safe_summary=APPROVED_SUMMARY,
        metadata={
            "stage": approved_stage,
            "claims_state": approved_claims_state,
            "attempt": 3,
        },
    )
    client.app.state.prime_sentinel_verifier = _SIGNING_VERIFIER
    stable_id = queue_into_store(client.app.state.store, evidence)

    assert client.get("/admin/restrictions/status").status_code == 401
    assert (
        client.get(
            "/admin/restrictions/status",
            headers=auth(relay_token),
        ).status_code
        == 403
    )

    status = client.get(
        "/admin/restrictions/status",
        headers=auth(admin_token),
    )
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["ok"] is True
    assert status_body["restriction_events_seen"] == 1
    assert status_body["valid_restriction_events"] == 1
    assert "recent" not in status_body
    assert status.headers["cache-control"] == "no-store"

    recent = client.get(
        "/admin/restrictions/recent?limit=10",
        headers=auth(admin_token),
    )
    assert recent.status_code == 200
    body = recent.json()
    assert body["recent"][0]["event_id"] == stable_id
    assert body["recent"][0]["restriction_id"] == evidence.restriction_id
    serialized = json.dumps(body, sort_keys=True)
    for forbidden in (
        "safe_summary",
        "metadata",
        APPROVED_SUMMARY,
        approved_stage,
        approved_claims_state,
        raw_input,
        raw_generated,
        safe_output,
    ):
        assert forbidden not in serialized

    assert (
        client.get(
            "/admin/restrictions/recent?limit=0",
            headers=auth(admin_token),
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/admin/restrictions/recent?limit=101",
            headers=auth(admin_token),
        ).status_code
        == 422
    )


def test_restriction_status_api_reports_malformed_event(client, tokens):
    _relay_token, admin_token = tokens
    client.app.state.store.append_audit(
        AuditRecord.create(
            event=RESTRICTION_EVENT,
            actor="PRIME_SENTINEL",
            payload={
                "schema": RESTRICTION_SCHEMA,
                "restriction_id": "f" * 32,
                "raw_content_persisted": True,
            },
        )
    )

    response = client.get(
        "/admin/restrictions/status",
        headers=auth(admin_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["restriction_events_seen"] == 1
    assert body["malformed_restriction_events"] == 1


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
