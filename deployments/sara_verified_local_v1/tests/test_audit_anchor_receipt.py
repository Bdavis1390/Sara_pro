from __future__ import annotations

import base64
import hashlib

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.audit_anchor_receipt import (
    AUDIT_ANCHOR_RECEIPT_SCHEMA,
    RECEIPT_AUTH_ED25519,
    RECEIPT_AUTH_NONE,
    RETENTION_NOT_ESTABLISHED,
    AuditAnchorReceiptError,
    build_anchor_publication,
    publish_anchor_and_verify_receipt,
    receipt_signing_payload,
    verify_anchor_receipt,
)
from worldshepherd_sara.audit_checkpoint_anchor import export_external_anchor
from worldshepherd_sara.audit_checkpoint_guarded import GuardedSaraAuditCheckpointManager
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.storage import DurableStore


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _anchor(tmp_path):
    store = DurableStore(tmp_path / "sara")
    store.append_audit(
        AuditRecord(
            timestamp="2026-09-15T02:00:00+00:00",
            event="anchor_receipt_test",
            actor="admin_operator",
            payload={"state": "expected"},
        )
    )
    manager = GuardedSaraAuditCheckpointManager(
        store,
        private_key=Ed25519PrivateKey.generate(),
        key_id="SARA-AUDIT-ANCHOR-RECEIPT-TEST",
    )
    manager.create_checkpoint()
    external = tmp_path / "external"
    external.mkdir()
    path = (external / "anchor.json").resolve()
    export_external_anchor(manager, path)
    return path


class SignedTestSink:
    def __init__(self) -> None:
        self.key = Ed25519PrivateKey.generate()
        public_bytes = self.key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_key = _b64url(public_bytes)
        self.fingerprint = hashlib.sha256(public_bytes).hexdigest()

    def publish(self, publication):
        receipt = {
            "schema": AUDIT_ANCHOR_RECEIPT_SCHEMA,
            "sink_id": "TEST-SIGNED-SINK",
            "receipt_id": f"TEST-RECEIPT-{publication['checkpoint_sequence']:08d}",
            "accepted_at": "2026-09-15T02:01:00+00:00",
            "anchor_sha256": publication["anchor_sha256"],
            "checkpoint_sha256": publication["checkpoint_sha256"],
            "checkpoint_sequence": publication["checkpoint_sequence"],
            "checkpoint_record_count": publication["checkpoint_record_count"],
            "retention_status": RETENTION_NOT_ESTABLISHED,
            "provider_authentication": RECEIPT_AUTH_ED25519,
            "provider_public_key_b64url": self.public_key,
            "provider_key_fingerprint_sha256": self.fingerprint,
        }
        receipt["signature_b64url"] = _b64url(
            self.key.sign(receipt_signing_payload(receipt))
        )
        return receipt


class FailingSink:
    def publish(self, publication):
        raise RuntimeError("simulated provider failure")


def test_signed_sink_publication_verifies_against_pinned_provider(tmp_path):
    anchor = _anchor(tmp_path)
    sink = SignedTestSink()
    result = publish_anchor_and_verify_receipt(
        anchor_path=anchor,
        sink=sink,
        trusted_provider_fingerprint_sha256=sink.fingerprint,
    )
    assert result["verification"]["status"] == "PASS"
    assert result["verification"]["verification_state"] == "AUTHENTICATED_RECEIPT"
    assert result["verification"]["retention_status"] == RETENTION_NOT_ESTABLISHED
    assert result["receipt"]["anchor_sha256"] == result["publication"]["anchor_sha256"]


def test_signed_receipt_rejects_signature_tampering(tmp_path):
    publication = build_anchor_publication(_anchor(tmp_path))
    sink = SignedTestSink()
    receipt = sink.publish(publication)
    receipt["receipt_id"] = "TAMPERED-RECEIPT"
    with pytest.raises(AuditAnchorReceiptError, match="signature verification failed"):
        verify_anchor_receipt(
            publication=publication,
            receipt=receipt,
            trusted_provider_fingerprint_sha256=sink.fingerprint,
        )


def test_receipt_replay_against_different_publication_is_rejected(tmp_path):
    publication = build_anchor_publication(_anchor(tmp_path))
    sink = SignedTestSink()
    receipt = sink.publish(publication)
    different = dict(publication)
    different["anchor_sha256"] = "0" * 64
    with pytest.raises(AuditAnchorReceiptError, match="anchor_sha256 does not match"):
        verify_anchor_receipt(
            publication=different,
            receipt=receipt,
            trusted_provider_fingerprint_sha256=sink.fingerprint,
        )


def test_generic_receipt_cannot_self_assert_worm_retention(tmp_path):
    publication = build_anchor_publication(_anchor(tmp_path))
    sink = SignedTestSink()
    receipt = sink.publish(publication)
    receipt["retention_status"] = "WORM"
    with pytest.raises(AuditAnchorReceiptError, match="must not assert"):
        verify_anchor_receipt(
            publication=publication,
            receipt=receipt,
            trusted_provider_fingerprint_sha256=sink.fingerprint,
        )


def test_unauthenticated_receipt_cannot_satisfy_provider_pin(tmp_path):
    publication = build_anchor_publication(_anchor(tmp_path))
    receipt = {
        "schema": AUDIT_ANCHOR_RECEIPT_SCHEMA,
        "sink_id": "UNAUTH-SINK",
        "receipt_id": "UNAUTH-RECEIPT-1",
        "accepted_at": "2026-09-15T02:02:00+00:00",
        "anchor_sha256": publication["anchor_sha256"],
        "checkpoint_sha256": publication["checkpoint_sha256"],
        "checkpoint_sequence": publication["checkpoint_sequence"],
        "checkpoint_record_count": publication["checkpoint_record_count"],
        "retention_status": RETENTION_NOT_ESTABLISHED,
        "provider_authentication": RECEIPT_AUTH_NONE,
    }
    with pytest.raises(AuditAnchorReceiptError, match="trusted provider fingerprint"):
        verify_anchor_receipt(
            publication=publication,
            receipt=receipt,
            trusted_provider_fingerprint_sha256="1" * 64,
        )


def test_sink_failure_is_normalized(tmp_path):
    with pytest.raises(AuditAnchorReceiptError, match="publication failed"):
        publish_anchor_and_verify_receipt(
            anchor_path=_anchor(tmp_path),
            sink=FailingSink(),
        )
