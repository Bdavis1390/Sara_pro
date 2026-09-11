from __future__ import annotations

import copy
import hashlib
import json

import pytest

from worldshepherd_sara.echo_checkpoint import EchoCheckpointManager
from worldshepherd_sara.echo_checkpoint_anchor import (
    EXTERNAL_READ_BACK_MODE,
    READ_BACK_CONTENT_MATCH,
    TEST_PROVIDER,
    TEST_PROVIDER_MODE,
    EchoCheckpointAnchorError,
    build_anchor_receipt,
    build_anchor_request,
    build_external_readback_evidence,
    build_test_anchor_evidence,
    verify_anchor_evidence,
    verify_anchor_receipt,
    verify_anchor_request,
)
from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.models import AuditRecord


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _record(event_id: str) -> AuditRecord:
    return AuditRecord(
        timestamp="2026-09-11T01:45:00+00:00",
        event="echo_anchor_test",
        actor="admin_operator",
        payload={
            "_outbox_event_id": event_id,
            "_delivery_semantics": "AT_LEAST_ONCE",
            "value": 1,
        },
    )


def _checkpoint(tmp_path, key):
    root = tmp_path / "anchor-echo-data"
    root.mkdir(mode=0o700)
    store = EchoEventStore(root.resolve())
    manager = EchoCheckpointManager(
        store,
        private_key=key,
        key_id="ECHO-ANCHOR-TEST-V1",
    )
    store.ingest(_record("SARA-EVENT-AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA"))
    return manager.create_checkpoint(), manager.fingerprint_sha256


def test_anchor_request_is_deterministic_and_binds_verified_checkpoint(tmp_path, echo_checkpoint_key):
    key, _path = echo_checkpoint_key
    bundle, fingerprint = _checkpoint(tmp_path, key)
    first = build_anchor_request(bundle, fingerprint)
    second = build_anchor_request(bundle, fingerprint)
    assert first == second
    assert first["checkpoint_sha256"] == bundle["checkpoint_sha256"]
    assert first["key_fingerprint_sha256"] == fingerprint
    assert len(first["anchor_payload_sha256"]) == 64
    assert len(first["anchor_request_sha256"]) == 64
    assert verify_anchor_request(first, bundle, fingerprint) == first


def test_simulated_receipt_verifies_only_with_supplied_evidence_artifact(tmp_path, echo_checkpoint_key):
    key, _path = echo_checkpoint_key
    bundle, fingerprint = _checkpoint(tmp_path, key)
    request = build_anchor_request(bundle, fingerprint)
    evidence = build_test_anchor_evidence(
        request,
        provider_reference="test://echo-anchor/1",
        observed_at="2026-09-11T01:46:00+00:00",
    )
    receipt = build_anchor_receipt(
        request,
        evidence,
        expected_provider=TEST_PROVIDER,
        expected_mode=TEST_PROVIDER_MODE,
    )
    result = verify_anchor_receipt(
        receipt,
        evidence,
        bundle,
        fingerprint,
        expected_provider=TEST_PROVIDER,
        expected_mode=TEST_PROVIDER_MODE,
    )
    assert result["status"] == "PASS"
    assert result["verification_state"] == "SIMULATED_ONLY"
    assert result["evidence_sha256"] == evidence["evidence_sha256"]
    assert "external publication" in evidence["claims_boundary"]


def test_anchor_request_rejects_untrusted_checkpoint_fingerprint(tmp_path, echo_checkpoint_key):
    key, _path = echo_checkpoint_key
    bundle, _fingerprint = _checkpoint(tmp_path, key)
    with pytest.raises(EchoCheckpointAnchorError, match="not trusted"):
        build_anchor_request(bundle, "0" * 64)


def test_receipt_tamper_fails_even_if_attacker_recomputes_receipt_digest(tmp_path, echo_checkpoint_key):
    key, _path = echo_checkpoint_key
    bundle, fingerprint = _checkpoint(tmp_path, key)
    request = build_anchor_request(bundle, fingerprint)
    evidence = build_test_anchor_evidence(
        request,
        provider_reference="test://echo-anchor/1",
        observed_at="2026-09-11T01:46:00+00:00",
    )
    receipt = build_anchor_receipt(
        request,
        evidence,
        expected_provider=TEST_PROVIDER,
        expected_mode=TEST_PROVIDER_MODE,
    )
    tampered = copy.deepcopy(receipt)
    tampered["checkpoint_sha256"] = "0" * 64
    core = dict(tampered)
    core.pop("receipt_sha256")
    tampered["receipt_sha256"] = hashlib.sha256(_canonical(core)).hexdigest()
    with pytest.raises(EchoCheckpointAnchorError, match="does not exactly bind"):
        verify_anchor_receipt(
            tampered,
            evidence,
            bundle,
            fingerprint,
            expected_provider=TEST_PROVIDER,
            expected_mode=TEST_PROVIDER_MODE,
        )


def test_receipt_rejects_substituted_evidence_even_with_valid_evidence_digest(tmp_path, echo_checkpoint_key):
    key, _path = echo_checkpoint_key
    bundle, fingerprint = _checkpoint(tmp_path, key)
    request = build_anchor_request(bundle, fingerprint)
    evidence = build_test_anchor_evidence(
        request,
        provider_reference="test://echo-anchor/1",
        observed_at="2026-09-11T01:46:00+00:00",
    )
    receipt = build_anchor_receipt(
        request,
        evidence,
        expected_provider=TEST_PROVIDER,
        expected_mode=TEST_PROVIDER_MODE,
    )
    substituted = copy.deepcopy(evidence)
    substituted["provider_reference"] = "test://echo-anchor/substituted"
    core = dict(substituted)
    core.pop("evidence_sha256")
    substituted["evidence_sha256"] = hashlib.sha256(_canonical(core)).hexdigest()
    with pytest.raises(EchoCheckpointAnchorError, match="does not exactly bind"):
        verify_anchor_receipt(
            receipt,
            substituted,
            bundle,
            fingerprint,
            expected_provider=TEST_PROVIDER,
            expected_mode=TEST_PROVIDER_MODE,
        )


def test_test_provider_cannot_be_promoted_to_external_mode(tmp_path, echo_checkpoint_key):
    key, _path = echo_checkpoint_key
    bundle, fingerprint = _checkpoint(tmp_path, key)
    request = build_anchor_request(bundle, fingerprint)
    evidence = build_test_anchor_evidence(
        request,
        provider_reference="test://echo-anchor/1",
        observed_at="2026-09-11T01:46:00+00:00",
    )
    promoted = copy.deepcopy(evidence)
    promoted["provider"] = "GITHUB_REMOTE"
    promoted["provider_mode"] = EXTERNAL_READ_BACK_MODE
    promoted["verification_state"] = READ_BACK_CONTENT_MATCH
    promoted["provider_content_sha256"] = hashlib.sha256(_canonical(request)).hexdigest()
    core = dict(promoted)
    core.pop("evidence_sha256")
    promoted["evidence_sha256"] = hashlib.sha256(_canonical(core)).hexdigest()
    with pytest.raises(EchoCheckpointAnchorError, match="requires provider document"):
        verify_anchor_evidence(
            promoted,
            request,
            expected_provider="GITHUB_REMOTE",
            expected_mode=EXTERNAL_READ_BACK_MODE,
        )


def test_external_readback_requires_exact_supplied_document_and_reports_content_match(tmp_path, echo_checkpoint_key):
    key, _path = echo_checkpoint_key
    bundle, fingerprint = _checkpoint(tmp_path, key)
    request = build_anchor_request(bundle, fingerprint)
    evidence = build_external_readback_evidence(
        request,
        request,
        provider="GITHUB_REMOTE",
        provider_reference="https://github.com/example/repo/blob/ref/anchor.json",
        observed_at="2026-09-11T01:47:00+00:00",
    )
    assert evidence["verification_state"] == READ_BACK_CONTENT_MATCH
    assert "does not prove" in evidence["claims_boundary"]
    with pytest.raises(EchoCheckpointAnchorError, match="requires provider document"):
        verify_anchor_evidence(
            evidence,
            request,
            expected_provider="GITHUB_REMOTE",
            expected_mode=EXTERNAL_READ_BACK_MODE,
        )
    verified = verify_anchor_evidence(
        evidence,
        request,
        expected_provider="GITHUB_REMOTE",
        expected_mode=EXTERNAL_READ_BACK_MODE,
        provider_document=request,
    )
    assert verified["provider_content_sha256"] == hashlib.sha256(_canonical(request)).hexdigest()
    receipt = build_anchor_receipt(
        request,
        evidence,
        expected_provider="GITHUB_REMOTE",
        expected_mode=EXTERNAL_READ_BACK_MODE,
        provider_document=request,
    )
    with pytest.raises(EchoCheckpointAnchorError, match="requires provider document"):
        verify_anchor_receipt(
            receipt,
            evidence,
            bundle,
            fingerprint,
            expected_provider="GITHUB_REMOTE",
            expected_mode=EXTERNAL_READ_BACK_MODE,
        )
    result = verify_anchor_receipt(
        receipt,
        evidence,
        bundle,
        fingerprint,
        expected_provider="GITHUB_REMOTE",
        expected_mode=EXTERNAL_READ_BACK_MODE,
        provider_document=request,
    )
    assert result["status"] == "PASS"
    assert result["verification_state"] == READ_BACK_CONTENT_MATCH
    assert "does not prove remote retrieval provenance" in result["claims_boundary"]


def test_external_readback_rejects_different_provider_document(tmp_path, echo_checkpoint_key):
    key, _path = echo_checkpoint_key
    bundle, fingerprint = _checkpoint(tmp_path, key)
    request = build_anchor_request(bundle, fingerprint)
    wrong = copy.deepcopy(request)
    wrong["checkpoint_sha256"] = "0" * 64
    with pytest.raises(EchoCheckpointAnchorError, match="does not equal anchor request"):
        build_external_readback_evidence(
            request,
            wrong,
            provider="GITHUB_REMOTE",
            provider_reference="https://github.com/example/repo/blob/ref/anchor.json",
            observed_at="2026-09-11T01:47:00+00:00",
        )
