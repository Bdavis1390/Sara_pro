from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import platform
import tempfile
import time
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.audit_anchor_receipt import (
    AUDIT_ANCHOR_RECEIPT_SCHEMA,
    RECEIPT_AUTH_ED25519,
    RETENTION_NOT_ESTABLISHED,
    AuditAnchorReceiptError,
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


class InternalSignedEvidenceSink:
    """Test-only signed sink proving the provider-neutral receipt contract."""

    def __init__(self) -> None:
        self.key = Ed25519PrivateKey.generate()
        public_bytes = self.key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_key_b64url = _b64url(public_bytes)
        self.fingerprint_sha256 = hashlib.sha256(public_bytes).hexdigest()

    def publish(self, publication: dict[str, Any]) -> dict[str, Any]:
        receipt = {
            "schema": AUDIT_ANCHOR_RECEIPT_SCHEMA,
            "sink_id": "INTERNAL-SIGNED-EVIDENCE-SINK",
            "receipt_id": f"INTERNAL-RECEIPT-{publication['checkpoint_sequence']:08d}",
            "accepted_at": "2026-09-15T02:05:00+00:00",
            "anchor_sha256": publication["anchor_sha256"],
            "checkpoint_sha256": publication["checkpoint_sha256"],
            "checkpoint_sequence": publication["checkpoint_sequence"],
            "checkpoint_record_count": publication["checkpoint_record_count"],
            "retention_status": RETENTION_NOT_ESTABLISHED,
            "provider_authentication": RECEIPT_AUTH_ED25519,
            "provider_public_key_b64url": self.public_key_b64url,
            "provider_key_fingerprint_sha256": self.fingerprint_sha256,
        }
        receipt["signature_b64url"] = _b64url(
            self.key.sign(receipt_signing_payload(receipt))
        )
        return receipt


def _expect_rejected(callable_, fragment: str) -> str:
    try:
        callable_()
    except AuditAnchorReceiptError as exc:
        message = str(exc)
        if fragment not in message:
            raise RuntimeError(
                f"unexpected receipt rejection; wanted {fragment!r}, got {message!r}"
            ) from exc
        return message
    raise RuntimeError(f"receipt adversarial case was not rejected: {fragment}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--software-commit", default=os.getenv("GITHUB_SHA", "UNKNOWN"))
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="ws-anchor-receipt-evidence-") as temp:
        root = Path(temp)
        store = DurableStore(root / "sara")
        store.append_audit(
            AuditRecord(
                timestamp="2026-09-15T02:04:00+00:00",
                event="anchor_receipt_evidence",
                actor="admin_operator",
                payload={"state": "expected"},
            )
        )
        manager = GuardedSaraAuditCheckpointManager(
            store,
            private_key=Ed25519PrivateKey.generate(),
            key_id="SARA-AUDIT-ANCHOR-RECEIPT-EVIDENCE-V1",
        )
        manager.create_checkpoint()
        external = root / "external"
        external.mkdir()
        anchor_path = (external / "anchor.json").resolve()
        anchor = export_external_anchor(manager, anchor_path)

        sink = InternalSignedEvidenceSink()
        verified = publish_anchor_and_verify_receipt(
            anchor_path=anchor_path,
            sink=sink,
            trusted_provider_fingerprint_sha256=sink.fingerprint_sha256,
        )
        publication = verified["publication"]
        receipt = verified["receipt"]
        verification = verified["verification"]
        if verification["verification_state"] != "AUTHENTICATED_TRUSTED_PROVIDER_RECEIPT":
            raise RuntimeError(f"unexpected trusted-provider verification state: {verification}")
        if verification["provider_identity_pinned"] is not True:
            raise RuntimeError("trusted provider identity was not explicitly pinned")
        if verification["retention_status"] != RETENTION_NOT_ESTABLISHED:
            raise RuntimeError("receipt contract unexpectedly promoted retention assurance")

        signature_tamper = dict(receipt)
        signature_tamper["receipt_id"] = "TAMPERED-RECEIPT"
        signature_error = _expect_rejected(
            lambda: verify_anchor_receipt(
                publication=publication,
                receipt=signature_tamper,
                trusted_provider_fingerprint_sha256=sink.fingerprint_sha256,
            ),
            "signature verification failed",
        )

        replay_publication = dict(publication)
        replay_publication["anchor_sha256"] = "0" * 64
        replay_error = _expect_rejected(
            lambda: verify_anchor_receipt(
                publication=replay_publication,
                receipt=receipt,
                trusted_provider_fingerprint_sha256=sink.fingerprint_sha256,
            ),
            "anchor_sha256 does not match",
        )

        retention_tamper = dict(receipt)
        retention_tamper["retention_status"] = "WORM"
        retention_error = _expect_rejected(
            lambda: verify_anchor_receipt(
                publication=publication,
                receipt=retention_tamper,
                trusted_provider_fingerprint_sha256=sink.fingerprint_sha256,
            ),
            "must not assert an unverified retention guarantee",
        )

        wrong_provider_error = _expect_rejected(
            lambda: verify_anchor_receipt(
                publication=publication,
                receipt=receipt,
                trusted_provider_fingerprint_sha256="f" * 64,
            ),
            "provider is not the trusted provider",
        )

        unpinned = verify_anchor_receipt(
            publication=publication,
            receipt=receipt,
        )
        if unpinned["verification_state"] != "SIGNED_RECEIPT_UNPINNED_PROVIDER":
            raise RuntimeError("unpinned provider receipt was over-promoted")
        if unpinned["provider_identity_pinned"] is not False:
            raise RuntimeError("unpinned provider receipt reported a pinned identity")

    result = {
        "schema": "WS-SARA-AUDIT-ANCHOR-RECEIPT-EVIDENCE-V1",
        "result": "PASS",
        "software_commit": args.software_commit,
        "executed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "anchor": {
            "anchor_sha256": anchor["anchor_sha256"],
            "checkpoint_sha256": anchor["checkpoint_sha256"],
            "checkpoint_sequence": anchor["checkpoint_sequence"],
        },
        "receipt_contract": {
            "verification_state": verification["verification_state"],
            "provider_key_pinned": verification["provider_identity_pinned"],
            "provider_signature_verified": True,
            "publication_anchor_exact_match": True,
            "unpinned_signed_receipt_state": unpinned["verification_state"],
            "retention_status": verification["retention_status"],
        },
        "adversarial_acceptance": {
            "signed_receipt_tampering_rejected": bool(signature_error),
            "receipt_replay_against_different_anchor_rejected": bool(replay_error),
            "unverified_worm_self_assertion_rejected": bool(retention_error),
            "wrong_provider_key_pin_rejected": bool(wrong_provider_error),
            "unpinned_signed_receipt_not_treated_as_trusted_provider": True,
        },
        "claims_boundary": [
            "The sink in this evidence run is internal test software, not an external provider.",
            "PASS proves the provider-neutral publication/receipt interface, exact-anchor binding, provider-key pinning, and Ed25519 receipt verification in software.",
            "A signed receipt from an unpinned key is explicitly not treated as trusted-provider authentication.",
            "Retention status remains NOT_ESTABLISHED by construction.",
            "This does not establish external provider deployment, provider independence, WORM or immutable retention, public transparency, third-party attestation, regulatory certification, or operational authorization.",
        ],
    }
    Path(args.out).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
