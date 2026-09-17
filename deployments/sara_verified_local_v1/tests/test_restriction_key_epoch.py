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
    FINGERPRINT_KEY_ID_ENV,
    RESTRICTION_AUTHORITY,
    RESTRICTION_EVENT,
    RESTRICTION_SCHEMA,
    RESTRICTION_SCHEMA_V2,
    RestrictionProvenanceError,
    capture_restriction,
    fingerprint_key_id_from_environment,
)


KEY = b"worldshepherd-g5-key-epoch-test-key-32-bytes-minimum"
OTHER_KEY = b"worldshepherd-g5-other-test-key-32-bytes-minimum"
KEY_ID = "ws-restriction-key-epoch-2026-09-a"
OTHER_KEY_ID = "ws-restriction-key-epoch-2026-09-b"
APPROVED_SUMMARY = "Output was restricted; only bounded provenance is retained."


def evidence(*, key=KEY, key_id=KEY_ID):
    return capture_restriction(
        fingerprint_key=key,
        fingerprint_key_id=key_id,
        action="BLOCK",
        reason_code="POLICY.KEY_EPOCH_TEST",
        source_system="CHAT_ASSISTANT",
        processor="POLICY_GATE",
        process_version="v3",
        policy_ref="CONTENT_POLICY",
        correlation_id="key-epoch-001",
        raw_input="same raw input for key epoch test",
        raw_generated="same raw generated content for key epoch test",
        safe_summary=APPROVED_SUMMARY,
        metadata={
            "stage": "post_generation_policy_check",
            "claims_state": "IMPLEMENTED_IN_SOFTWARE",
            "attempt": 1,
        },
        occurred_at="2026-09-17T22:45:00+00:00",
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


def audit_record(payload):
    value = copy.deepcopy(payload)
    value["_outbox_event_id"] = f"SARA-EVENT-RESTRICTION-{value['restriction_id']}"
    value["_delivery_semantics"] = "AT_LEAST_ONCE"
    return AuditRecord(
        timestamp="2026-09-17T22:45:01+00:00",
        event=RESTRICTION_EVENT,
        actor=RESTRICTION_AUTHORITY,
        payload=value,
    ).model_dump(mode="json")


def legacy_v2_payload() -> dict:
    payload = evidence().semantic_document()
    payload["schema"] = RESTRICTION_SCHEMA_V2
    payload.pop("fingerprint_key_id")
    payload["restriction_id"] = canonical_id(payload)
    return payload


def test_new_restrictions_bind_fingerprint_key_epoch_into_v3_identity():
    item = evidence()
    document = item.semantic_document()

    assert RESTRICTION_SCHEMA.endswith("V3")
    assert document["schema"] == RESTRICTION_SCHEMA
    assert document["fingerprint_key_id"] == KEY_ID
    assert item.fingerprint_key_id == KEY_ID
    assert item.restriction_id == canonical_id(document)


def test_epoch_change_changes_evidence_identity_without_changing_content_fingerprints():
    first = evidence(key=KEY, key_id=KEY_ID)
    second = evidence(key=KEY, key_id=OTHER_KEY_ID)

    assert first.input_fingerprint == second.input_fingerprint
    assert first.generated_fingerprint == second.generated_fingerprint
    assert first.restriction_id != second.restriction_id


def test_key_material_change_changes_fingerprints_even_if_declared_epoch_is_same():
    first = evidence(key=KEY, key_id=KEY_ID)
    second = evidence(key=OTHER_KEY, key_id=KEY_ID)

    assert first.input_fingerprint != second.input_fingerprint
    assert first.generated_fingerprint != second.generated_fingerprint
    assert first.restriction_id != second.restriction_id


def test_v3_projection_exposes_only_non_secret_epoch_identifier():
    projected = project_restriction_audit_record(audit_record(evidence().semantic_document()))

    assert projected["fingerprint_key_id"] == KEY_ID
    assert projected["fingerprint_key_epoch_bound_in_payload"] is True
    assert projected["authority"] == RESTRICTION_AUTHORITY


def test_v2_legacy_projection_is_explicitly_epoch_unbound():
    payload = legacy_v2_payload()
    projected = project_restriction_audit_record(audit_record(payload))

    assert projected["provenance_schema"] == RESTRICTION_SCHEMA_V2
    assert projected["fingerprint_key_id"] is None
    assert projected["fingerprint_key_epoch_bound_in_payload"] is False
    assert projected["authority_bound_in_payload"] is True


def test_v3_epoch_id_tampering_requires_matching_semantic_identity():
    payload = evidence().semantic_document()
    payload["fingerprint_key_id"] = OTHER_KEY_ID

    with pytest.raises(RestrictionObservabilityError, match="semantic evidence identity"):
        project_restriction_audit_record(audit_record(payload))


def test_v3_cannot_be_downgraded_to_v2_by_stripping_key_epoch():
    payload = evidence().semantic_document()
    original_v3_id = payload["restriction_id"]
    payload["schema"] = RESTRICTION_SCHEMA_V2
    payload.pop("fingerprint_key_id")
    assert payload["restriction_id"] == original_v3_id

    with pytest.raises(RestrictionObservabilityError, match="semantic evidence identity"):
        project_restriction_audit_record(audit_record(payload))


def test_invalid_or_missing_key_epoch_fails_closed(monkeypatch):
    with pytest.raises(RestrictionProvenanceError, match="fingerprint_key_id"):
        evidence(key_id="bad key id with spaces")

    monkeypatch.delenv(FINGERPRINT_KEY_ID_ENV, raising=False)
    with pytest.raises(RestrictionProvenanceError, match="fingerprint_key_id"):
        fingerprint_key_id_from_environment()

    monkeypatch.setenv(FINGERPRINT_KEY_ID_ENV, KEY_ID)
    assert fingerprint_key_id_from_environment() == KEY_ID


def test_observability_aggregates_by_non_secret_key_epoch():
    first = audit_record(evidence(key_id=KEY_ID).semantic_document())
    second = audit_record(evidence(key_id=OTHER_KEY_ID).semantic_document())
    legacy = audit_record(legacy_v2_payload())

    report = restriction_observability([first, second, legacy], recent_limit=3)

    assert report["ok"] is True
    assert report["counts"]["by_fingerprint_key_id"] == {
        KEY_ID: 1,
        OTHER_KEY_ID: 1,
        "UNBOUND_LEGACY": 1,
    }
