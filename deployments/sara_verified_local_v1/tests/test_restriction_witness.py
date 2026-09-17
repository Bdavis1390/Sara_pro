from __future__ import annotations

import copy
import hashlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.echo_checkpoint import EchoCheckpointManager
from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.restriction_observability import (
    project_restriction_audit_record,
)
from worldshepherd_sara.restriction_provenance import (
    RESTRICTION_AUTHORITY,
    RESTRICTION_EVENT,
    capture_restriction,
)
from worldshepherd_sara.restriction_witness import (
    RESTRICTION_WITNESS_SCHEMA,
    RestrictionWitnessVerificationError,
    verify_restriction_witness,
)


KEY = b"worldshepherd-g6-fingerprint-key-32-bytes-minimum"
BASELINE_RESIDUAL_RISK_UNITS = 4
MAX_RESIDUAL_RATIO = 0.10


def evidence(*, correlation_id: str = "g6-001", reason_code: str = "POLICY.G6_TEST"):
    return capture_restriction(
        fingerprint_key=KEY,
        fingerprint_key_id="epoch-g6-a",
        action="BLOCK",
        reason_code=reason_code,
        source_system="CHAT_ASSISTANT",
        processor="POLICY_GATE",
        process_version="v3",
        policy_ref="CONTENT_POLICY",
        correlation_id=correlation_id,
        raw_input="g6 restricted input",
        raw_generated="g6 restricted generated content",
        safe_summary="Output was restricted; only bounded provenance is retained.",
        metadata={
            "stage": "post_generation_policy_check",
            "claims_state": "IMPLEMENTED_IN_SOFTWARE",
            "attempt": 1,
        },
        occurred_at="2026-09-17T23:30:00+00:00",
    )


def audit_record(item) -> dict:
    payload = item.semantic_document()
    payload["_outbox_event_id"] = item.outbox_event_id
    payload["_delivery_semantics"] = "AT_LEAST_ONCE"
    return AuditRecord(
        timestamp="2026-09-17T23:30:01+00:00",
        event=RESTRICTION_EVENT,
        actor=RESTRICTION_AUTHORITY,
        payload=payload,
    ).model_dump(mode="json")


def checkpoint_for(tmp_path, records: list[dict], *, key_id: str = "g6-test-signer"):
    store = EchoEventStore((tmp_path / key_id).resolve())
    for record in records:
        store.ingest(AuditRecord(**record))
    manager = EchoCheckpointManager(
        store,
        private_key=Ed25519PrivateKey.generate(),
        key_id=key_id,
    )
    return manager.create_checkpoint(), manager.fingerprint_sha256


def recompute_application_identity(record: dict) -> dict:
    forged = copy.deepcopy(record)
    payload = forged["payload"]
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
    restriction_id = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:32]
    payload["restriction_id"] = restriction_id
    payload["_outbox_event_id"] = f"SARA-EVENT-RESTRICTION-{restriction_id}"
    return forged


def rejects(record, bundle, fingerprint) -> bool:
    try:
        verify_restriction_witness(
            record,
            bundle,
            expected_checkpoint_key_fingerprint_sha256=fingerprint,
        )
        return False
    except RestrictionWitnessVerificationError:
        return True


def test_valid_restriction_is_witnessed_by_trusted_signed_checkpoint(tmp_path):
    record = audit_record(evidence())
    bundle, fingerprint = checkpoint_for(tmp_path, [record])

    receipt = verify_restriction_witness(
        record,
        bundle,
        expected_checkpoint_key_fingerprint_sha256=fingerprint,
    )

    assert receipt["schema"] == RESTRICTION_WITNESS_SCHEMA
    assert receipt["status"] == "PASS"
    assert receipt["restriction_id"] == record["payload"]["restriction_id"]
    assert receipt["event_id"] == record["payload"]["_outbox_event_id"]
    assert receipt["authority"] == RESTRICTION_AUTHORITY
    assert receipt["fingerprint_key_id"] == "epoch-g6-a"
    assert receipt["checkpoint"]["algorithm"] == "Ed25519"
    assert receipt["checkpoint"]["key_fingerprint_sha256"] == fingerprint


def test_self_consistent_full_record_rewrite_passes_projection_but_fails_witness(tmp_path):
    original = audit_record(evidence())
    bundle, fingerprint = checkpoint_for(tmp_path, [original])

    forged = copy.deepcopy(original)
    forged["payload"]["reason_code"] = "POLICY.G6_FORGED"
    forged = recompute_application_identity(forged)

    projected = project_restriction_audit_record(forged)
    assert projected["reason_code"] == "POLICY.G6_FORGED"

    with pytest.raises(
        RestrictionWitnessVerificationError,
        match="not uniquely witnessed",
    ):
        verify_restriction_witness(
            forged,
            bundle,
            expected_checkpoint_key_fingerprint_sha256=fingerprint,
        )


def test_wrong_trust_fingerprint_fails_closed(tmp_path):
    record = audit_record(evidence())
    bundle, _fingerprint = checkpoint_for(tmp_path, [record])

    with pytest.raises(
        RestrictionWitnessVerificationError,
        match="public-key fingerprint is not trusted",
    ):
        verify_restriction_witness(
            record,
            bundle,
            expected_checkpoint_key_fingerprint_sha256="0" * 64,
        )


def test_signed_checkpoint_tamper_fails_closed(tmp_path):
    record = audit_record(evidence())
    bundle, fingerprint = checkpoint_for(tmp_path, [record])
    tampered = copy.deepcopy(bundle)
    tampered["manifest"]["events"][0]["semantic_sha256"] = "0" * 64

    with pytest.raises(RestrictionWitnessVerificationError):
        verify_restriction_witness(
            record,
            tampered,
            expected_checkpoint_key_fingerprint_sha256=fingerprint,
        )


def test_transport_timestamp_change_does_not_change_semantic_witness(tmp_path):
    original = audit_record(evidence())
    bundle, fingerprint = checkpoint_for(tmp_path, [original])
    transport_variant = copy.deepcopy(original)
    transport_variant["timestamp"] = "2026-09-17T23:30:02+00:00"

    receipt = verify_restriction_witness(
        transport_variant,
        bundle,
        expected_checkpoint_key_fingerprint_sha256=fingerprint,
    )

    assert receipt["status"] == "PASS"


def test_checkpoint_that_omits_event_fails_witness(tmp_path):
    original = audit_record(evidence())
    other = audit_record(
        evidence(
            correlation_id="g6-002",
            reason_code="POLICY.G6_OTHER",
        )
    )
    bundle, fingerprint = checkpoint_for(tmp_path, [other], key_id="g6-other-signer")

    with pytest.raises(
        RestrictionWitnessVerificationError,
        match="not uniquely witnessed",
    ):
        verify_restriction_witness(
            original,
            bundle,
            expected_checkpoint_key_fingerprint_sha256=fingerprint,
        )


def test_g6_reduces_declared_unsigned_authenticity_paths_by_at_least_ten_x(tmp_path):
    original = audit_record(evidence())
    bundle, fingerprint = checkpoint_for(tmp_path, [original])

    forged = copy.deepcopy(original)
    forged["payload"]["reason_code"] = "POLICY.G6_FORGED"
    forged = recompute_application_identity(forged)
    assert project_restriction_audit_record(forged)["reason_code"] == "POLICY.G6_FORGED"

    tampered_bundle = copy.deepcopy(bundle)
    tampered_bundle["signature_b64url"] = "A" * 86

    other = audit_record(
        evidence(
            correlation_id="g6-003",
            reason_code="POLICY.G6_OMISSION",
        )
    )
    other_bundle, other_fp = checkpoint_for(
        tmp_path,
        [other],
        key_id="g6-omission-signer",
    )

    residual = sum(
        int(value)
        for value in (
            not rejects(forged, bundle, fingerprint),
            not rejects(original, bundle, "0" * 64),
            not rejects(original, tampered_bundle, fingerprint),
            not rejects(original, other_bundle, other_fp),
        )
    )

    assert BASELINE_RESIDUAL_RISK_UNITS == 4
    assert residual / BASELINE_RESIDUAL_RISK_UNITS <= MAX_RESIDUAL_RATIO
    assert residual == 0
